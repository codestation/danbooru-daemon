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
from os.path import exists, join, dirname, abspath


def list_generator(list_widget):
    for i in range(list_widget.count()):
        yield list_widget.item(i)


def parse_dimension(term, dim):
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


def parse_query(text):
    query = {}
    query['tags'] = []

    if isinstance(text, list):
        items = text
    else:
        items = re.sub(' +', ' ', text).split(' ')

    try:
        for item in items:
            if item.startswith("site:"):
                query['site'] = item.split(":")[1]
            elif item.startswith("rating:"):
                query['rating'] = item.split(":")[1]
            elif item.startswith("width:"):
                query.update(parse_dimension(item, "width"))
            elif item.startswith("height:"):
                query.update(parse_dimension(item, "height"))
            elif item.startswith("ratio:"):
                query['ratio'] = item.split(":", 1)[1]
                query['ratio_width'] = int(item.split(":")[1])
                query['ratio_height'] = int(item.split(":")[2])
            elif item.startswith("limit:"):
                query['limit'] = item.split(":")[1]
            else:
                query['tags'].append(item)
        return query
    except (ValueError, TypeError, IndexError):
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


def filter_posts(posts, query):

    if query.get('rating'):
        posts[:] = [post for post in posts
                    if post['rating'] == query['rating']]

    if query.get('width'):
        if query['width_type'] == "=":
            posts[:] = [post for post in posts
                        if post['width'] == query['width']]
        if query['width_type'] == "<":
            posts[:] = [post for post in posts
                        if post['width'] < query['width']]
        if query['width_type'] == ">":
            posts[:] = [post for post in posts
                        if post['width'] > query['width']]

    if query.get('height'):
        if query['height_type'] == "=":
            posts[:] = [post for post in posts
                        if post['height'] == query['height']]
        if query['height_type'] == "<":
            posts[:] = [post for post in posts
                        if post['height'] < query['height']]
        if query['height_type'] == ">":
            posts[:] = [post for post in posts
                        if post['height'] > query['height']]

    if query.get('ratio'):
        posts[:] = [post for post in posts
                    if post['width'] * 1.0 / post['height'] ==
                    query['ratio_width'] * 1.0 / query['ratio_height']]
    return posts


def remove_duplicates(posts):
    posts[:] = list(dict((x['id'], x) for x in posts).values())
    return sorted(posts, key=lambda k: k['id'], reverse=True)
