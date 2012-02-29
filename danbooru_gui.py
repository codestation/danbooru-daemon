#!/usr/bin/python3
# -*- coding: utf-8 -*-


import sys
from os.path import join, dirname
from PyQt4 import QtCore, QtGui, uic

from danbooru import utils
from danbooru.database import Database


class DanbooruGUI(QtGui.QMainWindow):

    SLIDER_MULT = 16
    img = None
    info_format = ("<table>" +
                   "<tr><td align='right'><b>Width:</b></td>" +
                   "<td><a href='width:%i'>%i</a></td></tr>" +
                   "<tr><td align='right'><b>Height:</b></td>" +
                   "<td><a href='height:%i'>%i</a></td></tr>" +
                   "<tr><td align='right'><b>Tags:</b></td>" +
                   "<td>%s</td></tr>" +
                   "<tr><td align='right'><b>Rating:</b></td>" +
                   "<td><a href='rating:%s'>%s</a></td></tr>" +
                   "<tr><td align='right'><b>Score:</b></td>" +
                   "<td>%i</td></tr>" +
                   "<tr><td align='right'><b>From:</b></td>" +
                   "<td>%s</td></tr>" +
                   "<tr><td align='right'><b>ID:</b></td>" +
                   "<td>%i</td></tr>" +
                   "</table>"
                   )

    def __init__(self, parent=None):
        super(DanbooruGUI, self).__init__(parent)
        self.ui = uic.loadUi('danbooru.ui', self)
        self.setup()

    def setup(self):
        # UI settings
        self.listWidget.setDragEnabled(False)

        # UI signals
        self.searchButton.clicked.connect(self.startSearch)
        self.queryBox.returnPressed.connect(self.startSearch)
        self.zoomSlider.sliderMoved.connect(self.sliderMove)
        self.listWidget.itemSelectionChanged.connect(self.selectionChanged)
        self.infoLabel.linkActivated.connect(self.tagSelected)
        # UI event overrides
        self.infoDock.resizeEvent = self.updatePreview

        # UI data
        pixels = self.zoomSlider.value() * self.SLIDER_MULT
        self.zoomSlider.setToolTip("Size: %i pixels" % pixels)

        # Other setup
        self.thumb = self.ThumbnailWorker(self.listWidget)
        self.thumb.makeIconSignal.connect(self.makeIcon)
        self.db = Database("danbooru-db.sqlite")

        # Add clear button on queryBox
        self.clearButton = QtGui.QPushButton(self.queryBox)
        self.clearButton.setVisible(False)
        self.clearButton.setStyleSheet("QPushButton { border: none; padding: 0px; }")
        self.clearButton.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.clearButton.setIcon(QtGui.QIcon("edit-clear-locationbar-rtl.png"))
        self.clearButton.clicked.connect(self.queryBox.clear)
        self.queryBox.textChanged.connect(self.updateClearButton)
        layout = QtGui.QHBoxLayout(self.queryBox)
        self.queryBox.setLayout(layout)
        layout.addStretch()
        layout.addWidget(self.clearButton)

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
            self.previewWidget.setPixmap(self.getScaledPixmap(self.img))

    def getScaledPixmap(self, image):
        size = self.previewWidget.size()
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

    def selectionChanged(self):
        items = self.listWidget.selectedItems()
        if not items:
            self.nameLabel.setText("No selection")
            self.img = None
        elif len(items) == 1:
            item = items[0]
            self.nameLabel.setText("1 selected item")
            post = item.data(QtCore.Qt.UserRole)
            full_path = utils.post_abspath(post)
            self.img = QtGui.QImage(full_path)
            self.updatePreview()
            tags = ["<a href='%s'>%s</a>" % (tag, tag) for tag in post['tags']]
            tags = " ".join(tags)
            self.infoLabel.setText(self.info_format %
                (post['width'], post['width'], post['height'], post['height'],
                 tags, post['rating'], post['rating'], post['score'],
                 post['board_url'], post['id']))
        else:
            self.nameLabel.setText("%i selected items" % len(items))
            self.img = None

    def tagSelected(self, tag):
        self.queryBox.setText(self.queryBox.text() + " %s" % tag)
        self.startSearch()

    def itemClicked(self, item):
        post = item.data(QtCore.Qt.UserRole)
        full_path = utils.post_abspath(post)
        self.previewWidget.setPixmap(QtGui.QPixmap(full_path))

    def makeIcon(self, item, image):
        value = self.zoomSlider.value() * self.SLIDER_MULT
        pixmap = QtGui.QPixmap(value, value)
        pixmap.convertFromImage(image)
        icon = QtGui.QIcon(pixmap)
        item.setIcon(icon)

    class ThumbnailWorker(QtCore.QThread):

        makeIconSignal = QtCore.pyqtSignal(QtGui.QListWidgetItem, QtGui.QImage)
        abort = False

        def __init__(self, ListWidget, parent=None):
            super(self.ThumbnailWorker, self).__init__(parent)
            self.widget = ListWidget

        def stop(self):
            self.abort = True

        def run(self):
            self.abort = False
            thumbnail_dir = join(dirname(sys.argv[0]), ".danbooru-thumbnails")
            th = utils.ThumbnailCache(thumbnail_dir)
            generator = utils.list_generator(self.widget)
            for item in generator:
                if self.abort: break
                post = item.data(QtCore.Qt.UserRole)
                full_path = utils.post_abspath(post)
                image = th.getThumbnail(full_path)
                self.makeIconSignal.emit(item, image)

    def sliderMove(self, value):
        value *= self.SLIDER_MULT
        self.zoomSlider.setToolTip("Size: %i pixels" % value)
        self.listWidget.setIconSize(QtCore.QSize(value, value))
        generator = utils.list_generator(self.listWidget)
        for item in generator:
            item.setSizeHint(QtCore.QSize(value + 32,value + 32))
        
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
                self.statusLabel.setText("Error in term: %s" % query)
                return

            if query.get('site'):
                self.db.setHost(host=None, alias=query['site'])
            else:
                if query.get('rating'):
                    self.statusLabel.setText("Search by rating depends on site")
                    return
                self.db.clearHost()
            self.thumb.stop()
            self.thumb.wait()
            self.listWidget.clear()
            self.statusLabel.setText("Processing...")
            if query.get('tags'):
                posts = self.db.getANDPosts(query['tags'], limit=100, extra_items=query)
            else:
                posts = self.db.getPosts(100, extra_items=query)
            for post in posts:
                self.addItem(post)
            self.statusLabel.setText("Found %i images" % len(posts))
            size = self.zoomSlider.value() * self.SLIDER_MULT
            self.listWidget.setIconSize(QtCore.QSize(size, size))            
            self.thumb.start()
    
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    w = DanbooruGUI()
    w.show()
    sys.exit(app.exec_())
