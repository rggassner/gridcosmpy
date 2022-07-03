#!/usr/bin/python3
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
SCALED_FOLDER="scaled/"
TRIMS_FOLDER="trims/"
im_width=450

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
        if not exists(IMAGES_FOLDER+str(level)+'.jpg'):
            img_data = res = session.get('https://www.sito.org/synergy/gridcosm/pieces/'+str(level).zfill(3)+'-f.jpg').content
            with open(IMAGES_FOLDER+str(level)+'.jpg', 'wb') as handler:
                handler.write(img_data)

def load_image(filename):
    filename=IMAGES_FOLDER+str(filename)+'.jpg'
    return Image.open(filename)

def enlarge(image):
    waifu2x = Waifu2x(gpuid=-1, scale=2, noise=3)
    return waifu2x.process(image)

def gen_frames_out(current):
    pointer=0
    frame_count=0
    while(pointer<current-1):
        width = im_width * 3
        czoom_ratio=zoom_ratio
        while (width*zoom_ratio) >= im_width:
            working_frame = load_image(pointer+1).resize((im_width*3,im_width*3), Image.ANTIALIAS)
            working_frame.paste(load_image(pointer),(im_width,im_width))
            working_frame = working_frame.resize((int(math.floor(im_width*3*czoom_ratio)),int(math.floor(im_width*3*czoom_ratio))), Image.ANTIALIAS)
            nwidth, width = working_frame.size
            working_frame=working_frame.crop((math.floor((nwidth/2)-(im_width/2)),math.floor((nwidth/2)-(im_width/2)),math.floor((nwidth/2)+(im_width/2)),math.floor((nwidth/2)+(im_width/2))))
            if not exists(SCALED_FOLDER+str(frame_count).zfill(8)+".jpg"):
                enlarge(working_frame).save(SCALED_FOLDER+str(frame_count).zfill(8)+".jpg")
            frame_count=frame_count+1
            czoom_ratio=czoom_ratio*zoom_ratio
        pointer=pointer+1

def gen_video():
    output = ( ffmpeg
    .input(SCALED_FOLDER+'*.jpg', pattern_type='glob', framerate=25)
    .filter('crop',im_width*2,int(math.floor((im_width*2)/1.77777)))
    .output('gridcosmpy.mp4')
    .run())

session = requests.session()
session.mount('https://', TLSAdapter())
current=get_current(session=session)
sync_images(current,session=session)
gen_frames_out(current)
gen_video()
