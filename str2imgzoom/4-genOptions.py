#!/bin/python3
from diffusers import StableDiffusionInpaintPipeline
import torch,sys
from PIL import Image

steps=50
noptions=27

def dummy(images, **kwargs):
    return images, False

def gen_out(image,iteration):
    old_im = image.resize((128, 128))
    old_size = old_im.size
    new_size = (512, 512)
    new_im = Image.new("RGB", new_size) 
    box = tuple((n - o) // 2 for n, o in zip(new_size, old_size))
    new_im.paste(old_im, box)
    new_im.save('tmp/scaled/'+str(iteration)+'-scaled.png')

prompt=sys.argv[1]
prompt=prompt.strip()
count=sys.argv[2]

pipe = StableDiffusionInpaintPipeline.from_pretrained( "runwayml/stable-diffusion-inpainting",torch_dtype=torch.float16).to('cuda')
pipe.safety_checker = dummy
print(prompt)
for iteration in range(1,noptions):
    torch.cuda.empty_cache()
    init_image_arr = Image.open('out/'+str(int(count)-1)+'-scaled.png')
    mask_image_arr = Image.open('img/mask.png')
    outpainted_image = pipe(prompt=prompt, image=init_image_arr, mask_image=mask_image_arr,num_inference_steps=steps).images[0]
    outpainted_image.save('tmp/img/'+str(iteration)+'.png')
    gen_out(outpainted_image,iteration)
