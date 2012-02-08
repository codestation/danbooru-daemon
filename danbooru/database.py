import os
import sqlite3

class Database(object):
    
    ratings = {'s': 'Safe', 'q': 'Questionable', 'e': 'Explicit'}

    def __init__(self, dbname):
        self.dbname = dbname        
        self.conn = sqlite3.connect(dbname)
        
    def updatePosts(self, posts, commit=True):
        self.conn.executemany('UPDATE post SET width=:width,height=:height,' + 
                              'file_size=:file_size,file_url=:file_url,author=:author,' + 
                              'creator_id=:creator_id,rating=:rating,source=:source,' + 
                              'score=:score,parent_id=:parent_id,status=:status,' + 
                              'change=:change,md5=:md5,created_at=:created_at,' + 
                              'sample_url=:sample_url,sample_width=:sample_width,' + 
                              'sample_height=:sample_height,preview_url=:preview_url,' + 
                              'preview_width=:preview_width,preview_height=:preview_height,' + 
                              'has_notes=:has_notes,has_comments=:has_comments,' + 
                              'has_children=:has_children WHERE id=:id', posts)
        if commit:            
            self.conn.commit()
        
    def insertPosts(self, posts, commit=True):
        self.conn.executemany('INSERT INTO post (id,width,height,file_size,file_url,author,creator_id,rating,source,' + 
                      'score,parent_id,status,change,md5,created_at,sample_url,sample_width,sample_height,' + 
                      'preview_url,preview_width,preview_height,has_notes,has_comments,has_children) VALUES ' + 
                      '(:id,:width,:height,:file_size,:file_url,:author,:creator_id,:rating,:source,' + 
                      ':score,:parent_id,:status,:change,:md5,:created_at,:sample_url,:sample_width,:sample_height,' + 
                      ':preview_url,:preview_width,:preview_height,:has_notes,:has_comments,:has_children)', posts)
        if commit:
            self.conn.commit()
            
    def deleteTags(self, post_id, tags, commit=True):
        self.conn.executemany('DELETE FROM post_tag WHERE post_id=%i AND tag_name=?' % post_id, tags)
        if commit:
            self.conn.commit()
            
    def insertTags(self, post_id, tags, commit=True):
        self.conn.executemany('INSERT INTO post_tag (post_id, tag_name) VALUES (%i, ?)' % post_id, [(x,) for x in tags])
        if commit:
            self.conn.commit()
            
    def addTags(self, posts, delete=True, commit=True):
        for post in posts:
            rows = self.conn.execute('SELECT tag_name FROM post_tag WHERE post_id=:id', post)
            exists = [x[0] for x in rows]            
            ins = [x for x in post['tags'] if x not in exists]
            self.insertTags(post['id'], ins, False)
            
            if delete:
                dele = [x for x in exists if x not in post['tags']]
                self.deleteTags(post['id'], dele, False)
        if commit:
            self.conn.commit()
            
    def addPosts(self, posts, update=True, commit=True):
        id_list = [x['id'] for x in posts]
        placeholders = ', '.join('?' for unused in id_list)
        rows = self.conn.execute('SELECT id FROM post WHERE id IN (%s)' % placeholders, id_list)
        exists = [x[0] for x in rows]        

        if update:
            upd = [x for x in posts if x['id'] in exists]
            self.updatePosts(upd, False)
            
        insert = [x for x in posts if not x['id'] in exists]
        self.insertPosts(insert, False)
        self.addTags(posts, False)
        if commit:
            self.conn.commit()
        return len(insert)

    def getPost(self, file):
        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d
        
        self.conn.row_factory = dict_factory
        row = self.conn.execute('SELECT * from post WHERE md5 = ?', [os.path.splitext(file)[0]])
        data = row.fetchone()
        self.conn.row_factory = None
        row = self.conn.execute('SELECT tag_name FROM post_tag WHERE post_id =:id', data)
        data['tags'] = [x[0] for x in row]
        data['rating'] = self.ratings[data['rating']]
        return data
                
    def getFiles(self, limit, offset):
        rows = self.conn.execute('SELECT file_url, md5 FROM post ORDER BY id DESC LIMIT ? OFFSET ?', (limit, offset))
        return [{'file_url':x[0], 'md5':x[1]} for x in rows]
