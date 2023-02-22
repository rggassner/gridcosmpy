#!/bin/python3
from diffusers import StableDiffusionInpaintPipeline
import torch,argparse
from PIL import Image

steps=50
noptions=25
allow_nsfw=False

def dummy(images, **kwargs):
    return images, False

argParser = argparse.ArgumentParser()
argParser.add_argument("-t", "--text",required=True,help="Text that will be used to inpaint the image.")
args = argParser.parse_args()
prompt=args.text
prompt=prompt.strip()
pipe = StableDiffusionInpaintPipeline.from_pretrained( "runwayml/stable-diffusion-inpainting",torch_dtype=torch.float16).to('cuda')
if allow_nsfw:
    pipe.safety_checker = dummy

for iteration in range(1,noptions):
    torch.cuda.empty_cache()
    init_image_arr = Image.open('img/input.png')
    mask_image_arr = Image.open('img/mask.png')
    outpainted_image = pipe(prompt=prompt, image=init_image_arr, mask_image=mask_image_arr,num_inference_steps=steps).images[0]
    outpainted_image.save('tmp/'+str(iteration)+'.png')
