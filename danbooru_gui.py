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
import sys
import webbrowser
from os.path import join
from PyQt4 import QtCore, QtGui

from danbooru.utils import Settings
from danbooru.utils import default_dbpath
from danbooru.utils import parse_query
from danbooru.utils import get_resource_paths, list_generator
from danbooru.db import Storage
from danbooru.ui import ImageViewer, ThumbnailWorker, load_ui, getScaledPixmap,\
    load_translation


class DanbooruSettings(QtGui.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = load_ui('ui/settings.ui', self)


class DanbooruGUI(QtGui.QMainWindow):

    SLIDER_MULT = 16
    RATING = {'s': "Safe", 'q': "Questionable", 'e': "Explicit"}
    img = None

    def __init__(self, parent=None):
        super().__init__(parent)
        load_ui('ui/danbooru.ui', self)
        self.setupUI()
        self.loadSettings()
        self.setupThumbnailWorker()

    def setupUI(self):
        # Connect signals
        self.searchButton.clicked.connect(self.startSearch)
        self.zoomSlider.sliderMoved.connect(self.sliderMove)
        self.queryBox.returnPressed.connect(self.startSearch)
        self.queryBox.textChanged.connect(self.updateClearButton)
        self.infoLabel.linkActivated.connect(self.tagSelected)
        self.listWidget.itemEntered.connect(self.itemOver)
        self.listWidget.itemDoubleClicked.connect(self.doubleClicked)
        self.listWidget.itemSelectionChanged.connect(self.selectionChanged)

        # Event overrides
        self.infoDock.resizeEvent = self.updatePreview

        # Set settings
        pixels = self.zoomSlider.value() * self.SLIDER_MULT
        self.zoomSlider.setToolTip("Size: %i pixels" % pixels)
        self.listWidget.setDragEnabled(False)

        # Add clear button inside the queryBox
        self.clearButton = QtGui.QPushButton(self.queryBox)
        self.clearButton.setVisible(False)
        self.clearButton.setStyleSheet('QPushButton { border: none; padding: 0px; }')
        self.clearButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.clearButton.clicked.connect(self.queryBox.clear)

        for path in get_resource_paths():
            icon = QtGui.QIcon(os.path.join(path, 'ui/query-clear.png'))
            if icon.availableSizes():
                self.clearButton.setIcon(icon)
                break

        layout = QtGui.QHBoxLayout(self.queryBox)
        self.queryBox.setLayout(layout)
        layout.addStretch()
        layout.addWidget(self.clearButton)

        # Add a keyboard shortcut to toggle visibility of the info panel
        info_shortcut = QtGui.QShortcut(QtGui.QKeySequence('F11'), self)
        info_shortcut.activated.connect(self.toggleInfoPanel)

        # Create systray icon
        self.sysTray = QtGui.QSystemTrayIcon(self)
        self.sysTray.setIcon(QtGui.QIcon().fromTheme('image-loading'))
        self.sysTray.activated.connect(self.restoreWindow)

    def table_entry(self, title, value, href=None):
        if href:
            val = '<td><a href="%s">%s</a></td>' % (href, value)
        else:
            val = '<td>%s</td>' % value
        return '<tr><td align="right"><b>%s:</b></td><td>%s</td></tr>' % (title, val)

    def setupThumbnailWorker(self):
        self.thumb = ThumbnailWorker(self.listWidget, self.base_dir)
        self.thumb.makeIconSignal.connect(self.makeIcon)
        self.thumb.setStatusSignal.connect(self.setStatus)
        self.thumb.clearWidgetListSignal.connect(self.clearWidgetList)

    def loadSettings(self):
        # load user settings
        user_dir = os.path.expanduser("~")
        configfile = os.path.join(user_dir, '.danbooru-daemon.cfg')
        config = Settings(configfile)
        dbname = config.loadValue('dbname', 'general', default_dbpath())
        self.db = Storage(dbname)
        self.base_dir = config.loadValue('download_path', 'general', '.')

#        except DanbooruError:
#            self.statusLabel.setText(self.tr("No config loaded"))
#            self.searchButton.setEnabled(False)
#            self.queryBox.returnPressed.disconnect(self.startSearch)

    def restoreWindow(self, reason):  # @UnusedVariable
        self.sysTray.hide()
        self.showNormal()

    def toggleInfoPanel(self):
        self.infoDock.setVisible(not self.infoDock.isVisible())

    def clearWidgetList(self):
        self.listWidget.clear()

    def itemOver(self, item_img):
        pass

    def updateClearButton(self, text):
        self.clearButton.setVisible(bool(text))

    def updatePreview(self, event=None):  # @UnusedVariable
        if self.img:
            dock_s = self.infoDock.size()
            prev_w = self.previewWidget
            extra = self.infoLabel.size().height() + 64
            if prev_w.size().width() > dock_s.height() - extra:
                height = dock_s.height() - extra
            else:
                height = prev_w.size().width()
            self.previewWidget.setMinimumHeight(height)

            size = self.previewWidget.size()
            if isinstance(self.img, QtGui.QIcon):
                self.previewWidget.setPixmap(getScaledPixmap(self.img.pixmap(256, 256), size))
            else:
                self.previewWidget.setPixmap(getScaledPixmap(self.img, size))

    def getItemPath(self, item):
        post = item.data(QtCore.Qt.UserRole)
        sess = self.db.DBsession()
        post = sess.merge(post)
        img = post.image
        return join(self.base_dir, img.md5[0], img.md5 + img.file_ext)

    def nextImage(self, viewer):
        self.listWidget.setCurrentRow(self.listWidget.currentRow() + 1, QtGui.QItemSelectionModel.SelectCurrent)
        item = self.listWidget.currentItem()
        path = self.getItemPath(item)
        viewer.loadImage(path=path)

    def prevImage(self, viewer):
        self.listWidget.setCurrentRow(self.listWidget.currentRow() - 1, QtGui.QItemSelectionModel.SelectCurrent)
        item = self.listWidget.currentItem()
        path = self.getItemPath(item)
        viewer.loadImage(path=path)

    def showImage(self, full_path):
        viewer = ImageViewer(path=full_path)
        viewer.onNextImage.connect(self.nextImage)
        viewer.onPrevImage.connect(self.prevImage)
        viewer.showFullScreen()
        self.hide()
        viewer.exec()
        self.show()

    def doubleClicked(self, item):
        path = self.getItemPath(item)
        self.showImage(path)

    def buildInfoTag(self, post):
        tags = ['<a href="%s">%s</a>' % (tag.name, tag.name) for tag in post.tags]
        pools = ['<a href="pool:%i">%s</a>' % (pool.pool_id, pool.name) for pool in post.pools]

        table_items = list()
        table_items.append(self.table_entry(self.tr("Width"), post.image.width, "width:%i" % post.image.width))
        table_items.append(self.table_entry(self.tr("Height"), post.image.height, "height:%i" % post.image.height))
        if tags:
            table_items.append(self.table_entry(self.tr("Tags"), " ".join(tags)))
        table_items.append(self.table_entry(self.tr("Rating"), self.RATING[post.rating], "rating:%s" % post.rating))
        table_items.append(self.table_entry(self.tr("Score"), post.score))
        table_items.append(self.table_entry(self.tr("From"), post.board.host))
        table_items.append(self.table_entry(self.tr("ID"), post.post_id))
        if pools:
            table_items.append(self.table_entry(self.tr("Pools"), " ".join(pools)))
        page_url = '%s/post/show/%i' % (post.board.host, post.post_id)
        table_items.append(self.table_entry(self.tr("URL"), page_url, page_url))
        return '<table>%s</table>' % ''.join(table_items)

    def selectionChanged(self):
        items = self.listWidget.selectedItems()
        if not items:
            self.nameLabel.setText(self.tr("No selection"))
            self.img = None
        elif len(items) == 1:
            item = items[0]
            self.listWidget.scrollToItem(item)
            self.nameLabel.setText(self.tr("1 selected item"))
            post = item.data(QtCore.Qt.UserRole)
            sess = self.db.DBsession()
            post = sess.merge(post)
            img = post.image
            full_path = join(self.base_dir, img.md5[0], img.md5 + img.file_ext)
            self.img = QtGui.QImage(full_path)

            if not self.img or self.img.byteCount() == 0:
                self.img = QtGui.QIcon().fromTheme('image-x-generic')

            self.updatePreview()
            self.infoLabel.setText(self.buildInfoTag(post))
        else:
            self.nameLabel.setText(self.tr("%i selected items") % len(items))
            self.img = None

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.WindowStateChange:
            if self.windowState() & QtCore.Qt.WindowMinimized:
                self.hide()
                self.sysTray.show()
                event.ignore()

    def tagSelected(self, tag):
        if tag.startswith('http://'):
            webbrowser.open(tag)
        else:
            self.queryBox.setText(' '.join([self.queryBox.text(), tag]))
            self.startSearch()

    def makeIcon(self, post, image):
        item = self.addItem(post)
        value = self.zoomSlider.value() * self.SLIDER_MULT
        if image:
            pixmap = QtGui.QPixmap(value, value)
            pixmap.convertFromImage(image)
            icon = QtGui.QIcon(pixmap)
            item.setIcon(icon)
        self.statusLabel.setText(self.tr("Found %i images") %
                                 self.listWidget.count())

    def setStatus(self):
        self.statusLabel.setText(self.tr("No results"))

    def sliderMove(self, value):
        value *= self.SLIDER_MULT
        self.zoomSlider.setToolTip(self.tr("Size: %i pixels") % value)
        self.listWidget.setIconSize(QtCore.QSize(value, value))
        generator = list_generator(self.listWidget)
        for item in generator:
            item.setSizeHint(QtCore.QSize(value + 32, value + 32))

    def addItem(self, post):
        item = QtGui.QListWidgetItem()
        item.setText(post.image.md5 + post.image.file_ext)
        item.setIcon(QtGui.QIcon().fromTheme('image-x-generic'))
        item.setData(QtCore.Qt.UserRole, post)
        item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom)
        value = self.zoomSlider.value() * self.SLIDER_MULT
        item.setSizeHint(QtCore.QSize(value + 32, value + 32))
        self.listWidget.addItem(item)
        return item

    def startSearch(self):
        text = self.queryBox.text().strip()

        if not text:
            return

        result = parse_query(text)

        if isinstance(result, str):
            self.statusLabel.setText(self.tr("Error in term: %s") % result)
            return

        tags, query = result

        if not query.get('site') and query.get('rating'):
            self.statusLabel.setText(self.tr("Search by rating depends on site"))
            return

        self.thumb.stop()
        self.thumb.wait()

        self.statusLabel.setText(self.tr("Processing..."))
        self.thumb.setData(tags, query, self.db)

        size = self.zoomSlider.value() * self.SLIDER_MULT
        self.listWidget.setIconSize(QtCore.QSize(size, size))
        self.thumb.start()

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    load_translation('danbooru_gui', app)
    DanbooruGUI().show()
    sys.exit(app.exec_())
