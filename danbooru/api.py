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
import time
import hashlib
import logging
import urllib.parse
import xml.dom.minidom

import requests

from danbooru.utils import filter_posts


class GenericApi(object):
    """Generic class for use into other imageboard classes"""

    def __init__(self, host):
        self.host = host

    def setLogin(self, login, password, salt='%s'):
        """Sets the username and hashed password with an optional salt"""
        sha1data = hashlib.sha1((salt % password).encode('utf8'))
        self.login = login
        self.hash = sha1data.hexdigest()

    def xmlToDictList(self, text):
        """Converts a xml page into a dict list"""
        dom = xml.dom.minidom.parseString(text)
        posts = []
        if dom.childNodes:
            for node in dom.childNodes[0].childNodes:
                if isinstance(node, xml.dom.minidom.Element):
                    posts.append(dict(node.attributes.items()))
        return posts

    def processPosts(self, posts, query=None):
        """
        Clean the post list by adding missing values and removing posts
        from the list that are in the blacklist
        """
        for post in posts:
            # rename key id -> post_id
            post['post_id'] = post.pop('id')
            # remove all extra spaces
            post['tags'] = re.sub(' +', ' ', post['tags']).split(' ')
            # remove duplicates
            post['tags'] = list(set(post['tags']))
            # default values for has_*
            post['has_comments'] = post.get('has_comments', None)
            post['has_notes'] = post.get('has_notes', None)

            if 'created_at' in post and isinstance(post['created_at'], dict):
                post['created_at'] = time.strftime(
                    "%a, %d %b %Y %H:%M:%S +0000",
                    time.gmtime(post['created_at']['s'])
                )

        filtered_posts = []
        if query and 'blacklist' in query:
            post_count = len(posts)
            # delete posts that have tags in blacklist
            for post in posts:
                # but exclude those in the whitelist
                if 'whitelist' in query:
                    if (not set(post['tags']).intersection(query['blacklist'])
                            or set(post['tags']).intersection(query['whitelist'])):
                        filtered_posts.append(post)
                else:
                    if (not set(post['tags']).intersection(query['blacklist'])
                            or set(post['tags'])):
                        filtered_posts.append(post)
            # calculate the remaining post count
            post_count -= len(filtered_posts)
            if post_count > 0:
                logging.debug("%i posts filtered by the blacklist", post_count)

        return filter_posts(filtered_posts, query) if query else filtered_posts

    def getPostsByType(self, tags, query, post_type, type_id, limit):
        r = requests.get(urllib.parse.urljoin(self.host, self.POST_API), params={
            post_type: type_id,
            'tags': tags,
            'limit': limit,
            'login': self.login,
            'password_hash': self.hash,
        })
        return self.processPosts(r.json(), query)


class DanbooruAPI(GenericApi):
    POST_API = "/post/index.json"
    TAG_API = "/tag/index.json"
    POOL_API = "/pool/index.json"
    POOL_LIST_API = "/pool/show.json"

    def getPoolsPage(self, page):
        args = {
            'page': page,
            'login': self.login,
            'password_hash': self.hash,
        }
        r = requests.get(urllib.parse.urljoin(self.host, self.POOL_LIST_API), params=args)
        return [post['id'] for post in r.json()['posts']]

    def getPoolPostsPage(self, pool_id, page):
        r = requests.get(urllib.parse.urljoin(self.host, self.POOL_LIST_API), params={
            'id': pool_id,
            'page': page,
            'login': self.login,
            'password_hash': self.hash,
        })
        return [post['id'] for post in r.json()['posts']]

    def getPosts(self, url, query):
        print(url)
        r = requests.get(url)
        return self.processPosts(r.json(), query)

    def getPools(self, url):
        r = requests.get(url)
        pools = r.json()
        for pool in pools:
            pool['pool_id'] = pool.pop('id')
        return pools

    def tagList(self, name):
        r = requests.get(urllib.parse.urljoin(self.host, self.TAG_API), params={
            'name': name,
            'login': self.login,
            'password_hash': self.hash,
        })
        return r.json()


class GelbooruAPI(GenericApi):
    POST_API = "/index.php?page=dapi&s=post&q=index"

    def getPostsByType(self, tags, query, post_type, type_id, limit):
        r = requests.get(urllib.parse.urljoin(self.host, self.POST_API), params={
            post_type: type_id,
            'tags': tags,
            'limit': limit,
        })
        posts = self.xmlToDictList(r.text)
        return self.processPosts(posts, query)

    def getPostsPage(self, tags, query, page, limit):
        r = requests.get(urllib.parse.urljoin(self.host, self.POST_API), params={
            'tags': tags,
            'pid': page,
            'limit': limit,
        })
        posts = self.xmlToDictList(r.text)
        return self.processPosts(posts, query)
