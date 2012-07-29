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

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship, relation
from sqlalchemy.schema import UniqueConstraint, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base, declared_attr


Base = declarative_base()


class Model(object):
    @classmethod
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True)  # @ReservedAssignment


class Board(Model, Base):
    host = Column(String)
    alias = Column(String)
    __table_args__ = (UniqueConstraint('host', 'alias'),)


class Image(Model, Base):
    width = Column(Integer)
    height = Column(Integer)
    md5 = Column(String(32), unique=True)
    file_ext = Column(String(4))
    file_size = Column(Integer)


association_table = Table('tag_post', Base.metadata,
    Column('tag_id', Integer, ForeignKey('tag.id', ondelete="CASCADE"),
           primary_key=True),
    Column('post_id', Integer, ForeignKey('post.id', ondelete="CASCADE"),
           primary_key=True)
)


class Post(Model, Base):
    post_id = Column(Integer)
    file_url = Column(String)
    author = Column(String)
    creator_id = Column(Integer)
    rating = Column(String)
    source = Column(String)
    score = Column(Integer)
    parent_id = Column(Integer)
    status = Column(String)
    change = Column(Integer)
    created_at = Column(String)
    sample_url = Column(String)
    sample_width = Column(Integer)
    sample_height = Column(Integer)
    preview_url = Column(String)
    preview_width = Column(Integer)
    preview_height = Column(Integer)
    has_notes = Column(Integer)
    has_comments = Column(Integer)
    has_children = Column(Integer)

    board_id = Column(Integer, ForeignKey('board.id', ondelete="CASCADE"))
    image_id = Column(Integer, ForeignKey('image.id', ondelete="CASCADE"))

    board = relationship("Board")
    image = relationship("Image")

    tags = relation('Tag', secondary=association_table)

    __table_args__ = (UniqueConstraint('post_id', 'board_id'),)


class Tag(Model, Base):
    name = Column(String, nullable=False, index=True, unique=True)
