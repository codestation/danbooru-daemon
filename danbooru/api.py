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
import time
import socket
import hashlib
import logging
import urllib.parse
import xml.dom.minidom
from urllib.request import urlopen
from http.client import HTTPException
from urllib.error import URLError, HTTPError

from danbooru.error import DanbooruError
from danbooru.utils import filter_posts


class GenericApi(object):

    WAIT_TIME = 1.2

    def __init__(self, host):
        self.host = host
        self._delta_time = 0

    def _wait(self):
        self._delta_time = time() - self._delta_time
        if self._delta_time < self.WAIT_TIME:
            time.sleep(self.WAIT_TIME - self._delta_time)

    def _getData(self, url):
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
        return response.read().decode('utf8')

    def getDictFromJSON(self, url):
        return json.loads(self._getData(url))

    def getDictFromXML(self, url):
        dom = xml.dom.minidom.parseString(self._getData(url))
        posts = []
        if dom.childNodes:
            for node in dom.childNodes[0].childNodes:
                if isinstance(node, xml.dom.minidom.Element):
                    posts.append(dict(node.attributes.items()))
        return posts

    def _processPosts(self, posts, query=None, blacklist=None, whitelist=None):
        for post in posts:
            # rename key id -> post_id
            post['post_id'] = post.pop('id')
            #remove all extra spaces
            post['tags'] = re.sub(' +', ' ', post['tags']).split(' ')
            #remove duplicates
            post['tags'] = list(set(post['tags']))
            if not "has_comments" in post:
                post['has_comments'] = None
            if not "has_notes" in post:
                post['has_notes'] = None
            if "created_at" in post and isinstance(post['created_at'], dict):
                post['created_at'] = time.strftime(
                    "%a, %d %b %Y %H:%M:%S +0000",
                    time.gmtime(post['created_at']['s'])
                )

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

    def setLogin(self, login, password, salt):
        sha1data = hashlib.sha1((salt % password).encode('utf8'))
        self.login = login
        self.hash = sha1data.hexdigest()


class DanbooruApi(GenericApi):

    POST_API = "/post/index.json"
    TAG_API = "/tag/index.json"
    POOL_API = "/pool/index.json"
    POOL_LIST_API = "/pool/show.json"

    def getPostsPage(self, tags, query, page, limit, blacklist=None, whitelist=None):
        args = urllib.parse.urlencode({
            'tags': tags,
            'page': page,
            'limit': limit,
            'login': self.login,
            'password_hash': self.hash,
        })
        url = "%s%s?%s" % (self.host, self.POST_API, args)
        return self.getPosts(url, query, blacklist, whitelist)

    def getPoolsPage(self, page):
        args = urllib.parse.urlencode({
            'page': page,
            'login': self.login,
            'password_hash': self.hash,
        })
        url = "%s%s?%s" % (self.host, self.POOL_API, args)
        return self.getPools(url)

    def getPoolPostsPage(self, pool_id, page):
        args = urllib.parse.urlencode({
            'id': pool_id,
            'page': page,
            'login': self.login,
            'password_hash': self.hash,
        })
        url = "%s%s?%s" % (self.host, self.POOL_LIST_API, args)
        return self.getPoolPosts(url)

    def getPostsBefore(self, post_id, tags, query, limit, blacklist=None, whitelist=None):
        args = urllib.parse.urlencode({
            'before_id': post_id,
            'tags': tags,
            'limit': limit,
            'login': self.login,
            'password_hash': self.hash,
        })
        url = "%s%s?%s" % (self.host, self.POST_API, args)
        return self.getPosts(url, query, blacklist, whitelist)

    def getTagsBefore(self, post_id, tags, limit):
        pass

    def getPosts(self, url, query, blacklist, whitelist):
        posts = self.getDictFromJSON(url)
        return self._processPosts(posts, query, blacklist, whitelist)

    def getPoolPosts(self, url):
        pool = self.getDictFromJSON(url)
        return [post['id'] for post in pool['posts']]

    def getPools(self, url):
        pools = self.getDictFromJSON(url)
        for pool in pools:
            # rename key id -> pool_id
            pool['pool_id'] = pool['id']
            del pool['id']
        return pools

    def tagList(self, name):
        args = urllib.parse.urlencode({
            'name': name,
            'login': self.login,
            'password_hash': self.hash,
        })
        url = "%s%s?%s" % (self.host, self.TAG_API, args)
        return self.getDictFromJSON(url)


class GelbooruAPI(GenericApi):

    POST_API = "/index.php?page=dapi&s=post&q=index"

    def getPostsPage(self, tags, query, page, limit, blacklist=None, whitelist=None):
        args = urllib.parse.urlencode({
            'tags': tags,
            'pid': page,
            'limit': limit,
            'login': self.login,
            'password_hash': self.hash,
        })
        url = "%s%s?%s" % (self.host, self.POST_API, args)
        return self.getPosts(url, query, blacklist, whitelist)

    def getPosts(self, url, query, blacklist, whitelist):
        posts = self.getDictFromXML(url)
        return self._processPosts(posts, query, blacklist, whitelist)
