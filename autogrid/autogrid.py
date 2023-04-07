#!/bin/python3
from diffusers import StableDiffusionInpaintPipeline
import torch,argparse
from PIL import Image

noptions=25
allow_nsfw=True

def dummy(images, **kwargs):
    return images, False

argParser = argparse.ArgumentParser()
argParser.add_argument("-t", "--text",required=True,help="Text that will be used to inpaint the image.")
argParser.add_argument("-n", "--negative",required=True,help="Negative prompt.")
argParser.add_argument("-s", "--steps",required=True,help="Number of steps.")
args = argParser.parse_args()
prompt=args.text
negative_prompt=args.negative
steps=int(args.steps)
negative_prompt.strip()
prompt=prompt.strip()
pipe = StableDiffusionInpaintPipeline.from_pretrained( "runwayml/stable-diffusion-inpainting",torch_dtype=torch.float16).to('cuda')
if allow_nsfw:
    pipe.safety_checker = dummy

for iteration in range(1,noptions):
    torch.cuda.empty_cache()
    init_image_arr = Image.open('img/input.png')
    mask_image_arr = Image.open('img/mask.png')
    outpainted_image = pipe(prompt=prompt, negative_prompt=negative_prompt,image=init_image_arr, mask_image=mask_image_arr,num_inference_steps=steps).images[0]
    outpainted_image.save('tmp/'+str(iteration)+'.png')
