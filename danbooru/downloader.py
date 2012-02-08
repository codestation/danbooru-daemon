#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
   Copyright 2012 codestation

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import shutil
import hashlib
from time import sleep
from os.path import basename, splitext
from urllib.parse import urlsplit
from urllib.request import urlopen

class Downloader(object):
    
    total = 0
    abort = False

    def __init__(self, path, extra):
        self.path = path
        self.extra = extra
        
    def stopDownload(self):
        self.abort = True

    def downloadQueue(self, dl_list, check=True):
        for dl in dl_list:
            if self.abort: break
            file_extra = self.extra + '/' + basename(urlsplit(dl['file_url'])[2])            
            filename = self.path + '/' + basename(urlsplit(dl['file_url'])[2])
            try:
                ext = False
                try:
                    f = open(file_extra, 'rb')
                    ext = True
                except IOError:
                    f = open(filename, 'rb')
                if check:
                    md5_hash = hashlib.md5()
                    while True:
                        d = f.read(128)
                        if not d: break
                        md5_hash.update(d)
                    f.close()
                    md5 = md5_hash.hexdigest()
                else:
                    print('Skipping md5 hash calculation')
                    md5 = basename(splitext(filename)[0])
                if md5 == dl['md5']:
                    print('%s already exists, skipping' % dl['file_url'])
                    if ext:
                        print('Moving %s to %s' % (file_extra, filename))
                        shutil.move(file_extra, filename)
                    continue
            except IOError:
                pass
            
            local_file = open(filename, 'wb')
            remote_file = urlopen(dl['file_url'])
            shutil.copyfileobj(remote_file, local_file)
            remote_file.close()
            local_file.close()
            self.total += 1
            print('(%i) %s [OK]' % (self.total, dl['file_url']))
            sleep(1)