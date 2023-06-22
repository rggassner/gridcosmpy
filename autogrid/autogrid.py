#!/bin/python3
from diffusers import StableDiffusionInpaintPipeline
import torch,argparse
from PIL import Image
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import os,datetime

noptions=200
tile_size=150
sd_size=512
allow_nsfw=True

def dummy(images, **kwargs):
    return images, False

def get_image_mask_rows():
    mask = Image.new("RGB", (tile_size*3,tile_size*3), (255, 255, 255))
    image = Image.new("RGB", (tile_size*3,tile_size*3), (255, 255, 255))
    pmask = Image.new("RGB", (tile_size,tile_size), (0, 0, 0))
    header = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5'}
    page=requests.get("https://www.sito.org/cgi-bin/gridcosm/gridcosm?level=top", headers=header).text
    soup = BeautifulSoup(page, 'html.parser')
    rows = soup.find_all('table', attrs={'cellpadding': '0' ,'style':'width:100%; max-width: 450px;display:inline-block;vertical-align:top;'})[0].find_all('tr')
    rowcount=1
    for row in rows:
        data = row.find_all('td')
        for col in range(0,3):
            if len(data[col].find_all('img')) == 1:
                response = requests.get('https://www.sito.org/'+data[col].find_all('img')[0]['src'])
                part = Image.open(BytesIO(response.content))
                image.paste(part,(col*tile_size,(rowcount-1)*tile_size))
                mask.paste(pmask,(col*tile_size,(rowcount-1)*tile_size))
        rowcount=rowcount+1
    mask = mask.resize((sd_size,sd_size), Image.Resampling.LANCZOS)
    image = image.resize((sd_size,sd_size), Image.Resampling.LANCZOS)
    return image,mask,rows

def read_arguments():
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-t", "--text",required=True,help="Text that will be used to inpaint the image.")
    argParser.add_argument("-n", "--negative",required=True,help="Negative prompt.")
    argParser.add_argument("-s", "--steps",required=True,type=int,help="Number of steps.")
    return argParser.parse_args()

def gen_images(prompt,negative_prompt,steps):
    out_dir=str(datetime.datetime.now().timestamp())
    os.mkdir(out_dir)
    image,mask,rows=get_image_mask_rows()
    pipe = StableDiffusionInpaintPipeline.from_pretrained( "runwayml/stable-diffusion-inpainting",torch_dtype=torch.float16).to('cuda')
    if allow_nsfw:
        pipe.safety_checker = dummy
    for iteration in range(1,noptions):
        torch.cuda.empty_cache()
        outpainted_image = pipe(prompt=prompt, negative_prompt=negative_prompt,image=image, mask_image=mask,num_inference_steps=steps).images[0]
        outpainted_image.save(out_dir+'/'+str(iteration)+'.png')
        os.mkdir(out_dir+'/'+str(iteration))
        resized=outpainted_image.resize((tile_size*3,tile_size*3),Image.Resampling.LANCZOS)
        rowcount=1
        for row in rows:
            data = row.find_all('td')
            for col in range(0,3):
                if len(data[col].find_all('img')) != 1:
                    outi = resized.crop((col*tile_size,(rowcount-1)*tile_size,(col+1)*tile_size,rowcount*tile_size))
                    outi.save(out_dir+'/'+str(iteration)+'/'+str(col)+'-'+str(rowcount)+'.png')
            rowcount=rowcount+1

def main():
    args=read_arguments()
    gen_images(args.text,args.negative,args.steps)

if __name__ == "__main__":
    main()
