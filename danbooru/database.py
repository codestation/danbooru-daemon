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

import os
import sqlite3
import logging

class Database(object):
    
    ratings = {'s': 'safe', 'q': 'questionable', 'e': 'explicit'}
    
    post_fields = [
                 'author',
                 'change',
                 'created_at',
                 'creator_id',
                 'file_size',
                 'file_url',
                 'has_children',
                 'has_comments',# !konachan
                 'has_notes',# !konachan
                 'height',
                 'md5',
                 'parent_id',
                 'preview_height',
                 'preview_url',
                 'preview_width',
                 'rating',
                 'sample_height',
                 'sample_url',
                 'sample_width',
                 'score',                 
                 'source',
                 'status',
                 'width'
                ]

    def __init__(self, dbname):
        self.dbname = dbname        
        self.conn = sqlite3.connect(dbname)
        try:
            f = open("danbooru-db.sql")
            self.conn.executescript(f.read())
            self.conn.commit()
        except IOError:
            pass
        
    def setHost(self, host):
        try:
            self.conn.execute('INSERT INTO board (name) VALUES (?)', [host]);
        except sqlite3.IntegrityError:
            pass
        rows = self.conn.execute('SELECT name, id FROM board ORDER BY id ASC')
        self.hosts = [{'name':x[0], 'id':x[1]} for x in rows]        
        self.board_id = [x['id'] for x in self.hosts if x['name'] == host][0]
        
    def updatePosts(self, posts, board_id, commit=True):
        fields = ",".join("%s=:%s" % (x,x) for x in self.post_fields)
        self.conn.executemany('UPDATE post SET %s WHERE id=:id AND board_id=%i' % (fields, self.board_id), posts)
        if commit:            
            self.conn.commit()
        
    def insertPosts(self, posts, commit=True):
        fields = ",".join(self.post_fields)
        values = ",".join(":%s" % x for x in self.post_fields)
        self.conn.executemany('INSERT INTO post (id,board_id,%s) VALUES(:id,%i,%s)' % (fields, self.board_id, values), posts)
        if commit:
            self.conn.commit()
            
    def deleteTags(self, post_id, tags, commit=True):
        self.conn.executemany('DELETE FROM post_tag WHERE post_id=%i AND board_id=%i AND tag_name=?' % (post_id, self.board_id), tags)
        if commit:
            self.conn.commit()
            
    def insertTags(self, post_id, tags, commit=True):
        self.conn.executemany('INSERT INTO post_tag (post_id, board_id, tag_name) VALUES (%i, %i, ?)' % (post_id, self.board_id), [(x,) for x in tags])
        if commit:
            self.conn.commit()
            
    def addTags(self, posts, board_id, delete=True, commit=True):
        for post in posts:
            rows = self.conn.execute('SELECT tag_name, post_id FROM post_tag WHERE post_id=:id AND board_id=%i' % self.board_id, post)
            exists = [x[0] for x in rows]
            if exists:
                ins = [x for x in post['tags'] if x not in exists]
                self.insertTags(post['id'], ins, False)
                if delete:
                    dele = [(x,) for x in exists if x not in post['tags']]
                    if dele:
                        self.deleteTags(post['id'], dele, False)
        if commit:
            self.conn.commit()
            
    def addPosts(self, posts, update=True, commit=True):
        id_list = [x['id'] for x in posts]
        placeholders = ', '.join('?' for unused in id_list)
        rows = self.conn.execute('SELECT id FROM post WHERE board_id=%i AND id IN (%s)' % (self.board_id, placeholders), id_list)
        exists = [x[0] for x in rows]
        if update:
            upd = [x for x in posts if x['id'] in exists]
            self.updatePosts(upd, False)
            
        insert = [x for x in posts if not x['id'] in exists]
        self.insertPosts(insert, False)
        self.addTags(posts, False)
        if commit:
            self.conn.commit()
        if update:
            return (len(insert), len(upd))
        else:
            return (len(insert), )

    def getPost(self, file):
        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d
        
        for host in self.hosts:
            self.conn.row_factory = dict_factory
            row = self.conn.execute('SELECT * from post WHERE board_id=%i AND md5 = ?' % host['id'], [os.path.splitext(file)[0]])
            data = row.fetchone()
            if data:
                logging.debug("Using post from %s" % host['name'])
                self.conn.row_factory = None
                row = self.conn.execute('SELECT tag_name FROM post_tag WHERE post_id =:id AND board_id=%i' % host['id'], data)
                data['tags'] = [x[0] for x in row]
                data['rating'] = self.ratings[data['rating']]
                return data
                
    def getFiles(self, limit, offset):
        if self.board_id:
            rows = self.conn.execute('SELECT file_url, md5 FROM post WHERE board_id=%i ORDER BY id DESC LIMIT ? OFFSET ?' % self.board_id, (limit, offset))
        else:
            rows = self.conn.execute('SELECT file_url, md5 FROM post ORDER BY id DESC LIMIT ? OFFSET ?', (limit, offset))
        return [{'file_url':x[0], 'md5':x[1]} for x in rows]
