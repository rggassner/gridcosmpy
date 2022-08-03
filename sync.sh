#!/bin/bash
#wget isn´t fun!
current=4565
download_dir="/gridcosmpy/original"
for image in `seq -f "%03g" 0 $current`
do
        if [[ ! -f "$download_dir/$image-f.jpg" ]]
        then
                google-chrome https://www.sito.org/synergy/gridcosm/pieces/$image-f.jpg &
                sleep 3
                xdotool search --name " - Google Chrome" windowactivate %1
                sleep 1
                xdotool key Ctrl+s
                sleep 1
                xdotool key Alt+Tab
                sleep 1
                xdotool key Alt+Tab
                sleep 1
                xdotool key Return
                sleep 1
                pkill chrome
        fi
done
