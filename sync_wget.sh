#!/bin/bash
current=`wget -O - https://www.sito.org/cgi-bin/gridcosm/gridcosm 2> /dev/null | grep "<title>SITO - Gridcosm level .*</title>" | sed "s/[^0-9]//g"`
download_dir="original"
for image in `seq -f "%03g" 0 $current`
do
        if [[ ! -f "$download_dir/$image-f.jpg" ]]
        then
                wget https://www.sito.org/synergy/gridcosm/pieces/$image-f.jpg --directory-prefix=$download_dir
        fi
done
