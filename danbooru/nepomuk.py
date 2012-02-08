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

from os.path import abspath
from PyKDE4.kdecore import KUrl
from PyKDE4.nepomuk import Nepomuk

class NepomukBus(object):
    
    ndbu_uri = 'http://www.semanticdesktop.org/ontologies/2012/02/07/ndbu#%s'

    def __init__(self):
        if Nepomuk.ResourceManager.instance().init() != 0:
            raise Exception('Error initializing nepomuk')
        
    def removeProperties(self, res, ontologies):
        for ontology in ontologies:
            res.removeProperty(KUrl(self.ndbu_uri % ontology))
            
    def setProperty(self, res, ontology, prop):
        res.setProperty(KUrl(self.ndbu_uri % ontology), Nepomuk.Variant(prop))
        
    def getResource(self, res):
        if isinstance(res, str):
            absolute_path = abspath(res)
            return Nepomuk.Resource(KUrl(absolute_path))
        else:
            return res
    
    def updateTags(self, filename, post):
        res = self.getResource(filename)
        self.removeTags(filename)
        for name in post['tags']:
            tag = Nepomuk.Tag(name)
            tag.setLabel(name)
            res.addTag(tag)
        if post['source']:     
            self.setProperty(res, 'source', KUrl(post['source']))            
        else:
            self.removeProperties(res, ['source'])
        self.setProperty(res, 'score', post['score'])
        self.setProperty(res, 'author', post['author'])
        self.setProperty(res, 'postId', post['id'])
        self.setProperty(res, 'rating', post['rating'])
            
    def setRating(self, file, rating):
        if rating not in range(0, 11): return
        resource = self.getResource(file)
        resource.setRating(rating)
        
    def getRating(self, file):
        resource = self.getResource(file)
        return resource.rating()
            
    def getTags(self, file):
        resource = self.getResource(file)
        for i in resource.tags():
            print(i.label())
        return [x.label() for x in resource.tags()]
        
    def removeTags(self, file):        
        resource = self.getResource(file)
        resource.removeProperty(resource.tagUri())
