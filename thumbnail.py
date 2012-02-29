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
from os.path import join, basename, splitext, exists
from PyQt4 import QtCore, QtGui


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
