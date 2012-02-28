#!/usr/bin/python3
# -*- coding: utf-8 -*-

#   Copyright 2012 codestation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from os.path import join,basename, splitext
from urllib.parse import urlsplit

def list_generator(list_widget):
    for i in range(list_widget.count()):
        yield list_widget.item(i)
        
def post_abspath(post):
    base = post_basename(post)
    subdir = post['md5'][0]
    return join("/home/code/danbooru", subdir, base)

def post_basename(post):
    base = basename(urlsplit(post['file_url'])[2])
    #fix extension to jpg
    if splitext(base)[1] == ".jpeg":
        return post['md5'] + ".jpg"
    else:
        return post['md5'] + splitext(base)[1]
    
def scale_size(size, length):
    image_width = size[0]
    image_height = size[1]
    if image_width > image_height:
        image_height = int(length * 1.0 / image_width * image_height)
        image_width = length
    elif image_width < image_height:
        image_width = int(length * 1.0 / image_height * image_width)
        image_height = length
    else:
        image_width = length
        image_height = length
    return(image_width, image_height)

