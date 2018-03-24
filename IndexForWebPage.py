#!/usr/bin/env python
# -*- coding:utf-8 -*-
from bs4 import BeautifulSoup
import urllib
import re
import lucene
import jieba
import sys
import os
import threading
import time
from datetime import datetime
from java.io import File
from org.apache.lucene.analysis.miscellaneous import LimitTokenCountAnalyzer
from org.apache.lucene.analysis.core import WhitespaceAnalyzer
from org.apache.lucene.document import Document, Field, FieldType
from org.apache.lucene.index import FieldInfo, IndexWriter, IndexWriterConfig
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.util import Version

INDEX_DIR = "IndexFiles.index"

"""
This class is loosely based on the Lucene (java implementation) demo class
org.apache.lucene.demo.IndexFiles.  It will take a directory as an argument
and will index all of the files in that directory and downward recursively.
It will index on the file path, the file name and the file contents.  The
resulting Lucene index will be placed in the current directory and called
'index'.
"""


class Ticker(object):
    def __init__(self):
        self.tick = True

    def run(self):
        while self.tick:
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(1.0)


class IndexFiles(object):
    """Usage: python IndexFiles <doc_directory>"""

    def __init__(self, root, storeDir, analyzer):

        if not os.path.exists(storeDir):
            os.mkdir(storeDir)

        store = SimpleFSDirectory(File(storeDir))
        analyzer = LimitTokenCountAnalyzer(analyzer, 1048576)
        config = IndexWriterConfig(Version.LUCENE_CURRENT, analyzer)
        config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
        writer = IndexWriter(store, config)

        self.indexDocs(root, writer)
        ticker = Ticker()
        print 'commit index',
        threading.Thread(target=ticker.run).start()
        writer.commit()
        writer.close()
        ticker.tick = False
        print 'done'

    def indexDocs(self, root, writer):

        t1 = FieldType()
        t1.setIndexed(True)
        t1.setStored(True)
        t1.setTokenized(False)
        t1.setIndexOptions(FieldInfo.IndexOptions.DOCS_AND_FREQS)

        t2 = FieldType()
        t2.setIndexed(True)
        t2.setStored(False)
        t2.setTokenized(True)
        t2.setIndexOptions(FieldInfo.IndexOptions.DOCS_AND_FREQS_AND_POSITIONS)

        global x
        for root, dirnames, filenames in os.walk(root):
            for filename in filenames:
                if not filename.startswith('http'):
                    continue
                try:
                    path = os.path.join(root, filename)
                    file = open(path)
                    soup = BeautifulSoup(file.read(), 'lxml')
                    contents = unicode(''.join(soup.findAll(text=True)).encode('utf-8'), 'utf-8')
                    imgurl = ''
                    for i in soup.findAll('title'):
                        title = i.get_text()
                        break
                    file.close()
                    f = open('index.txt', 'r')
                    for line in f.xreadlines():
                        list = []
                        for element in line.strip().split('\t'):
                            list.append(element)
                        if len(list) == 2:
                            if list[1] == filename:
                                url = list[0]
                    proto, rest = urllib.splittype(url)
                    res, rest = urllib.splithost(rest)
                    p = re.compile('(\w+)\.(.+)')
                    m = p.match(res)
                    domain = m.group(2)
                    for j in soup.findAll('img', {'src': re.compile('^http://img.xiami.net/images/album/')}):
                        imgurl = j.get('src', '')
                        break
                    for k in soup.findAll('h1', {'property': re.compile('v:itemreviewed')}):
                        if "<span>" not in str(k):
                            album = k.get_text()
                            subalbum = ''
                        else:
                            a = re.compile('<h1 property="v:itemreviewed">(.*)<span>(.*)</span>(.*)')
                            b = a.match(str(k))
                            album = b.group(1)
                            subalbum = b.group(2)
                        break
                    for t in soup.findAll('a', {'href': re.compile('^/artist/')}):
                        singer = t.get_text()
                        break
                    s = 1
                    reviews = ""
                    for l in soup.findAll('div', {'id': re.compile('^brief_')}):
                        if s <= 3:
                            tmp = l.get_text().strip().split('\n')
                            reviews += tmp[0] + '\n'
                            s += 1
                    if imgurl != '':
                        print "adding", x, url, album, imgurl
                        urllib.urlretrieve(imgurl, './imgs/%s.jpg' % x)
                        doc = Document()
                        doc.add(Field("url", url, t1))
                        doc.add(Field("domain", domain, t1))
                        doc.add(Field("title", title, t1))
                        doc.add(Field("path", root, t1))
                        doc.add(Field("name", filename, t1))
                        doc.add(Field("imgurl", imgurl, t1))
                        doc.add(Field("album", album, t1))
                        doc.add(Field("subalbum", subalbum, t1))
                        doc.add(Field("singer", singer, t1))
                        doc.add(Field("reviews", reviews, t1))
                        doc.add(Field("imgnum", str(x), t1))
                        if len(contents) > 0:
                            seg_list = jieba.cut(contents)
                            contents = " ".join(seg_list)
                            doc.add(Field("contents", contents, t2))
                        else:
                            print "warning: no content in %s" % filename
                        x += 1
                        writer.addDocument(doc)
                    else:
                        print "warning: %s is empty" % imgurl
                except Exception, e:
                    print "Failed in indexDocs:", e


if __name__ == '__main__':
    """
    if len(sys.argv) < 2:
        print IndexFiles.__doc__
        sys.exit(1)
    """
    x = 1
    lucene.initVM(vmargs=['-Djava.awt.headless=true'])
    print 'lucene', lucene.VERSION
    start = datetime.now()
    try:
        """
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        IndexFiles(sys.argv[1], os.path.join(base_dir, INDEX_DIR),
                   StandardAnalyzer(Version.LUCENE_CURRENT))
                   """
        analyzer = WhitespaceAnalyzer(Version.LUCENE_CURRENT)
        IndexFiles('html', 'WebPageIndex', analyzer)
        end = datetime.now()
        print end - start
    except Exception, e:
        print "Failed: ", e
        raise e
