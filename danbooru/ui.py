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
import time
from PyQt4 import QtCore, QtGui, uic

from danbooru.models import Post
from danbooru.utils import get_resource_paths
from danbooru.error import DanbooruError


class ThumbnailCache(object):

    MAX_SIZE = 256

    def __init__(self, path):
        self.path = path
        os.makedirs(path, exist_ok=True)

    def getThumbnail(self, path):
        if os.path.exists(path):
            base = os.path.splitext(os.path.basename(path))[0]
            image = QtGui.QImage()
            if image.load(os.path.join(self.path, base + ".png"), format="png"):
                return image
            else:
                image = self.scaleImage(path, self.MAX_SIZE)
                image.save(os.path.join(self.path, base + ".png"), format="png")
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

    makeIconSignal = QtCore.pyqtSignal(Post, object)
    setStatusSignal = QtCore.pyqtSignal()
    clearWidgetListSignal = QtCore.pyqtSignal()
    abort = False

    def __init__(self, ListWidget, basedir, parent=None):
        super().__init__(parent)
        self.widget = ListWidget
        self.basedir = basedir
        user_path = os.path.expanduser("~")
        self.thumbnail_dir = os.path.join(user_path, ".cache/danbooru-daemon/thumbnails")
        os.makedirs(self.thumbnail_dir, exist_ok=True)

    def setData(self, tags, query, db):
        self.tags = tags
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
        if self.tags:
            posts = self.db.getANDPosts(self.tags, limit=200, extra_items=self.query)
        else:
            posts = self.db.getPosts(200, extra_items=self.query)

        if not posts:
            self.setStatusSignal.emit()
        else:
            for post in posts:
                if self.abort:
                    time.sleep(1)
                    break
                img = post.image
                full_path = os.path.join(self.basedir, img.md5[0], img.md5 + img.file_ext)
                image = th.getThumbnail(full_path)
                self.makeIconSignal.emit(post, image)


class ImageView(QtGui.QGraphicsView):

    MARGIN = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mScrollPos = None

    def scrollSet(self, pos):
        self.horizontalScrollBar().setValue(pos.x())
        self.verticalScrollBar().setValue(pos.y())

    def scrollGet(self):
        x = self.horizontalScrollBar().value()
        y = self.verticalScrollBar().value()
        return QtCore.QPoint(x, y)

    def mouseMoveEvent(self, event):
        QtGui.QGraphicsView.mouseMoveEvent(self, event)

        mouseWarp = False
        mousePos = event.pos()

        maxWidth = self.rect().width()
        maxHeight = self.rect().height()

        if mousePos.x() <= self.MARGIN:
            mousePos.setX(maxWidth - self.MARGIN - 1)
            mouseWarp = True
        elif mousePos.x() >= maxWidth - self.MARGIN:
            mousePos.setX(self.MARGIN + 1)
            mouseWarp = True
        if mousePos.y() <= self.MARGIN:
            mousePos.setY(maxHeight - self.MARGIN - 1)
            mouseWarp = True
        elif mousePos.y() >= maxHeight - self.MARGIN:
            mousePos.setY(self.MARGIN + 1)
            mouseWarp = True

        screenDelta = QtGui.QCursor.pos() - event.pos()

        if mouseWarp:
            QtGui.QCursor.setPos(mousePos + screenDelta)
            self.mScrollPos = self.scrollGet()
        elif self.mScrollPos is not None:
            self.scrollSet(self.mScrollPos)
            self.mScrollPos = None

    def mouseDoubleClickEvent(self, event):  # @UnusedVariable
        self.parentWidget().close()

    def keyPressEvent(self, event):
        # let pass the keys to the parent
        if event.key() in [QtCore.Qt.Key_Left, QtCore.Qt.Key_Right]:
            event.ignore()


class ImageViewer(QtGui.QDialog):

    SCALE_TO_WIDTH = True
    SCALE_TO_HEIGHT = True
    FIT_TO_SCREEN = False

    onNextImage = QtCore.pyqtSignal(QtGui.QDialog)
    onPrevImage = QtCore.pyqtSignal(QtGui.QDialog)

    def __init__(self, parent=None, path=None):
        super().__init__(parent)
        layout = QtGui.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.pixmap = None

        scene = QtGui.QGraphicsScene()
        if path:
            self.item = QtGui.QGraphicsPixmapItem(QtGui.QPixmap(path))
        else:
            self.item = QtGui.QGraphicsPixmapItem()
        scene.addItem(self.item)

        self.view = ImageView()
        self.view.setFrameStyle(0)
        self.view.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)
        self.view.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.black))
        self.view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.view.setRenderHint(QtGui.QPainter.Antialiasing & QtGui.QPainter.SmoothPixmapTransform)
        self.view.setScene(scene)

        layout.addWidget(self.view)

    def loadImage(self, image=None, path=None):
        if image:
            self.pixmap = QtGui.QPixmap.fromImage(image)
        elif path:
            self.pixmap = QtGui.QPixmap(path)
        if self.pixmap:
            self.item.setPixmap(self.pixmap)
            self.onResize(None)

    def onResize(self, event):  # @UnusedVariable
        wrect = self.rect()
        prect = self.pixmap.rect()

        ratioW = wrect.width() / prect.width()
        ratioH = wrect.height() / prect.height()
        if not self.SCALE_TO_HEIGHT:
            if self.FIT_TO_SCREEN:
                self.item.setPixmap(self.pixmap.scaledToWidth(prect.width() * ratioW, QtCore.Qt.SmoothTransformation))
            self.view.verticalScrollBar().setValue(0)
        elif not self.SCALE_TO_WIDTH:
            if self.FIT_TO_SCREEN:
                self.item.setPixmap(self.pixmap.scaledToHeight(prect.height() * ratioH, QtCore.Qt.SmoothTransformation))
            self.view.horizontalScrollBar().setValue(0)
        else:
            ratio = min(ratioW, ratioH)
            self.item.setPixmap(self.pixmap.scaled(int(prect.width() * ratio), int(prect.height() * ratio), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        wrect = self.item.pixmap().rect()
        self.view.setSceneRect(QtCore.QRectF(wrect))

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Left:
            self.onPrevImage.emit(self)
        elif key == QtCore.Qt.Key_Right:
            self.onNextImage.emit(self)


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
    if isinstance(image, QtGui.QImage):
        return QtGui.QPixmap.fromImage(img)
    else:
        return img


def load_ui(uifile, baseinstance):
    for path in get_resource_paths():
        try:
            return uic.loadUi(os.path.join(path, uifile), baseinstance)
        except:
            pass
    else:
        raise DanbooruError("Cannot load UI file")


def load_translation(file, app):
    translator = QtCore.QTranslator(app)
    for path in get_resource_paths():
        if translator.load(file + '.' + QtCore.QLocale.system().name(), path):
            app.installTranslator(translator)
            break