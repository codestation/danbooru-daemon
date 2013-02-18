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
import urllib
import logging
import requests
from danbooru.utils import md5sum


class Downloader(object):

    CHUNK_SIZE = 8 * 1024

    def __init__(self, path, stop_event):
        self.path = path
        self.event = stop_event
        requests_log = logging.getLogger("requests")
        requests_log.setLevel(logging.WARNING)

    def download_file(self, url, dst, size=8192, callback=lambda *x: None):  # @UnusedVariable
        with open(dst, 'wb') as local_file:
            r = requests.get(url, stream=True)
            remote_size = int(r.headers.get('content-length', -1))
            read_size = 0
            for chunk in iter(lambda: r.raw.read(size), b''):
                if self.event.is_set():
                    callback(dst, -1, remote_size)
                    break
                read_size += len(chunk)
                local_file.write(chunk)
                callback(dst, read_size, remote_size)

    def valid_image(self, row, filename, check_md5sum=False):
        if os.path.isfile(filename):
            if not row.image.file_size or os.path.getsize(filename) == row.image.file_size:
                if not check_md5sum or md5sum(filename) == row.image.md5:
                    return True
                else:
                    logging.warning("%s md5sum doesn't match, re-downloading", filename)
            else:
                logging.warning("%s filesize doesn't match, re-downloading", filename)
        #else:
        #    logging.warning("%s doesn't exists, re-downloading", filename)
        return False

    def downloadQueue(self, db, check_md5sum=False, callback=None):
        for row in db.getImageList():
            if self.event.is_set():
                break
            base_name = row.image.md5 + row.image.file_ext
            subdir = row.image.md5[0]
            filename = os.path.join(self.path, subdir, base_name)
            if not self.valid_image(row, filename, check_md5sum):
                if row.file_url.startswith('http'):
                    url = row.file_url
                else:
                    url = urllib.parse.urljoin(row.board.host, row.file_url)
                self.download_file(url, filename, callback=callback)
