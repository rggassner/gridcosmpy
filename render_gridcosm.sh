#!/bin/bash
mkdir -p original
mkdir -p input_upscaled
mkdir -p output_frames
mkdir -p reversed
mkdir -p reversed/tmp
current=`wget -O - https://www.sito.org/cgi-bin/gridcosm/gridcosm 2> /dev/null | grep "<title>SITO - Gridcosm level .*</title>" | sed "s/[^0-9]//g"`
current=$((current-1))
download_dir="original"
for image in `seq -f "%03g" 0 $current`
do
        if [[ ! -f "$download_dir/$image-f.jpg" ]]
        then
                wget https://www.sito.org/synergy/gridcosm/pieces/$image-f.jpg --directory-prefix=$download_dir
        fi
done
echo Synced
rm gridcosmpy.mp4
rm gridcosmpy_reversed.mp4
#rm input_upscaled/*
#rm output_frames/*
rm reversed/tmp/*
rm reversed/*.jpg
for file in original/*.jpg; do
  if [ -f "$file" ]; then
    bfilename=$(basename "$file" .jpg)
    if [ ! -f "input_upscaled/$bfilename.png" ]; then
      echo "$file upscaling"
      ./waifu2x-ncnn-vulkan/build/waifu2x-ncnn-vulkan -f png -i "$file" -o "input_upscaled/$bfilename.png" -s 4 -n 3 -g 0
    else
      echo "$file already converted"
    fi
  else
    echo "Error: $file not found or is not a regular file."
  fi
done
./gridcosmpy.py -r 3
