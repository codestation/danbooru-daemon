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

from sqlalchemy import event
from sqlalchemy.orm import scoped_session, joinedload
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.sql.expression import func, ClauseElement, distinct, not_

from danbooru.models import Board, Post, Image, Tag, Base, Pool


class Database(object):

    def __init__(self, dbname=""):
        # prepare the engine
        self.engine = create_engine("sqlite:///%s" % dbname)

        # enable foreign key support on sqlite
        def _fk_pragma_on_connect(dbapi_con, con_record):  # @UnusedVariable
            dbapi_con.execute('pragma foreign_keys=ON')
        event.listen(self.engine, 'connect', _fk_pragma_on_connect)

        # create the tables
        Base.metadata.create_all(bind=self.engine)  # @UndefinedVariable

        # create a session
        self.DBsession = scoped_session(
            sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        )

    def _cleanDict(self, model, post):
        clean = [x.name for x in model.__mapper__.columns]
        return {key: value for key, value in post.items() if key in clean}

    def _getOrCreate(self, session, model, defaults=None, **kwargs):
        instance = session.query(model).filter_by(**kwargs).first()
        if instance:
            return instance, False
        else:
            params = dict((k, v) for k, v in kwargs.items() if not isinstance(v, ClauseElement))
            if defaults:
                params.update(defaults)
            instance = model(**params)
            session.add(instance)
            return instance, True

    def _dict2ToQuery(self, query, items):
        q = query.join(Post.image)
        if items.get("width"):
            if items['width_type'] == "<":
                q = q.filter(Image.width < items['width'])
            elif items['width_type'] == ">":
                q = q.filter(Image.width > items['width'])
            else:
                q = q.filter(Image.width == items['width'])

        elif items.get("height"):
            if items['height_type'] == "<":
                q = q.filter(Image.height < items['height'])
            elif items['height_type'] == ">":
                q = q.filter(Image.height > items['height'])
            else:
                q = q.filter(Image.height == items['height'])

        elif items.get("rating"):
            q = q.filter(Post.rating == items['rating'])

        elif items.get("pool"):
            q = q.join(Post.pools)
            q = q.filter(Pool.pool_id == items['pool'])

        elif items.get("ratio"):
            ratio = items['ratio_width'] * 1.0 / items['ratio_height']
            q = q.filter(Image.width * 1.0 / Image.height == ratio)

        return q

    def clearHost(self):
        self.board = None

    def setHost(self, host, alias):
        s = self.DBsession()
        if host:
            board, created = self._getOrCreate(s, Board, **{'host': host, 'alias': alias})
            if created:
                s.add(board)
                s.commit()
        else:
            board = s.query(Board).filter_by(alias=alias).first()
            if not board:
                return False
        self.board = board
        return True

    def savePosts(self, posts):
        results = {'tags': 0, 'images': 0, 'posts': 0}
        s = self.DBsession()

        for post in posts:
            if 'file_url' not in post:
                continue
            #fix file extension
            defaults = {'file_ext': os.path.splitext(post['file_url'])[1]}
            if defaults['file_ext'] == ".jpeg":
                defaults['file_ext'] = ".jpg"

            clean_image = self._cleanDict(Image, post)
            defaults.update(clean_image)

            img, created = self._getOrCreate(s, Image, defaults, **{'md5': post['md5']})
            results['images'] += int(created)

            tags = [self._getOrCreate(s, Tag, **{'name': v}) for v in post['tags']]
            results['tags'] += sum(created for tag, created in tags)

            defaults = {'image': img, 'tags': [tag for tag, created in tags]}
            clean_post = self._cleanDict(Post, post)
            defaults.update(clean_post)

            # avoid search by post_id
            del defaults['post_id']

            new_post, created = self._getOrCreate(s, Post, defaults, **{'post_id': post['post_id'], 'board': self.board})
            results['posts'] += int(created)

            s.add(new_post)
            s.flush()

        s.commit()
        return results

    def savePools(self, pools):
        s = self.DBsession()
        up_to_date = False
        created = 0
        updated = 0

        for pool in pools:
            clean_pool = self._cleanDict(Pool, pool)
            clean_pool.update({'modified': 1})
            new_pool, created = self._getOrCreate(s, Pool, clean_pool, **{'pool_id': pool['pool_id'], 'board': self.board})
            if not created:
                if new_pool.updated_at != pool['updated_at']:
                    new_pool.updated_at = pool['updated_at']
                    new_pool.post_count = pool['post_count']
                    new_pool.modified = True
                    updated += 1
                else:
                    up_to_date = True
                    break
            else:
                s.add(new_pool)
                created += 1
        s.commit()
        return created, updated, up_to_date

    def savePool(self, pool_id, posts_id=None, modified=False):
        s = self.DBsession()
        pool = s.query(Pool).filter_by(board=self.board, pool_id=pool_id).first()
        if not pool:
            return
        total = 0
        if posts_id:
            posts = s.query(Post).filter(Post.post_id.in_(posts_id), Post.board == self.board).all()
            pool.posts += posts
            total = len(posts)
        elif modified:
            pool.posts = []
        pool.modified = modified
        s.commit()
        return total

    def getPost(self, file):
        s = self.DBsession()
        md5 = os.path.splitext(file)[0]
        q = s.query(Post).join(Post.image)
        return q.filter_by(md5=md5).first()

    def fileExists(self, md5):
        return bool(self.DBsession().query(Image).filter_by(md5=md5).first())

    #FIXME: unused?
    def getORPosts(self, tags, limit):
        q = self.DBsession().query(Post).join(Post.tags)
        q = q.filter(Tag.name.in_(tags)).group_by(Post.image_id)
        q = q.order_by(Post.post_id.desc())
        return q.limit(limit).all()

    def getANDPosts(self, tags, limit=100, extra_items=None):
        q = self.DBsession().query(Post).join(Post.tags)
        if extra_items:
            q = self._dict2ToQuery(q, extra_items)
        if self.board:
            q = q.filter(Post.board == self.board)
        q = q.filter(Tag.name.in_(tags)).group_by(Post.image_id)
        q = q.having(func.count(distinct(Tag.name)) == len(tags))
        q = q.order_by(Post.post_id.desc())
        if limit:
            q = q.limit(limit)
        return q.all()

    def getPosts(self, limit=100, offset=0, extra_items=None):
        q = self.DBsession().query(Post)
        if extra_items:
            q = self._dict2ToQuery(q, extra_items)
        q = q.order_by(Post.post_id.desc())
        return q.limit(limit).offset(offset).all()

    def getPools(self, limit=100, offset=0, extra_items=None):
        q = self.DBsession().query(Pool).filter_by(modified=True)
        if extra_items:
            q = self._dict2ToQuery(q, extra_items)
        q = q.order_by(Pool.updated_at.asc())
        return q.limit(limit).offset(offset).all()

    def getFiles(self, limit, offset):
        q = self.DBsession().query(Post).join(Post.image)
        if self.board:
            q = q.filter(Post.board == self.board)
        q = q.options(joinedload('image'))
        return q.limit(limit).offset(offset).all()

    def deletePostsByTags(self, blacklist, whitelist):
        if not blacklist:
            return 0

        s = self.DBsession()

        subq = s.query(Post.id).distinct().join(Post.tags)
        subq = subq.filter(Tag.name.in_(whitelist))

        q = s.query(Post.id).distinct().join(Post.tags)
        q = q.filter(Tag.name.in_(blacklist)).except_(subq)

        d = s.query(Post).filter(Post.id.in_(q))
        post_count = d.delete(synchronize_session='fetch')

        # delete the image refs without posts from the database
        q = s.query(Post.image_id).distinct()
        d = s.query(Image.id).filter(not_(Image.id.in_(q)))
        img_count = d.delete(synchronize_session='fetch')

        q = s.query(Tag.id).join(Post.tags)
        d = s.query(Tag.id).filter(not_(Tag.id.in_(q)))
        tag_count = d.delete(synchronize_session='fetch')

        s.commit()
        return (post_count, img_count, tag_count)
