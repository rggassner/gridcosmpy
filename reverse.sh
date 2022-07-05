#!/bin/bash
ffmpeg -y -i gridcosmpy.mp4 -map 0 -c copy -f segment -segment_time 60 -reset_timestamps 1 trims/video_%05d.mp4
for f in trims/*.mp4
do
    	ffmpeg -y -i $f -vf reverse ${f/.mp4/_reversed.mp4}
done
>fileList.txt
>tmp.txt
for f in trims/*_reversed.mp4
do 
    echo file \'$f\' > tmp.txt
    cat fileList.txt >> tmp.txt
    rm fileList.txt
    mv tmp.txt fileList.txt
done
ffmpeg -y -f concat -safe 0 -i fileList.txt -c copy gridcosmpy_reversed.mp4
rm trims/*
rm fileList.txt
