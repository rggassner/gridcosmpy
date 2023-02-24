#!/bin/bash
cat 0-book.txt | tr -d "\n" | sed 's/¬ //g'| sed 's/  */ /g' > 1-book.txt
