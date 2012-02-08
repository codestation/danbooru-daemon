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