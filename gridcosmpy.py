#!/usr/bin/python3
import multiprocessing
import requests
import ffmpeg
import math
import ssl
import re
from waifu2x_ncnn_vulkan_python import Waifu2x
from os.path import exists
from PIL import Image

zoom_ratio=.98
IMAGES_FOLDER="images/"
OIMAGES_FOLDER="imagesi/"
SCALED_FOLDER="scaled/"
TRIMS_FOLDER="trims/"
im_width=3600
NPROCS=5
INPUT_FORMAT='png'
OUTPUT_FORMAT='jpg'
ENLARGE=False

class TLSAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = ctx
        return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)

def get_current(session=""):
    res = session.get('https://www.sito.org/cgi-bin/gridcosm/gridcosm')
    current=re.search(r'SITO - Gridcosm level ([0-9].+)</title>',res.content.decode())
    return int(current[1])-1

def sync_images(current,session=""):
    for level in range(current):
        if not exists(OIMAGES_FOLDER+str(level)+'.jpg'):
            img_data = res = session.get('https://www.sito.org/synergy/gridcosm/pieces/'+str(level).zfill(3)+'-f.jpg').content
            with open(OIMAGES_FOLDER+str(level)+'.jpg', 'wb') as handler:
                handler.write(img_data)

def load_image(filename,folder=IMAGES_FOLDER,fformat=INPUT_FORMAT):
    filename=folder+str(filename)+'.'+fformat
    return Image.open(filename)

def enlarge(image):
    waifu2x = Waifu2x(gpuid=0, scale=8, noise=3)
    return waifu2x.process(image)

def gen_frames_out(current):
    pool = multiprocessing.Pool(NPROCS)
    result = pool.map(gen_frame_out, range(0,current-1))

def gen_frame_out(current):
    print('Starting {}'.format(current))
    frame_count=1000*current
    width = im_width * 3
    czoom_ratio=zoom_ratio
    while (width*zoom_ratio) >= im_width:
        #If the frame does not exist
        if not exists(SCALED_FOLDER+str(frame_count).zfill(12)+".jpg"):
            working_frame = load_image(current+1).resize((im_width*3,im_width*3), Image.ANTIALIAS)
            working_frame.paste(load_image(current),(im_width,im_width))
            if (current-1) >= 0:
                previous=load_image(current-1,folder=IMAGES_FOLDER).resize((int(math.floor(im_width/3)),int(math.floor(im_width/3))), Image.ANTIALIAS)
                working_frame.paste(previous,(im_width+int(math.floor(im_width/3)),im_width+int(math.floor(im_width/3))))
                if (current-2) >= 0:
                    pprevious=load_image(current-2,folder=IMAGES_FOLDER).resize((int(math.floor(im_width/9)),int(math.floor(im_width/9))), Image.ANTIALIAS)
                    working_frame.paste(pprevious,(im_width+int(math.floor(im_width/3+im_width/9)),im_width+int(math.floor(im_width/3+im_width/9)) ))
            working_frame = working_frame.resize((int(math.floor(im_width*3*czoom_ratio)),int(math.floor(im_width*3*czoom_ratio))), Image.ANTIALIAS)
            nwidth, width = working_frame.size
            working_frame=working_frame.crop((math.floor((nwidth/2)-(im_width/2)),math.floor((nwidth/2)-(im_width/2)),math.floor((nwidth/2)+(im_width/2)),math.floor((nwidth/2)+(im_width/2))))
            if ENLARGE:
                enlarge(working_frame).save(SCALED_FOLDER+str(frame_count).zfill(12)+".jpg")
            else:
                working_frame.save(SCALED_FOLDER+str(frame_count).zfill(12)+".jpg")
        #Quite rare condition, used to avoid generating a image smaller than the video size after a resumed run
        else:
            nwidth, width = load_image(str(frame_count).zfill(12),folder=SCALED_FOLDER,fformat=OUTPUT_FORMAT).size
        frame_count=frame_count+1
        czoom_ratio=czoom_ratio*zoom_ratio
    print('   Finished {}'.format(current))
    return True

def gen_video():
    output = ( ffmpeg
    .input(SCALED_FOLDER+'*.jpg', pattern_type='glob', framerate=25)
    .filter('crop',im_width,int(math.floor(im_width/1.77777)))
    .output('gridcosmpy.mp4')
    .run())

session = requests.session()
session.mount('https://', TLSAdapter())
current=get_current(session=session)
sync_images(current,session=session)
gen_frames_out(current)
gen_video()

