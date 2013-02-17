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

import os
import re
import sys
import time
import logging
import hashlib
import configparser
from danbooru.error import DanbooruError

__DELTA_TIME__ = 0
__WAIT_TIME__ = 1.2


def delay(method):
    def wrapper(*args, **kwargs):
        global __DELTA_TIME__
        __DELTA_TIME__ = time.time() - __DELTA_TIME__
        if __DELTA_TIME__ < __WAIT_TIME__:
            time.sleep(__WAIT_TIME__ - __DELTA_TIME__)
        method(*args, **kwargs)
    return wrapper

_UNSET = object()


class Settings(object):

    def __init__(self, configfile):
        self.config = configparser.ConfigParser(interpolation=None)
        if not self.config.read(configfile):
            raise DanbooruError('No config loaded')

    def _setValue(self, key, section):
        if isinstance(key, tuple):
            if key[1] == int:
                value = self.config.getint(section, key[0])
            elif key[1] == bool:
                value = self.config.getboolean(section, key[0])
            else:
                logging.warning("Unknown type: %s", key[1])
                value = self.config.get(section, key[0])
            setattr(self, key[0], value)
        else:
            value = self.config.get(section, key)
            setattr(self, key, value)
        return value

    def loadValue(self, key, section, default=_UNSET):
        if isinstance(key, list):
            return {k: self._loadValue(k, section, default) for k in key}
        else:
            return self._loadValue(key, section, default)

    def _loadValue(self, key, section, default=_UNSET):
        try:
            return self._setValue(key, section)
        except configparser.NoOptionError:
            if section not in ['general', 'default']:
                return self._loadValue(key, 'default', default)
            if default is _UNSET:
                raise
            else:
                logging.warning("%s isn't defined in config file", key)
                setattr(self, key, default)
                return default


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
    tags = []

    if isinstance(text, list):
        items = text
    else:
        items = re.sub(' +', ' ', text).split(' ')

    for item in items:
        try:
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
            elif item.startswith("pool:"):
                query['pool'] = item.split(":")[1]
            else:
                tags.append(item)
        except (ValueError, TypeError, IndexError):
            return item
    return tags, query


def find_resource(base, filename):
    base_path = [os.path.dirname(os.path.abspath(base)),
                 "/usr/local/share/danbooru-daemon",
                 "/usr/share/danbooru-daemon"]

    for path in base_path:
        full_path = os.path.join(path, filename)

        if os.path.exists(full_path):
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


def default_dbpath():
    user_dir = os.path.expanduser("~")
    db_dir = os.path.join(user_dir, ".local/share/danbooru-daemon")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "danbooru-db.sqlite")


def md5sum(filename):
    md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(128 * md5.block_size), b''):
            md5.update(chunk)
    return md5.hexdigest()


def db_page_query(q):
    offset = 0
    while True:
        r = False
        for elem in q.limit(1000).offset(offset):
            r = True
            yield elem
        offset += 1000
        if not r:
            break


def getExecPath():
    try:
        sFile = os.path.abspath(sys.modules['__main__'].__file__)
    except:
        sFile = sys.executable
    return os.path.dirname(sFile)


def get_resource_paths():
    return [getExecPath(),
            '/usr/local/share/danbooru-daemon',
            '/usr/share/danbooru-daemon']


def retry_if_except(func, *args, max_retries=3, exception=Exception, reraise=True):
    while True:
        try:
            return func(*args)
        except exception:
            if max_retries > 0:
                logging.warning("Exception in %s (%i tries left)", func.__name__, max_retries)
                max_retries -= 1
            else:
                if reraise:
                    raise
                else:
                    return
