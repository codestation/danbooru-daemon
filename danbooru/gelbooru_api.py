import danbooru

import xml.dom.minidom


class GelbooruAPI(danbooru.api.Api):

    POST_API = "/index.php?page=dapi&s=post&q=index"

    def __init__(self, host):
        self.host = host
        self._delta_time = 0

    def getPostsPage(self, tag, query, page, limit, blacklist=None, whitelist=None):
        url = "%s%s&tags=%s&pid=%i&limit=%i" % (self.host, self.POST_API, tag, page, limit)
        return self.getPosts(url, query, blacklist, whitelist)

    def getPosts(self, url, query, blacklist, whitelist):
        data = self._getData(url)
        dom = xml.dom.minidom.parseString(data)
        if dom.childNodes:
            posts = [dict(node.attributes.items()) for node in dom.childNodes[0].childNodes if isinstance(node, xml.dom.minidom.Element)]
            return self._processPosts(posts, query, blacklist, whitelist)
