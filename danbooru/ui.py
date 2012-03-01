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

from os import makedirs
from PyQt4 import QtCore, QtGui
from os.path import basename, splitext, exists, join, expanduser

from danbooru import utils


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

    makeIconSignal = QtCore.pyqtSignal(QtGui.QListWidgetItem, QtGui.QImage)
    abort = False

    def __init__(self, ListWidget, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.widget = ListWidget
        user_path = expanduser("~")
        self.thumbnail_dir = join(user_path, ".cache/danbooru-daemon/thumbnails")
        makedirs(self.thumbnail_dir, exist_ok=True)

    def stop(self):
        self.abort = True

    def run(self):
        self.abort = False
        th = ThumbnailCache(self.thumbnail_dir)
        generator = utils.list_generator(self.widget)
        for item in generator:
            if self.abort: break
            post = item.data(QtCore.Qt.UserRole)
            full_path = utils.post_abspath(post)
            image = th.getThumbnail(full_path)
            self.makeIconSignal.emit(item, image)
