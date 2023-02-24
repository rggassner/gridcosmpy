#!/bin/bash
IFS=$'\n'
count=1
function goption {
			echo "Choose image $count: $line"
			read option
			mv tmp/img/$option.png out/$count.png
			mv tmp/scaled/$option-scaled.png out/$count-scaled.png
			rm tmp/img/*
			rm tmp/scaled/*
			count=`echo $count+1|bc -l`
}

for line in `cat 2-book.txt`
do
    	echo "working out/$count.png "
	if [[ -f "out/$count.png" ]]
       	then
    		echo "out/$count.png exists."
		count=`echo $count+1|bc -l`
	else
		if [ "$(ls -A tmp/img)" ]
		then
			goption
		else
			./4-genOptions.py "$line" $count
			goption
		fi
	fi
done
