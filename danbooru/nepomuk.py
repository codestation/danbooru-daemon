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

import logging
from os import listdir
from os.path import abspath, join, isdir, isfile
from PyKDE4.kdecore import KUrl
from PyKDE4.nepomuk import Nepomuk
from PyQt4.QtCore import QObject, QCoreApplication, QEventLoop, QTimer

class NepomukTask(object):
    
    def abortTask(self):
        self.job.cancelJob()
    
    def _initNepomuk(self):            
        self.app = QCoreApplication([])
        if Nepomuk.ResourceManager.instance().init() != 0:
            raise Exception('Error initializing Nepomuk')         
        
    def updateDirectoryTags(self, path, db):
        self._initNepomuk()                
        self.job = self.NepomukJob()
        self.job.setDirData(path, db)
        QTimer.singleShot(0, self.job.updateDir)
        return self.app.exec_()
    
    def updateFileTags(self, file, db):
        self._initNepomuk()                
        self.job = self.NepomukJob()
        self.job.setFileData(file, db)
        QTimer.singleShot(0, self.job.updateFile)
        return self.app.exec_()  
    
    class NepomukJob(QObject):
        
        ndbu_uri = 'http://www.semanticdesktop.org/ontologies/2012/02/07/ndbu#%s'
        file_count = 1        
        abort = False
        
        def __init__(self):
            QObject.__init__(self)
            
        def setDirData(self, path, db):
            self.start_path = path
            self.db = db
            
        def setFileData(self, path, db):
            self.file_path = path
            self.db = db
            
        def cancelJob(self):
            self.abort = True

        def updateDirTags(self, directory):
            loop = QEventLoop()
            for name in listdir(directory):
                if self.abort: break
                full_path = join(directory, name)
                if isdir(full_path):
                    self.updateDirTags(full_path)
                elif isfile(full_path):
                    logging.debug('(%i) Processing %s' % (self.file_count, name))
                    post = self.db.getPost(name)
                    if post:
                        res = self.getResource(full_path)
                        self.updateFileTags(res, post, skip=True)
                        self.file_count += 1
                        loop.processEvents()
                    else:
                        logging.debug('%s isn\'t in database' % name)
            QCoreApplication.quit()
                
        def updateFile(self):
            self.updateFileTags(self.file_path)
            
        def updateDir(self):
            self.updateDirTags(self.start_path)
            
        def removeProperties(self, res, ontologies):
            for ontology in ontologies:
                res.removeProperty(KUrl(self.ndbu_uri % ontology))
                
        def setProperty(self, res, ontology, prop):
            res.setProperty(KUrl(self.ndbu_uri % ontology), Nepomuk.Variant(prop))
            
        def getResource(self, res):
            if isinstance(res, str):
                absolute_path = abspath(res)
                return Nepomuk.File(KUrl(absolute_path))
            else:
                return res
            
        def _addTag(self, res, name):
            tag = Nepomuk.Tag(name)
            tag.setLabel(name)
            res.addTag(tag)
            
        def updateFileTags(self, filename, post, skip=False):
            res = self.getResource(filename)
            
            if skip and self.ndbu_uri % 'postId' in res.allProperties():
                return
            self.removeTags(filename)
            for name in post['tags']:
                self._addTag(res, name)
            
            url = KUrl(post['board_url'])
            url_res = Nepomuk.Resource(url)
            url_res.addType(Nepomuk.Vocabulary.NFO.Website())
            res.addIsRelated(url_res)
            
            if post['source']:
                url = KUrl(post['source'])
                res.setDescription("Source: %s" % url.prettyUrl())

            if post['score']:
                self._addTag(res, "score:%s" % post['score'])
            if post['author']:
                self._addTag(res, "author:%s" % post['author'])
            if post['rating']:
                self._addTag(res, "rating:%s" % post['rating'])
            if post['id']:
                self._addTag(res, "id:%s" % post['id'])    
                
        def setRating(self, file, rating):
            if rating not in range(0, 11): return
            resource = self.getResource(file)
            resource.setRating(rating)
            
        def getRating(self, file):
            resource = self.getResource(file)
            return resource.rating()
                
        def getTags(self, file):
            resource = self.getResource(file)
            return [x.label() for x in resource.tags()]
            
        def removeTags(self, file):        
            resource = self.getResource(file)
            resource.removeProperty(resource.tagUri())

