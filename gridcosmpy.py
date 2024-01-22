#!/usr/bin/python3
import multiprocessing
import ffmpeg
import math
from os.path import exists
import os
from pathlib import  Path
from PIL import Image
import argparse

zoom_ratio=.98
IMAGES_FOLDER="input_upscaled/"
SCALED_FOLDER="output_frames/"
NPROCS=5
INPUT_FORMAT='png'

def load_image(filename,folder=IMAGES_FOLDER,fformat=INPUT_FORMAT):
    filename=folder+str(filename).zfill(3)+'-f.'+fformat
    return Image.open(filename)

def gen_frames_out(current):
    pool = multiprocessing.Pool(NPROCS)
    result = pool.map(gen_frame_out, range(0,current-2))

def get_image_size():
    png_files = [f for f in os.listdir(IMAGES_FOLDER) if f.lower().endswith('.png')]
    if png_files:
        first_png_path = os.path.join(IMAGES_FOLDER, png_files[0])
        im = Image.open(first_png_path)
        return im.size[0]
    else:
        return None  

def gen_frame_out(current):
    print('Starting {}'.format(current))
    frame_count=1000*current
    width = im_width * imrate
    czoom_ratio=zoom_ratio
    while (width*zoom_ratio) >= im_width:
        #If the frame does not exist
        if not exists(SCALED_FOLDER+str(frame_count).zfill(12)+".png"):
            #Create a large fame using the current one
            working_frame = load_image(current+1).resize((im_width*imrate,im_width*imrate), Image.LANCZOS)
            #Paste previous frame

            #works with 3(maybe 4)
            pos=int(math.floor( ((imrate*im_width)/2) - (im_width/2) ))
            #works with 4
            #pos=int(math.floor(((imrate/2)*im_width)-(im_width/2)))

            working_frame.paste(load_image(current),(pos,pos))
            #Paste smaller versions of previous frames. The higher the resolution, the higher the number of previous scaled images to combine.
            #Should have done an iterated loop for this, maybe when dealing with 8k...
            if (current-1) >= 0:
                previous=load_image(current-1,folder=IMAGES_FOLDER).resize((int(math.floor(im_width/imrate)),int(math.floor(im_width/imrate))), Image.LANCZOS)
                ppos=int(math.floor(((im_width/2)-((im_width/imrate)/2))))
                working_frame.paste(previous,(pos+ppos,pos+ppos))
                if (current-2) >= 0:
                    pprevious=load_image(current-2,folder=IMAGES_FOLDER).resize((int(math.floor(im_width/(imrate**2))),int(math.floor(im_width/(imrate**2)))), Image.LANCZOS)
                    pppos=int(math.floor(( (im_width/(2)) - ((im_width/imrate)/2))    /imrate         ))
                    working_frame.paste(pprevious,(pos+ppos+pppos,pos+ppos+pppos))
            #Resize the the resulting frame according to current zoom level
            working_frame = working_frame.resize((int(math.floor(im_width*imrate*czoom_ratio)),int(math.floor(im_width*imrate*czoom_ratio))), Image.LANCZOS)
            #Retrieve image dimensions
            nwidth, width = working_frame.size
            #Crop the center of the image to get the desired dimension
            working_frame=working_frame.crop((math.floor((nwidth/2)-(im_width/2)),math.floor((nwidth/2)-(im_width/2)),math.floor((nwidth/2)+(im_width/2)),math.floor((nwidth/2)+(im_width/2))))
            working_frame.save(SCALED_FOLDER+str(frame_count).zfill(12)+".png")
        #Quite rare condition, used to avoid generating a image smaller than the video size after a resumed run
        else:
            width = int(math.floor(im_width*imrate*czoom_ratio))
        frame_count=frame_count+1
        czoom_ratio=czoom_ratio*zoom_ratio
    print('   Finished {}'.format(current))
    return True

def gen_video():
    output = ( ffmpeg
    .input(SCALED_FOLDER+'*.png', pattern_type='glob', framerate=25)
    .filter('crop',im_width,int(math.floor(im_width/1.77777)))
    .output('gridcosmpy.mp4')
    .run())
    
def gen_video_reversed():
    output = ( ffmpeg
    .input('reversed/tmp/'+'*.png', pattern_type='glob', framerate=25)
    .output('gridcosmpy_reversed.mp4')
    .run(quiet=True))

def split_images():
    output= (ffmpeg
    .input('gridcosmpy.mp4')
    .output('reversed/%d.png', start_number=0)
    .overwrite_output()
    .run(quiet=True))

def rename_reversed():
    largest=0
    for filename in os.listdir('reversed'):
        if filename.endswith('.png'): 
            if int(Path(filename).stem) > largest:
                largest=int(Path(filename).stem)
    for num in range(0,int(largest+1)):
        os.rename('reversed/'+str(num)+'.png','reversed/tmp/'+str(largest-num).zfill(12)+'.png')

def get_current():
    count=0
    for path in os.listdir(IMAGES_FOLDER):
        if os.path.isfile(os.path.join(IMAGES_FOLDER, path)):
            count += 1
    return count

argParser = argparse.ArgumentParser()
argParser.add_argument("-r", "--rate",type=int, required=True,help="Image rate. This is the division of the external image size by the internal image size. Tested with 3 (gridcosm) and 4 (str2imgzoom).")
args = argParser.parse_args()
imrate=args.rate
im_width=get_image_size()
current=get_current()
gen_frames_out(current)
#gen_video()
split_images()
rename_reversed()
gen_video_reversed()
