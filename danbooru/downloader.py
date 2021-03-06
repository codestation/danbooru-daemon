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
import socket
import hashlib
import logging
from time import sleep
from os.path import isfile, join, getsize
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from http.client import HTTPException


class Downloader(object):

    _total = 1
    _stop = False

    def __init__(self, path):
        self.path = path

    def stop(self):
        logging.debug("Stopping download job")
        self._stop = True

    def _calculateMD5(self, name):
        try:
            file = open(name, 'rb')
            md5_hash = hashlib.md5()
            while True:
                d = file.read(128)
                if not d:
                    break
                md5_hash.update(d)
            file.close()
            return md5_hash.hexdigest()
        except IOError:
            pass

    def downloadQueue(self, dl_list, nohash=False, callback=None):
        for dl in dl_list:
            if self._stop:
                break
            base = dl.image.md5 + dl.image.file_ext

            subdir = dl.image.md5[0]
            filename = join(self.path, subdir, base)
            if isfile(filename):
                if not dl.image.file_size or getsize(filename) == dl.image.file_size:
                    if nohash:
                        continue
                    else:
                        md5 = self._calculateMD5(filename)
                        if md5:
                            if md5 == dl.image.md5:
                                #logging.debug("%s already exists, skipping" % filename)
                                continue
                            else:
                                logging.warning("%s md5sum doesn't match, re-downloading", filename)
                else:
                    logging.warning("%s filesize doesn't match, re-downloading", filename)
            #else:
            #    logging.warning("%s doesn't exists, re-downloading", filename)
            try:
                local_file = open(filename, 'wb')
            except IOError:
                logging.error('Error while creating %s', filename)
                continue

            retries = 0
            start = 0

            while not self._stop and retries < 3:
                try:
                    remote_file = urlopen(dl.file_url)

                    meta = remote_file.info()
                    if "Content-Length" in meta:
                        remote_size = int(meta['Content-Length'])
                    else:
                        remote_size = -1

                    if start:
                        remote_file.seek(start)

                    while not self._stop:
                        buf = remote_file.read(16 * 1024)
                        if not buf:
                            break
                        local_file.write(buf)
                        start += len(buf)
                        if callback:
                            callback(base, start, remote_size)

                    remote_file.close()
                    local_file.close()

                    if callback:
                        sys.stdout.write("\r")
                        sys.stdout.flush()

                    if self._stop:
                        logging.debug('(%i) %s [ABORTED]', self._total, base)
                        break

                    logging.debug('(%i) %s [OK]', self._total, base)
                    self._total += 1
                    sleep(1)
                    break
                except HTTPError as e:
                    logging.error('>>> Error %i: %s', e.code, e.msg)
                except URLError as e:
                    logging.error('>>> Error %s', e.reason)
                except HTTPException as e:
                    logging.error('>>> Error HTTPException')
                except socket.error as e:
                    logging.error("Connection error: %s", e)

                start = local_file.tell()

                retries += 1
                logging.warning('Retrying (%i) in 2 seconds...', retries)
                sleep(2)
