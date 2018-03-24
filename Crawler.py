#!/usr/bin/env python
# -*- coding:utf-8 -*-
import urllib2
import urlparse
from bs4 import BeautifulSoup
import re
import os
import threading
import Queue
import time
import chardet


def valid_filename(s):
    import string
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    s = ''.join(c for c in s if c in valid_chars)
    return s


def get_page(page):
    content = ''
    url = page
    user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/21.0'
    heads = {'User-Agent': user_agent}
    request = urllib2.Request(url, headers=heads)
    try:
        content = urllib2.urlopen(request, timeout=10).read()
        content = content.decode('utf-8', 'ignore')
    except:  # (IOError, urllib2.URLError, socket.timeout, httplib.BadStatusLine):
        pass
    return content


def get_all_links(content, page):
    links = []
    soup = BeautifulSoup(content, 'lxml')
    for i in soup.findAll('a', {'href': re.compile('^http|^/')}):
        url = i.get('href','')
        url = urlparse.urljoin(page, url)
        links.append(url)
    return links


def add_page_to_folder(page, content):
    if len(content) > 0:
        index_filename = 'index.txt'
        folder = 'html'
        filename = valid_filename(page)
        if not os.path.exists(folder):
            os.mkdir(folder)
        f = open(os.path.join(folder, filename), 'w')
        content = content.encode('utf-8', 'ignore')
        f.write(content)
        f.close()
        index = open(index_filename, 'a')
        index.write(page.encode('ascii', 'ignore') + '\t' + filename + '\n')
        index.close()
    return


def working():
    global crawled, varLock, q, graph, max_page, counter
    while counter < max_page:
        page = q.get()
        if page not in crawled:
            print page
            content = get_page(page)
            outlinks = get_all_links(content, page)
            for link in outlinks:
                a = re.compile('^http://www.xiami.com/album\w*')
                c = a.match(link)
                b = re.compile('^http://www.xiami.com/artist\w*')
                d = b.match(link)
                if c != None or d != None:
                    q.put(link)
            p = re.compile('^http://www.xiami.com/album/\w*')
            m = p.match(page)
            if m != None and len(page) > 27 and "tag" not in page and "index" not in page and "list" not in page:
                print 'Good Page:', page
                add_page_to_folder(page, content)
                counter += 1
            if varLock.acquire():
                graph[page] = outlinks
                crawled.append(page)
                varLock.release()
            q.task_done()
    return


start = time.clock()
crawled = []
img_crawled = []
graph = {}
varLock = threading.Lock()
NUM = 1
q = Queue.Queue()
q.put('http://www.xiami.com/music/newalbum?spm=a1z1s.6843761.1110925385.3.DHT2DX')
max_page = 1000
counter = 0
threads = []
for i in range(NUM):
    threads.append(threading.Thread(target=working))
for t in threads:
    t.setDaemon(True)
    t.start()
for t in threads:
    t.join()
end = time.clock()
print end - start
