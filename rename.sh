#!/bin/bash
cd images
for file in `ls -1`
do
	number=`echo $file | cut -d "-" -f 1 | bc`
	mv $file $number.jpg
done
