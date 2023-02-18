# gridcosmpy

A python script to generate flythrough videos zooming in and out the gridcosm project. Watch a demo here https://www.youtube.com/embed/kWf0khdT3Rc or here https://www.youtube.com/watch?v=fHBQec6JZWI 

It scrapes all images from the site,  upscales the image quality, creates intermediary frames, and uses ffmpeg to generate videos. Multiprocessing is available.

You might want to hardcode the variable "current" to a low number, like 10, to have a small preview before a full run.



# Dependencies

apt install libvulkan-dev swig cmake python3-pip ninja-build

pip install waifu2x-ncnn-vulkan-python ffmpeg-python

# Rescaling externaly

If you want to rescale images externaly using https://github.com/nihui/waifu2x-ncnn-vulkan

waifu2x-ncnn-vulkan -f png -i downloaded/ -o images/ -s 8 -n 3 -g 0

# Gridcosm

Gridcosm is a collaborative art project in which artists from around the world contribute images to a compounding series of graphical squares. Each level of Gridcosm is made up of nine square images arranged into a 3x3 grid. The middle image is a one-third size version of the previous level. Artists add images around that center image until a new 3x3 grid is completed, then that level itself shrinks and becomes the "seed" for the next level. This process creates an ever expanding tunnel of images, the newest level a direct result of the previous level which is a result of the previous level... and so on.

Visit Gridcosm and make a donation! https://www.sito.org/synergy/gridcosm/

This amazing project has been running since 1997.
