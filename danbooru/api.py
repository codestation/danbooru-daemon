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
import json
import hashlib
import logging

from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from http.client import BadStatusLine
from time import sleep, time, gmtime, strftime

from danbooru.error import DanbooruError


class Api(object):

    post_api = '/post/index.json'
    tag_api = '/tag/index.json'

    WAIT_TIME = 1.2

    def __init__(self, host, username, password, salt):
        self.host = host
        self.username = username
        self.password = password
        self.salt = salt
        self._delta_time = 0
        self._login_string = None

    def _wait(self):
        self._delta_time = time() - self._delta_time
        if self._delta_time < self.WAIT_TIME:
            sleep(self.WAIT_TIME - self._delta_time)

    def _loginData(self):
        if not self._login_string:
            sha1data = hashlib.sha1((self.salt % self.password).encode('utf8'))
            sha1_password = sha1data.hexdigest()
            # save the result to use it in the next calls
            self._login_string = '&login=%s&password_hash=%s' % (self.username, sha1_password)
        return self._login_string

    def getPostsPage(self, tags, page, limit, blacklist=None, whitelist=None):
        tags = ','.join(tags)
        url = "%s%s?tags=%s&page=%i&limit=%i" % (self.host, self.post_api,
              tags, page, limit) + self._loginData()
        return self.getPosts(url, blacklist, whitelist)

    def getPostsBefore(self, post_id, tags, limit, blacklist=None, whitelist=None):
        tags = ','.join(tags)
        url = "%s%s?before_id=%i&tags=%s&limit=%i" % (self.host, self.post_api,
              post_id, tags, limit) + self._loginData()
        return self.getPosts(url, blacklist, whitelist)

    def getTagsBefore(self, post_id, tags, limit):
        pass

    def getPosts(self, url, blacklist, whitelist):
        self._wait()
        try:
            response = urlopen(url)
            results = response.read().decode('utf8')
            posts = json.loads(results)
            for post in posts:
                #remove all extra spaces
                post['tags'] = re.sub(' +', ' ', post['tags']).split(' ')
                #remove duplicates
                post['tags'] = list(set(post['tags']))
                if not "has_comments" in post:
                    post['has_comments'] = None
                if not "has_notes" in post:
                    post['has_notes'] = None
                if "created_at" in post and isinstance(post['created_at'], dict):
                    post['created_at'] = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime(post['created_at']['s']))

            if blacklist:
                post_count = len(posts)
                # delete posts that have tags in blacklist
                if whitelist:
                    # but exclude those in the whitelist
                    posts[:] = [x for x in posts if not set(x['tags']).intersection(blacklist) or set(x['tags']).intersection(whitelist)]
                else:
                    posts[:] = [x for x in posts if not set(x['tags']).intersection(blacklist) or set(x['tags'])]
                post_count = post_count - len(posts)
                if post_count > 0:
                    logging.debug("%i posts filtered by the blacklist" % post_count)

            return posts
        except (URLError, HTTPError, BadStatusLine) as e:
            if isinstance(e, HTTPError):
                raise DanbooruError("Error %i: %s" % (e.code, e.msg))
            elif isinstance(e, BadStatusLine):
                raise DanbooruError("Error: Cannot fetch from %s" % url)
            else:
                raise DanbooruError("%s (%s)" % (e.reason, self.host))

    def tagList(self, name):
        self._wait()
        url = self.host + self.tag_api + '?name=%s' % name + self._loginData()
        try:
            response = urlopen(url)
            results = response.read().decode('utf8')
            tags = json.loads(results)
            return tags
        except (HTTPError, URLError) as e:
            if isinstance(e, HTTPError):
                raise DanbooruError("Error %i: %s" % (e.code, e.msg))
            else:
                raise DanbooruError("%s (%s)" % (e.reason, self.host))
