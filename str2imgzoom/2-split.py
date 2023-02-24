#!/bin/python3
import textwrap
f = open("1-book.txt", "r")
o = open("2-book.txt", "a")
text=f.read()
maxchars = 100
wrapper = textwrap.TextWrapper(width=maxchars)
word_list = wrapper.wrap(text=text)

for element in word_list:
    o.write(element+"\n")
