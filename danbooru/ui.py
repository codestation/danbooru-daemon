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

import time
from os import makedirs
from PyQt4 import QtCore, QtGui
from os.path import basename, splitext, exists, join, expanduser

from danbooru.models import Post


class ThumbnailCache(object):

    MAX_SIZE = 256

    def __init__(self, path):
        self.path = path
        makedirs(path, exist_ok=True)

    def getThumbnail(self, path):
        if exists(path):
            base = splitext(basename(path))[0]
            image = QtGui.QImage()
            if image.load(join(self.path, base + ".png"), format="png"):
                return image
            else:
                image = self.scaleImage(path, self.MAX_SIZE)
                image.save(join(self.path, base + ".png"), format="png")
                return image
        else:
            #TODO: get preview image from the Internet
            pass

    def scaleImage(self, path, length):
        image_reader = QtGui.QImageReader(path)
        image_width = image_reader.size().width()
        image_height = image_reader.size().height()
        if image_width > image_height:
            image_height = int(length * 1.0 / image_width * image_height)
            image_width = length
        elif image_width < image_height:
            image_width = int(length * 1.0 / image_height * image_width)
            image_height = length
        else:
            image_width = length
            image_height = length
        image_reader.setScaledSize(QtCore.QSize(image_width, image_height))
        return QtGui.QImage(image_reader.read())


class ThumbnailWorker(QtCore.QThread):

    makeIconSignal = QtCore.pyqtSignal(Post, QtGui.QImage)
    setStatusSignal = QtCore.pyqtSignal()
    clearWidgetListSignal = QtCore.pyqtSignal()
    abort = False

    def __init__(self, ListWidget, basedir, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.widget = ListWidget
        self.basedir = basedir
        user_path = expanduser("~")
        self.thumbnail_dir = join(user_path, ".cache/danbooru-daemon/thumbnails")
        makedirs(self.thumbnail_dir, exist_ok=True)

    def setData(self, query, db):
        self.query = query
        self.db = db

    def stop(self):
        self.abort = True

    def run(self):
        self.abort = False
        th = ThumbnailCache(self.thumbnail_dir)

        self.clearWidgetListSignal.emit()

        if self.query.get('site'):
            self.db.setHost(host=None, alias=self.query['site'])
        else:
            self.db.clearHost()
        if self.query.get('tags'):
            posts = self.db.getANDPosts(self.query['tags'], limit=200, extra_items=self.query)
        else:
            posts = self.db.get_posts(200, extra_items=self.query)

        if not posts:
            self.setStatusSignal.emit()
        else:
            for post in posts:
                if self.abort:
                    time.sleep(1)
                    break
                img = post.image
                full_path = join(self.basedir, img.md5[0], img.md5 + img.file_ext)
                image = th.getThumbnail(full_path)
                self.makeIconSignal.emit(post, image)


def getScaledPixmap(image, size):
    if size.width() > size.height():
        width = size.height()
    else:
        width = size.width()
    size = image.size()
    if size.width() < size.height():
        img = image.scaledToHeight(width, QtCore.Qt.SmoothTransformation)
    else:
        img = image.scaledToWidth(width, QtCore.Qt.SmoothTransformation)
    return QtGui.QPixmap.fromImage(img)
