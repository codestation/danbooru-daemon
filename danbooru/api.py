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

import json
import hashlib
from time import sleep, time
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

class Api(object):

    post_api = '/post/index.json'
    tag_api = '/tag/index.json'

    _delta_time = 0

    def __init__(self, host, username, password, salt, dbname):
        self.host = host
        self.username = username
        self.password = password
        self.salt = salt
        self.dbname = dbname
        
    def _wait(self):
        self._delta_time = time() - self._delta_time
        if self._delta_time < 1.2:
            sleep(1 - self._delta_time)

    def _loginData(self):
        sha1data = hashlib.sha1((self.salt % self.password).encode('utf8'))
        sha1_password = sha1data.hexdigest()
        return '&login=%s&password_hash=%s' % (self.username, sha1_password)
    
    def _getPosts(self, tags, page, limit):
        results = open('post.json', 'rb').read().decode('utf8')
        posts = json.loads(results)
        for post in posts:
            post['tags'] = post['tags'].split(' ')
        return posts
    
    def getPostsPage(self, tags, page, limit):
        url = self.host + self.post_api + '?tags=%s&page=%i&limit=%i' % (tags, page, limit) + self._loginData()
        return self.getPosts(url)
        
    def getPostsBefore(self, post_id, tags, limit):        
        url = self.host + self.post_api + '?before_id=%i&tags=%s&limit=%i' % (post_id, tags, limit) + self._loginData()
        return self.getPosts(url)
    
    def getTagsBefore(self, post_id, tags, limit):        
        url = self.host + self.tag_api + '?before_id=%i&tags=%s&limit=%i' % (post_id, tags, limit) + self._loginData()
        return self.getPosts(url)
        
    def getPosts(self, url):
        self._wait()
        try:
            response = urlopen(url)
            results = response.read().decode('utf8')
            posts = json.loads(results)
            for post in posts:
                post['tags'] = post['tags'].split(' ')
            return posts
        except URLError as e:
            print('\n>>> Error %s' % e.reason)
        except HTTPError as e:
            print('\n>>> Error %i: %s' % (e.code, e.msg))
        return []

    def tagList(self, name):
        self._wait()
        url = self.host + self.tag_api + '?name=%s' % name + self._loginData()
        try:
            response = urlopen(url)
            results = response.read().decode('utf8')
            tags = json.loads(results)
            return tags
        except URLError as e:
            print('\n>>> Error %i: %s' % (e.code, e.msg))
        except HTTPError as e:
            print('\n>>> Error %i: %s' % (e.code, e.msg))
        return []
