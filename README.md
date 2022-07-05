# gridcosmpy

A python script to generate flythrough videos zooming in and out the gridcosm project.

It scrapes all images from the site,  upscales the image quality, creates intermediary frames, and uses ffmpeg to generate videos. Multiprocessing is available.

You might want to hardcode the variable "current" to a low number, like 10, to have a small preview before a full run.

# Dependencies

apt install libvulkan-dev swig cmake python3-pip ninja-build

pip install waifu2x-ncnn-vulkan-python ffmpeg-python

# Rescaling externaly

If you want to rescale images externaly using https://github.com/nihui/waifu2x-ncnn-vulkan

waifu2x-ncnn-vulkan -i downloaded/ -o images/ -s 8 -n 3 -g 0

Visit Gridcosm and make a donation! https://www.sito.org/synergy/gridcosm/

This amazing project has been running since 1997.
