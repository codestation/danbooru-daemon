from PyQt4 import QtCore
from PyQt4.QtCore import QUrl
from PyKDE4 import kdecore
from PyKDE4.nepomuk import Nepomuk

class NepomukBus(object):
    
    ndbu_uri = 'http://www.semanticdesktop.org/ontologies/2012/02/07/ndbu#%s'

    def __init__(self):
        if Nepomuk.ResourceManager.instance().init() != 0:
            raise Exception('Error initializing nepomuk')
        
    def removeProperties(self, res, ontologies):
        for ontology in ontologies:
            res.removeProperty(QUrl(self.ndbu_uri % ontology))
            
    def setProperty(self, res, ontology, prop):
        res.setProperty(QUrl(self.ndbu_uri % ontology), Nepomuk.Variant(prop))
        
    def getResource(self, res):
        if isinstance(res, str):
            file_info = QtCore.QFileInfo(res)
            absolute_path = file_info.absoluteFilePath()
            return Nepomuk.Resource(kdecore.KUrl(absolute_path))
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
            self.setProperty(res, 'source', QUrl(post['source']))            
        else:
            self.removeProperties(res, ['source'])
        self.setProperty(res, 'score', post['score'])
        self.setProperty(res, 'author', post['author'])
        self.setProperty(res, 'postId', post['id'])
        self.setProperty(res, 'rating', post['rating'])
        self.removeProperties(res, ['source', 'score', 'author', 'postId', 'rating'])
            
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
