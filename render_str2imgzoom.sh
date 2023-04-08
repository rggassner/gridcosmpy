#!/bin/bash
rm gridcosmpy.mp4
rm gridcosmpy_reversed.mp4
rm input/*
rm input_upscaled/*
rm output_frames/*
rm reversed/tmp/*
rm reversed/*.jpg
cp str2imgzoom/out/*[0-9].png input/
waifu2x-ncnn-vulkan-20220728-ubuntu/waifu2x-ncnn-vulkan -f png -i input/ -o input_upscaled/ -s 8 -n 3 -g 0 
./gridcosmpy.py -r 4
