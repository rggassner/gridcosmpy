# gridcosmpy

A python script to generate flythrough videos zooming in and out from the gridcosm project.

It scraps all images from the site, creates intermediary images, upscales the image quality and uses ffmpeg to generate videos.

Warning, the process takes several days. You might want to hardcode the variable current to a low number, like 10, to have a small preview.

#Dependencies

apt install libvulkan-dev swig cmake

pip install waifu2x-ncnn-vulkan-python python-ffmpeg

Visit Gridcosm and make a donation! https://www.sito.org/synergy/gridcosm/

This amazing project has been running since 1997.

