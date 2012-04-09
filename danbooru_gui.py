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

import sys
from locale import getlocale
from os.path import join, expanduser
from PyQt4 import QtCore, QtGui, uic

from danbooru import utils, ui
from danbooru.database import Database
from danbooru.settings import Settings


class DanbooruGUI(QtGui.QMainWindow):

    SLIDER_MULT = 16
    img = None

    BASE_DIR = "."

    info_format = ('<table>' +
                   '<tr><td align="right"><b>%s:</b></td>' +
                   '<td><a href="width:%%i">%%i</a></td></tr>' +
                   '<tr><td align="right"><b>%s:</b></td>' +
                   '<td><a href="height:%%i">%%i</a></td></tr>' +
                   '<tr><td align="right"><b>%s:</b></td>' +
                   '<td>%%s</td></tr>' +
                   '<tr><td align="right"><b>%s:</b></td>' +
                   '<td><a href="rating:%%s">%%s</a></td></tr>' +
                   '<tr><td align="right"><b>%s:</b></td>' +
                   '<td>%%i</td></tr>' +
                   '<tr><td align="right"><b>%s:</b></td>' +
                   '<td>%%s</td></tr>' +
                   '<tr><td align="right"><b>%s:</b></td>' +
                   '<td>%%i</td></tr>' +
                   '</table>'
                   )

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.ui = uic.loadUi(utils.find_resource(__name__, "ui/danbooru.ui"), self)
        self.setupUI()
        self.loadSettings()

    def setupUI(self):
        # UI settings
        self.listWidget.setDragEnabled(False)

        # UI signals
        self.searchButton.clicked.connect(self.startSearch)
        self.queryBox.returnPressed.connect(self.startSearch)
        self.zoomSlider.sliderMoved.connect(self.sliderMove)
        self.listWidget.itemEntered.connect(self.itemOver)
        self.listWidget.itemSelectionChanged.connect(self.selectionChanged)
        self.infoLabel.linkActivated.connect(self.tagSelected)
        # UI event overrides
        self.infoDock.resizeEvent = self.updatePreview

        # UI data
        pixels = self.zoomSlider.value() * self.SLIDER_MULT
        self.zoomSlider.setToolTip("Size: %i pixels" % pixels)

        # Other setup
        self.thumb = ui.ThumbnailWorker(self.BASE_DIR, self.listWidget)
        self.thumb.makeIconSignal.connect(self.makeIcon)

        # Add clear button on queryBox
        self.clearButton = QtGui.QPushButton(self.queryBox)
        self.clearButton.setVisible(False)
        self.clearButton.setStyleSheet("QPushButton { border: none; padding: 0px; }")
        self.clearButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        icon = QtGui.QIcon(utils.find_resource(__name__, "ui/query-clear.png"))
        self.clearButton.setIcon(icon)
        self.clearButton.clicked.connect(self.queryBox.clear)
        self.queryBox.textChanged.connect(self.updateClearButton)
        layout = QtGui.QHBoxLayout(self.queryBox)
        self.queryBox.setLayout(layout)
        layout.addStretch()
        layout.addWidget(self.clearButton)

    def loadSettings(self):
        self.info_values = (self.tr("Width"), self.tr("Height"), self.tr("Tags"), self.tr("Rating"),
                            self.tr("Score"), self.tr("From"), self.tr("ID"))

        # load user settings
        user_dir = expanduser("~")
        cfg = Settings(join(user_dir, ".danbooru-daemon.cfg"))
        cfg.load("default", [], {'dbname': None})

        # Get the base path for image search
        self.BASE_DIR = cfg.download_path

        if not cfg.dbname:
            daemon_dir = join(user_dir, ".local/share/danbooru-daemon")
            cfg.dbname = join(daemon_dir, "danbooru-db.sqlite")
        dbname = join(daemon_dir, cfg.dbname)
        self.db = Database(dbname)

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
            self.previewWidget.setPixmap(ui.getScaledPixmap(self.img, size))

    def selectionChanged(self):
        items = self.listWidget.selectedItems()
        if not items:
            self.nameLabel.setText(self.tr("No selection"))
            self.img = None
        elif len(items) == 1:
            item = items[0]
            self.nameLabel.setText(self.tr("1 selected item"))
            post = item.data(QtCore.Qt.UserRole)
            full_path = utils.post_abspath(self.BASE_DIR, post)
            self.img = QtGui.QImage(full_path)
            self.updatePreview()
            tags = ['<a href="%s">%s</a>' % (tag, tag) for tag in post['tags']]
            tags = " ".join(tags)
            str_format = self.info_format % self.info_values
            self.infoLabel.setText(str_format %
                (post['width'], post['width'], post['height'], post['height'],
                 tags, post['rating'], post['rating'], post['score'],
                 post['board_url'], post['id']))
        else:
            self.nameLabel.setText(self.tr("%i selected items") % len(items))
            self.img = None

    def tagSelected(self, tag):
        self.queryBox.setText(self.queryBox.text() + " %s" % tag)
        self.startSearch()

    def itemClicked(self, item):
        post = item.data(QtCore.Qt.UserRole)
        full_path = utils.post_abspath(self.BASE_DIR, post)
        self.previewWidget.setPixmap(QtGui.QPixmap(full_path))

    def makeIcon(self, item, image):
        value = self.zoomSlider.value() * self.SLIDER_MULT
        pixmap = QtGui.QPixmap(value, value)
        pixmap.convertFromImage(image)
        icon = QtGui.QIcon(pixmap)
        item.setIcon(icon)

    def sliderMove(self, value):
        value *= self.SLIDER_MULT
        self.zoomSlider.setToolTip(self.tr("Size: %i pixels") % value)
        self.listWidget.setIconSize(QtCore.QSize(value, value))
        generator = utils.list_generator(self.listWidget)
        for item in generator:
            item.setSizeHint(QtCore.QSize(value + 32, value + 32))

    def addItem(self, post):
        item = QtGui.QListWidgetItem()
        item.setText(utils.post_basename(post))
        item.setIcon(QtGui.QIcon().fromTheme("image-x-generic"))
        item.setData(QtCore.Qt.UserRole, post)
        item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom)
        value = self.zoomSlider.value() * self.SLIDER_MULT
        item.setSizeHint(QtCore.QSize(value + 32, value + 32))
        self.listWidget.addItem(item)

    def startSearch(self):
        text = self.queryBox.text().strip()
        if text:
            query = utils.parseQuery(text)
            if isinstance(query, str):
                self.statusLabel.setText(self.tr("Error in term: %s") % query)
                return

            if query.get('site'):
                self.db.setHost(host=None, alias=query['site'])
            else:
                if query.get('rating'):
                    self.statusLabel.setText(self.tr("Search by rating depends on site"))
                    return
                self.db.clearHost()
            self.thumb.stop()
            self.thumb.wait()
            self.listWidget.clear()
            self.statusLabel.setText(self.tr("Processing..."))
            if query.get('tags'):
                posts = self.db.getANDPosts(query['tags'], limit=100, extra_items=query)
            else:
                posts = self.db.getPosts(100, extra_items=query)
            for post in posts:
                self.addItem(post)
            self.statusLabel.setText(self.tr("Found %i images") % len(posts))
            size = self.zoomSlider.value() * self.SLIDER_MULT
            self.listWidget.setIconSize(QtCore.QSize(size, size))
            self.thumb.start()

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)

    locale = getlocale()
    if locale[0]:
        translator = QtCore.QTranslator(app)
        try:
            resource = utils.find_resource(__file__, "danbooru_gui-%s.qm" % locale[0])
            if translator.load(resource):
                app.installTranslator(translator)
        except Exception:
            try:
                resource = utils.find_resource(__file__, "danbooru_gui-%s.qm" % locale[0].split("_")[0])
                if translator.load(resource):
                    app.installTranslator(translator)
            except Exception:
                pass

    w = DanbooruGUI()
    w.show()
    sys.exit(app.exec_())
