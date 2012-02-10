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

import shutil
import hashlib
from time import sleep
from os.path import basename, splitext, isfile
from urllib.parse import urlsplit
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

class Downloader(object):
    
    total = 0
    abort = False

    def __init__(self, path, extra):
        self.path = path
        self.extra = extra
        
    def stopDownload(self):
        self.abort = True
        
    def _calculateMD5(self, name):
        try:
            file = open(name, 'rb')
            md5_hash = hashlib.md5()
            while True:
                d = file.read(128)
                if not d: break
                md5_hash.update(d)
            file.close()
            return md5_hash.hexdigest()
        except IOError:
            pass
            
    def _checkLocal(self, base, file_md5, hash_from_file=False):        
        using_extra = False
        filename = self.path + '/' + base
        file_extra = self.extra + '/' + base
        
        if hash_from_file and isfile(filename):
            md5 = basename(splitext(filename)[0])
        else:
            md5 = self._calculateMD5(file_extra)
            using_extra = True
         
        if not md5:         
            md5 = self._calculateMD5(filename)

        if md5:
            if md5 == file_md5:
                if using_extra:
                    print('Moving %s to %s' % (file_extra, filename))
                    shutil.move(file_extra, filename)
                else:
                    print('%s already exists, skipping download' % filename)
                return True
            else:
                print('md5 mismatch for %s' % base)
        return False
                    
    def downloadQueue(self, dl_list):
        for dl in dl_list:
            if self.abort:
                break
            base = basename(urlsplit(dl['file_url'])[2])
            if self._checkLocal(base, dl['md5'], hash_from_file=True):                
                continue
            filename = self.path + '/' + base
            
            try:
                local_file = open(filename, 'wb')
            except IOError:
                print('Error while creating %s' % filename)
                continue

            retries = 0
            while retries < 3:
                try:
                    remote_file = urlopen(dl['file_url'])
                    shutil.copyfileobj(remote_file, local_file)
                    remote_file.close()                
                    local_file.close()
                    self.total += 1
                    print('(%i) %s [OK]' % (self.total, dl['file_url']))
                    sleep(1)
                    break
                except URLError as e:
                    print('\n>>> Error %s' % e.reason)
                except HTTPError as e:
                    print('\n>>> Error %i: %s' % (e.code, e.msg))
                retries += 1
                print('Retrying (%i) in 2 seconds...' % retries)
                sleep(2)
