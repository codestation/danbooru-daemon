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

import re
from urllib.parse import urlsplit
from os.path import basename, splitext, exists, join, dirname, abspath


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


def parseDimension(term, dim):
    query = {}
    if term[len("%s:" % dim)] == ">":
        query['%s_type' % dim] = ">"
        query[dim] = int(term.split(">")[1])
    elif term[len("%s:" % dim)] == "<":
        query['%s_type' % dim] = "<"
        query[dim] = int(term.split("<")[1])
    else:
        query['%s_type' % dim] = "="
        query[dim] = int(term.split(":")[1])
    return query


def parseQuery(text):
    query = {}
    query['tags'] = []
    items = re.sub(' +', ' ', text).split(' ')
    try:
        for item in items:
            if item.startswith("site:"):
                query['site'] = item.split(":")[1]
            elif item.startswith("rating:"):
                query['rating'] = item.split(":")[1]
            elif item.startswith("width:"):
                query.update(parseDimension(item, "width"))
            elif item.startswith("height:"):
                query.update(parseDimension(item, "height"))
            elif item.startswith("ratio:"):
                query['ratio'] = item.split(":", 1)[1]
                query['ratio_width'] = int(item.split(":")[1])
                query['ratio_height'] = int(item.split(":")[2])
            else:
                query['tags'].append(item)
        return query
    except Exception:
        return item


def find_resource(base, filename):
    base_path = [dirname(abspath(base)),
                 "/usr/local/share/danbooru-daemon",
                 "/usr/share/danbooru-daemon"]

    for path in base_path:
        full_path = join(path, filename)

        if exists(full_path):
            return full_path

    raise Exception("%s cannot be found." % filename)
