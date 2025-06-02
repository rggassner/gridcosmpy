#!venv/bin/python3
from diffusers import StableDiffusionInpaintPipeline
import torch, sys
from PIL import Image

steps = 50
noptions = 27

def dummy(images, **kwargs):
    return images, [False] * len(images)  # Fix: make it iterable

def gen_out(image, iteration):
    old_im = image.resize((128, 128))
    new_im = Image.new("RGB", (512, 512))
    box = tuple((n - o) // 2 for n, o in zip((512, 512), old_im.size))
    new_im.paste(old_im, box)
    new_im.save(f'tmp/scaled/{iteration}-scaled.png')

prompt = sys.argv[1].strip()
count = sys.argv[2]

pipe = StableDiffusionInpaintPipeline.from_pretrained(
    "stabilityai/stable-diffusion-2-inpainting",
    torch_dtype=torch.float16
).to("cuda")

pipe.safety_checker = dummy

print(prompt)

for iteration in range(1, noptions):
    torch.cuda.empty_cache()
    init_image_arr = Image.open(f'out/{int(count)-1}-scaled.png')
    mask_image_arr = Image.open('img/mask.png')
    
    outpainted_image = pipe(
        prompt=prompt,
        image=init_image_arr,
        mask_image=mask_image_arr,
        num_inference_steps=steps
    ).images[0]
    
    outpainted_image.save(f'tmp/img/{iteration}.png')
    gen_out(outpainted_image, iteration)

