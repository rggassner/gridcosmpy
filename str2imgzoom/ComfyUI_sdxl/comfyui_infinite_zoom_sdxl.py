#!/usr/bin/env python3
"""
Run an infinite-zoom illustration sequence through the local ComfyUI API.

Expected setup:
- ComfyUI is running locally.
- `infinite_zoom_api.json` is a ComfyUI workflow saved in API format.
- The workflow has:
    * a LoadImage node for the input canvas
    * a LoadImage node for the mask
    * an ImageToMask node converting the mask image's red channel to a mask
    * a CLIPTextEncode node for the positive prompt
    * a KSampler node
    * a SaveImage node
- The workflow uses VAE Encode (for Inpainting), with the input image and mask.
- `2-book.txt` contains one prompt/passage per line.
- `0.png` is the initial black canvas and `mask.png` is the white mask.

Edit the node IDs in the Configuration section to match your API workflow.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
from PIL import Image


# ---------------------------------------------------------------------------
# Configuration: change these values to match your machine/workflow.
# ---------------------------------------------------------------------------

COMFY_URL = "http://127.0.0.1:8188"

PROJECT_DIR = Path(".")
WORKFLOW_FILE = PROJECT_DIR / "infinite_zoom_api_sdxl.json"
INITIAL_IMAGE = PROJECT_DIR / "img/0_1024.png"
MASK_IMAGE = PROJECT_DIR / "img/mask_overlap_1024.png"
PROMPTS_FILE = PROJECT_DIR / "2-book.txt"

OUTPUT_DIR = PROJECT_DIR / "out"
CANDIDATES_DIR = OUTPUT_DIR / "candidates"
CANVAS_DIR = OUTPUT_DIR / "canvases"
STATE_FILE = OUTPUT_DIR / "project_state.json"

# API-format workflow node IDs. Replace these example values.
IMAGE_NODE_ID = "10"       # LoadImage for the current canvas
MASK_NODE_ID = "11"        # LoadImage for mask.png
MASK_CONVERT_NODE_ID = "12"  # ImageToMask
POSITIVE_NODE_ID = "6"     # CLIPTextEncode positive prompt
KSAMPLER_NODE_ID = "3"     # KSampler
SAVE_NODE_ID = "9"         # SaveImage

# Infinite zoom settings.
CANVAS_WIDTH = 1024
CANVAS_HEIGHT = 1024
CENTER_SCALE = 0.25        # Previous selected image becomes 25% of next canvas
CANDIDATES_PER_PASSAGE = 4
DEFAULT_STEPS = 30
DEFAULT_CFG = 6.0
DEFAULT_DENOISE = 1.0
POLL_INTERVAL_SECONDS = 1.0
JOB_TIMEOUT_SECONDS = 1800


def ensure_dirs() -> None:
    """Create project output directories."""
    for directory in (OUTPUT_DIR, CANDIDATES_DIR, CANVAS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def load_prompts(path: Path) -> list[str]:
    """Read one non-empty passage/prompt per line."""
    if not path.exists():
        raise FileNotFoundError(f"Prompts file not found: {path}")

    prompts = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [prompt for prompt in prompts if prompt]


def load_state() -> dict[str, Any]:
    """Load resumable project state, or return an empty state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"completed": {}}


def save_state(state: dict[str, Any]) -> None:
    """Atomically save project state."""
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(STATE_FILE)


def copy_to_comfy_input(source: Path, destination_name: str) -> str:
    """
    Copy an image into ComfyUI's local input folder.

    This assumes the script and ComfyUI run on the same machine. The standard
    input folder is <ComfyUI installation>/input; override COMFY_INPUT_DIR if
    your installation differs.
    """
    input_dir = Path(
        # Set COMFY_INPUT_DIR in the environment if ComfyUI uses a custom path.
        __import__("os").environ.get(
            "COMFY_INPUT_DIR",
            "/home/rgg/apps/ComfyUI/input",
        )
    )
    input_dir.mkdir(parents=True, exist_ok=True)
    destination = input_dir / destination_name
    shutil.copy2(source, destination)
    return destination.name


def create_zoom_canvas(source: Path, destination: Path) -> None:
    """
    Place the previous selected image, reduced in size, at the center of a
    black canvas. This creates the visual seed for the next zoom iteration.
    """
    with Image.open(source) as opened:
        image = opened.convert("RGB")

    new_width = max(1, round(CANVAS_WIDTH * CENTER_SCALE))
    new_height = max(1, round(CANVAS_HEIGHT * CENTER_SCALE))
    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0))
    left = (CANVAS_WIDTH - new_width) // 2
    top = (CANVAS_HEIGHT - new_height) // 2
    canvas.paste(image, (left, top))
    canvas.save(destination)


def api_get_image(
    session: requests.Session,
    filename: str,
    subfolder: str,
    folder_type: str,
) -> bytes:
    """Download an output image from ComfyUI's /view endpoint."""
    response = session.get(
        f"{COMFY_URL}/view",
        params={
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.content


def wait_for_history(
    session: requests.Session,
    prompt_id: str,
    timeout_seconds: int = JOB_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Poll ComfyUI history until the queued prompt finishes."""
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        response = session.get(f"{COMFY_URL}/history/{prompt_id}", timeout=30)
        response.raise_for_status()
        history = response.json()

        if prompt_id in history:
            entry = history[prompt_id]
            status = entry.get("status", {})
            if status.get("status_str") == "error" or status.get("completed") is False:
                messages = status.get("messages", [])
                if any(
                    isinstance(message, list)
                    and message
                    and message[0] == "execution_error"
                    for message in messages
                ):
                    raise RuntimeError(
                        f"ComfyUI reported an execution error: {messages}"
                    )
            if entry.get("outputs") is not None:
                return entry

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(
        f"Timed out waiting for ComfyUI prompt {prompt_id} after "
        f"{timeout_seconds} seconds."
    )


def patch_workflow(
    workflow_template: dict[str, Any],
    image_name: str,
    mask_name: str,
    positive_prompt: str,
    seed: int,
    save_prefix: str,
    steps: int,
    cfg: float,
    denoise: float,
) -> dict[str, Any]:
    """Copy the API workflow and update image, prompt, sampler, and output."""
    workflow = json.loads(json.dumps(workflow_template))

    required_nodes = {
        IMAGE_NODE_ID,
        MASK_NODE_ID,
        MASK_CONVERT_NODE_ID,
        POSITIVE_NODE_ID,
        KSAMPLER_NODE_ID,
        SAVE_NODE_ID,
    }
    missing = required_nodes.difference(workflow)
    if missing:
        raise KeyError(
            "Workflow is missing configured node IDs: "
            + ", ".join(sorted(missing))
            + ". Edit the node IDs at the top of this script."
        )

    workflow[IMAGE_NODE_ID]["inputs"]["image"] = image_name
    workflow[MASK_NODE_ID]["inputs"]["image"] = mask_name

    # ImageToMask normally has a `channel` input, e.g. red, green, blue, alpha.
    workflow[MASK_CONVERT_NODE_ID]["inputs"]["channel"] = "red"

    workflow[POSITIVE_NODE_ID]["inputs"]["text"] = positive_prompt

    sampler_inputs = workflow[KSAMPLER_NODE_ID]["inputs"]
    sampler_inputs["seed"] = seed
    sampler_inputs["steps"] = steps
    sampler_inputs["cfg"] = cfg
    sampler_inputs["denoise"] = denoise

    workflow[SAVE_NODE_ID]["inputs"]["filename_prefix"] = save_prefix
    return workflow


def queue_workflow(
    session: requests.Session,
    workflow: dict[str, Any],
) -> str:
    """Submit an API-format workflow to ComfyUI and return its prompt ID."""
    response = session.post(
        f"{COMFY_URL}/prompt",
        json={"prompt": workflow, "client_id": "infinite-zoom-python"},
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            f"ComfyUI rejected the workflow ({response.status_code}): "
            f"{response.text}"
        )

    result = response.json()
    if "prompt_id" not in result:
        raise RuntimeError(f"Unexpected ComfyUI response: {result}")
    return result["prompt_id"]


def collect_saved_images(
    session: requests.Session,
    history: dict[str, Any],
    candidate_stem: str,
) -> list[Path]:
    """Download image outputs from all nodes in the completed workflow."""
    downloaded: list[Path] = []
    outputs = history.get("outputs", {})

    for node_output in outputs.values():
        for image_info in node_output.get("images", []):
            data = api_get_image(
                session,
                image_info["filename"],
                image_info.get("subfolder", ""),
                image_info.get("type", "output"),
            )
            extension = Path(image_info["filename"]).suffix or ".png"
            destination = CANDIDATES_DIR / f"{candidate_stem}_{len(downloaded) + 1}{extension}"
            destination.write_bytes(data)
            downloaded.append(destination)

    return downloaded


def generate_candidate(
    session: requests.Session,
    workflow_template: dict[str, Any],
    input_canvas: Path,
    mask_path: Path,
    prompt: str,
    passage_number: int,
    candidate_number: int,
    steps: int,
    cfg: float,
    denoise: float,
) -> Path:
    """Run one candidate and return its downloaded image path."""
    image_name = copy_to_comfy_input(
        input_canvas,
        f"infinite_zoom_input_{passage_number:04d}.png",
    )
    mask_name = copy_to_comfy_input(mask_path, "infinite_zoom_mask.png")

    seed = random.randint(0, 2**63 - 1)
    prefix = f"infinite_zoom/p{passage_number:04d}_c{candidate_number:02d}"

    workflow = patch_workflow(
        workflow_template=workflow_template,
        image_name=image_name,
        mask_name=mask_name,
        positive_prompt=prompt,
        seed=seed,
        save_prefix=prefix,
        steps=steps,
        cfg=cfg,
        denoise=denoise,
    )

    prompt_id = queue_workflow(session, workflow)
    print(f"  Candidate {candidate_number}: queued as {prompt_id} (seed {seed})")

    history = wait_for_history(session, prompt_id)
    downloaded = collect_saved_images(
        session,
        history,
        f"p{passage_number:04d}_c{candidate_number:02d}",
    )

    if not downloaded:
        raise RuntimeError(
            "Workflow completed, but no image outputs were found. "
            "Check that the workflow ends in a SaveImage node."
        )

    # Most workflows have one SaveImage output. If yours saves more than one,
    # use the first image for candidate selection.
    chosen_file = downloaded[0]
    print(f"  Saved candidate: {chosen_file}")
    return chosen_file


def choose_candidate(candidates: list[Path], passage_number: int) -> Path:
    """Prompt the user to select a candidate, or regenerate with 'r'."""
    while True:
        print(f"\nPassage {passage_number}: candidates")
        for index, candidate in enumerate(candidates, start=1):
            print(f"  {index}: {candidate}")

        answer = input(
            "Choose a candidate number, or 'q' to quit: "
        ).strip().lower()

        if answer == "q":
            raise KeyboardInterrupt("Selection cancelled by user.")

        if answer.isdigit() and 1 <= int(answer) <= len(candidates):
            return candidates[int(answer) - 1]

        print("Invalid selection. Please enter one of the listed numbers or q.")


def main() -> int:
    """Run the infinite-zoom sequence."""
    global COMFY_URL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=COMFY_URL, help="ComfyUI base URL")
    parser.add_argument("--count", type=int, default=CANDIDATES_PER_PASSAGE)
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--cfg", type=float, default=DEFAULT_CFG)
    parser.add_argument("--denoise", type=float, default=DEFAULT_DENOISE)
    parser.add_argument(
        "--start-at",
        type=int,
        default=1,
        help="Passage number to start at (1-based); completed passages are skipped",
    )
    args = parser.parse_args()

    COMFY_URL = args.url.rstrip("/")

    ensure_dirs()

    for required in (WORKFLOW_FILE, INITIAL_IMAGE, MASK_IMAGE, PROMPTS_FILE):
        if not required.exists():
            print(f"ERROR: required file does not exist: {required}", file=sys.stderr)
            return 2

    workflow_template = json.loads(WORKFLOW_FILE.read_text(encoding="utf-8"))
    prompts = load_prompts(PROMPTS_FILE)
    state = load_state()

    # ComfyUI's /prompt expects the API-format node graph, not the regular UI
    # workflow export. A quick connectivity check gives a clearer error.
    with requests.Session() as session:
        try:
            response = session.get(f"{COMFY_URL}/system_stats", timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(
                f"ERROR: cannot reach ComfyUI at {COMFY_URL}: {exc}",
                file=sys.stderr,
            )
            return 2

        current_canvas = INITIAL_IMAGE

        # If previous passages are complete, reconstruct the next input canvas
        # from the most recently selected image.
        for previous_number in range(1, min(args.start_at, len(prompts) + 1)):
            previous_key = str(previous_number)
            if previous_key not in state["completed"]:
                print(
                    f"ERROR: passage {previous_number} is not recorded as complete. "
                    "Start at an earlier passage or restore project_state.json.",
                    file=sys.stderr,
                )
                return 2
            selected = Path(state["completed"][previous_key]["selected_image"])
            if not selected.exists():
                print(f"ERROR: selected image is missing: {selected}", file=sys.stderr)
                return 2
            current_canvas = CANVAS_DIR / f"passage_{previous_number:04d}_canvas.png"
            create_zoom_canvas(selected, current_canvas)

        for passage_number in range(args.start_at, len(prompts) + 1):
            key = str(passage_number)

            if key in state["completed"]:
                print(f"Passage {passage_number} already completed; skipping.")
                selected = Path(state["completed"][key]["selected_image"])
                current_canvas = CANVAS_DIR / f"passage_{passage_number:04d}_canvas.png"
                if not current_canvas.exists():
                    create_zoom_canvas(selected, current_canvas)
                continue

            passage = prompts[passage_number - 1]
            print(f"\n=== Passage {passage_number}/{len(prompts)} ===")
            print(passage)

            candidates: list[Path] = []
            for candidate_number in range(1, args.count + 1):
                candidate = generate_candidate(
                    session=session,
                    workflow_template=workflow_template,
                    input_canvas=current_canvas,
                    mask_path=MASK_IMAGE,
                    prompt=passage,
                    passage_number=passage_number,
                    candidate_number=candidate_number,
                    steps=args.steps,
                    cfg=args.cfg,
                    denoise=args.denoise,
                )
                candidates.append(candidate)

            selected_candidate = choose_candidate(candidates, passage_number)
            selected_destination = OUTPUT_DIR / f"{passage_number:04d}.png"
            shutil.copy2(selected_candidate, selected_destination)

            # Save state immediately after selection, so interruption won't
            # lose the committed result.
            state["completed"][key] = {
                "passage": passage,
                "selected_image": str(selected_destination.resolve()),
                "candidate_images": [str(path.resolve()) for path in candidates],
                "selected_candidate": str(selected_candidate.resolve()),
            }
            save_state(state)

            # Build the input canvas for the next iteration. The selected
            # image becomes a small centered image on a black canvas.
            current_canvas = CANVAS_DIR / f"passage_{passage_number:04d}_canvas.png"
            create_zoom_canvas(selected_destination, current_canvas)
            print(f"Selected image saved to {selected_destination}")
            print(f"Next zoom canvas saved to {current_canvas}")

    print("\nAll passages completed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nStopped. Completed selections have been saved.")
        raise SystemExit(130)
