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
            else:
                query['tags'].append(item)
        return query
    except Exception:
        return item
