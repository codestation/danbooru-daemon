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
import socket
import hashlib
import logging

from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from http.client import HTTPException
from time import sleep, time, gmtime, strftime

from danbooru.error import DanbooruError
from danbooru.utils import filter_posts


class Api(object):

    POST_API = "/post/index.json"
    TAG_API = "/tag/index.json"

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

    def getPostsPage(self, tag, query, page, limit, blacklist=None, whitelist=None):
        url = "%s%s?tags=%s&page=%i&limit=%i" % (self.host, self.POST_API,
            tag, page, limit) + self._loginData()
        return self.getPosts(url, query, blacklist, whitelist)

    def getPostsBefore(self, post_id, tag, query, limit, blacklist=None, whitelist=None):
        url = "%s%s?before_id=%i&tags=%s&limit=%i" % (self.host, self.POST_API,
              post_id, tag, limit) + self._loginData()
        return self.getPosts(url, query, blacklist, whitelist)

    def getTagsBefore(self, post_id, tags, limit):
        pass

    def getPosts(self, url, query, blacklist, whitelist):
        self._wait()

        try:
            response = urlopen(url)
        except HTTPError as ex:
            raise DanbooruError("Error %i: %s" % (ex.code, ex.msg))
        except URLError as ex:
            raise DanbooruError("%s (%s)" % (ex.reason, self.host))
        except HTTPException as ex:
            raise DanbooruError("Error: HTTPException")
        except socket.error as ex:
            raise DanbooruError("Connection error: %s" % ex)

        results = response.read().decode('utf8')
        posts = json.loads(results)
        for post in posts:
            # rename key id -> post_id
            post['post_id'] = post['id']
            del post['id']
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
                logging.debug("%i posts filtered by the blacklist", post_count)

        if query:
            return filter_posts(posts, query)
        else:
            return posts

    def tagList(self, name):
        self._wait()
        url = self.host + self.TAG_API + '?name=%s' % name + self._loginData()
        try:
            response = urlopen(url)
            results = response.read().decode('utf8')
            tags = json.loads(results)
            return tags
        except HTTPError as ex:
            raise DanbooruError("Error %i: %s" % (ex.code, ex.msg))
        except URLError as ex:
            raise DanbooruError("%s (%s)" % (ex.reason, self.host))
        except HTTPException as ex:
            raise DanbooruError("Error: HTTPException")
        except socket.error as ex:
            raise DanbooruError("Connection error: %s" % ex)
