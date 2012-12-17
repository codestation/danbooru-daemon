import logging
from threading import Thread, Event
from danbooru.db import Storage
from danbooru.api import DanbooruApi


class Daemon(Thread):

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.event = Event()
        self.loop_phrase = "new"

    def run(self):
        db = Storage(self.config['dbname'])
        while(not self.event.is_set()):
            for section in self.config['fetch_from']:
                self.current_param = section
                db.setHost(self.config['host'], section)
                board = DanbooruApi(self.config['host'])
                board.setLogin(self.config['login'], self.config['password'], self.config['salt'])
                self.current_phrase = "metadata"
                for tag in self.config['query']['tags']:
                    self.current_param = tag
                    if self.event.is_set():
                        return
                    self.update(tag, board, db)
                self.current_phrase = "download"
                self.download(db)
                #self.current_phrase = "nepomuk"
                #self.run_nepomuk(cfg, db)
                #if self._abort: break
            self.current_phrase = "wait"
            self.event.wait(self.config['fetch_interval'])
        self.current_phrase = "finished"

    def update(self):
        pass

    def download(self, db, callback):
        dl = Downloader(self.config['.download_path'])
        offset = 0
        limit = 2048

        def callback(file, current, total):
            sys.stdout.write("\r%s: %i of %i bytes" % (file, current, total))
            sys.stdout.flush()

        while not self.event.is_set():
            rows = db.getFiles(limit, offset)
            if rows:
                dl.downloadQueue(rows, self.config['skip_file_check'], callback)
                offset += limit

    @property
    def status(self):
        return self.current_phrase, self.current_param

    def stop(self):
        self.event.set()
