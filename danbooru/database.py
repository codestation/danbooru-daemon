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
#import logging

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
        self.board_id = None
        try:
            f = open("danbooru-db.sql")
            self.conn.executescript(f.read())
            self.conn.commit()
        except IOError:
            pass
        
    def dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
    
    def clearHost(self):
        self.board_id = None
        
    def getHost(self, board_id):
        self.conn.row_factory = self.dict_factory
        row = self.conn.execute('SELECT name, alias FROM board WHERE id=%i' % board_id)
        self.conn.row_factory = None
        result = row.fetchone()
        return result
        
    def setHost(self, host, alias):
        if host:
            try:
                self.conn.execute('INSERT INTO board (name, alias) VALUES (?, ?)', (host, alias));
                self.conn.commit()
            except sqlite3.IntegrityError:
                pass
        self.conn.row_factory = self.dict_factory
        rows = self.conn.execute('SELECT name, id, alias FROM board ORDER BY id ASC')
        self.conn.row_factory = None
        self.hosts = [x for x in rows]
        for item in self.hosts:
            if item['name'] == host or item['alias'] == alias:
                self.board_id = item['id']
                break
        
    def updatePosts(self, posts, commit=True):
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
            
    def addTags(self, posts, delete=True, commit=True):
        for post in posts:
            rows = self.conn.execute('SELECT tag_name, post_id FROM post_tag WHERE post_id=:id AND board_id=%i' % self.board_id, post)
            exists = [x[0] for x in rows]
            ins = [x for x in post['tags'] if x not in exists]
            if ins:
                self.insertTags(post['id'], ins, commit)
            if delete:
                dele = [(x,) for x in exists if x not in post['tags']]
                if dele:
                    self.deleteTags(post['id'], dele, commit)
        if commit:
            self.conn.commit()
            
    def addPosts(self, posts, update=True):
        id_list = [x['id'] for x in posts]
        placeholders = ', '.join('?' for unused in id_list)
        rows = self.conn.execute('SELECT id FROM post WHERE board_id=%i AND id IN (%s)' % (self.board_id, placeholders), id_list)
        exists = [x[0] for x in rows]
        if update:
            upd = [x for x in posts if x['id'] in exists]
            self.updatePosts(upd, commit=False)
            
        insert = [x for x in posts if not x['id'] in exists]
        self.insertPosts(insert, commit=False)
        self.addTags(posts, commit=False)
        self.conn.commit()
        if update:
            return (len(insert), len(upd))
        else:
            return (len(insert), )
        
    def preparePost(self, post):
        row = self.conn.execute('SELECT tag_name as tags FROM post_tag WHERE post_id =:id AND board_id=:board_id', post)
        post['tags'] = [x[0] for x in row]
        post['rating'] = self.ratings[post['rating']]
        host = self.getHost(post['board_id'])
        post['board_url'] = host['name']
        post['board_alias'] = host['alias']
        return post

    def getPost(self, file):        
        for host in self.hosts:
            self.conn.row_factory = self.dict_factory
            row = self.conn.execute('SELECT * from post WHERE board_id=%i AND md5 = ?' % host['id'], [os.path.splitext(file)[0]])
            self.conn.row_factory = None
            data = row.fetchone()
            if data:
                return self.preparePost(data)
            
    def fileExists(self, md5):
        row = self.conn.execute('SELECT md5 FROM post WHERE md5=? LIMIT 1', [md5])
        data = row.fetchone()
        return bool(data)
        
    def getORPosts(self, tags, limit):        
        placeholders = ', '.join('?' for unused in tags)
        sql = ('SELECT * FROM post WHERE id IN (SELECT DISTINCT post_id from ' +
              'post_tag WHERE tag_name IN (%s)) GROUP BY md5 ORDER BY id DESC')
        if limit > 0:
            sql += ' LIMIT %i' % limit            
        self.conn.row_factory = self.dict_factory
        rows = self.conn.execute(sql % placeholders, tags)
        self.conn.row_factory = None
        return [x for x in rows]
    
    def dictToQuery(self, items, first="AND"):
        sql = ""
        if items:
            if items.get("width"):                
                sql += "width %s %i" % (items['width_type'], items['width'])
            if items.get("height"):
                if sql: sql = " AND " + sql
                sql += "height %s %i" % (items['height_type'], items['height'])
            if items.get("rating"):
                for char, name in self.ratings.items():
                    if name == items['rating']:
                        if sql: sql = " AND " + sql
                        sql += "rating = '%s'" % char
                        break
            if sql:
                sql = " %s %s" % (first, sql)
        return sql
    
    def getANDPosts(self, tags, limit=100, extra_items=None):
        self.conn.row_factory = self.dict_factory        
        placeholders = ', '.join('?' for unused in tags)        
        extra_sql = self.dictToQuery(extra_items)
        if self.board_id:            
            sql = ("SELECT * FROM post WHERE board_id=%i AND id IN (SELECT post_id FROM post_tag " + 
                   "WHERE board_id=%i AND tag_name IN (%s) GROUP BY post_id HAVING COUNT(tag_name) = %i) " + 
                   "%s GROUP BY md5 ORDER BY id DESC")
        else:
            sql = ("SELECT * FROM post WHERE id IN (SELECT post_id FROM post_tag " + 
                   "WHERE tag_name IN (%s) GROUP BY post_id HAVING COUNT(tag_name) = %i) " + 
                   "%s GROUP BY md5 ORDER BY id DESC")
        if limit > 0:
            sql += ' LIMIT %i' % limit
        if self.board_id:
            rows = self.conn.execute(sql % (self.board_id, self.board_id, placeholders, len(tags), extra_sql), tags)
        else:
            rows = self.conn.execute(sql % (placeholders, len(tags), extra_sql), tags)
        self.conn.row_factory = None
        return [self.preparePost(data) for data in rows]
    
    def getPosts(self, limit=100, offset=0, extra_items=None):
        self.conn.row_factory = self.dict_factory
        if self.board_id:
            extra_sql = self.dictToQuery(extra_items)
            rows = self.conn.execute('SELECT * FROM post WHERE board_id=%i %s ORDER BY id DESC LIMIT ? OFFSET ?' % (self.board_id, extra_sql), (limit, offset))
        else:
            extra_sql = self.dictToQuery(extra_items, first="WHERE")
            rows = self.conn.execute('SELECT * FROM post %s GROUP BY md5 ORDER BY id DESC LIMIT ? OFFSET ?' % extra_sql, (limit, offset))
        self.conn.row_factory = None
        return [self.preparePost(data) for data in rows]
        
    def getFiles(self, limit, offset):
        self.conn.row_factory = self.dict_factory
        if self.board_id:
            rows = self.conn.execute('SELECT file_url, md5 FROM post WHERE board_id=%i ORDER BY id DESC LIMIT ? OFFSET ?' % self.board_id, (limit, offset))
        else:
            rows = self.conn.execute('SELECT file_url, md5 FROM post ORDER BY id DESC LIMIT ? OFFSET ?', (limit, offset))
        return [file for file in rows]
