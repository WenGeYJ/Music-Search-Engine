# -*-coding:utf-8 -*-

from web import form
import jieba
import re
import lucene
from bs4 import BeautifulSoup
import cv2
import numpy as np
import random
import os
import web
from java.io import File
from org.apache.lucene.analysis.core import WhitespaceAnalyzer
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.util import Version
from org.apache.lucene.search import BooleanQuery
from org.apache.lucene.search import BooleanClause
import sys


reload(sys)
sys.setdefaultencoding('utf8')


def similar(command):
    results = []
    tmp = []
    words = command.strip().split(' ')
    lenth = len(words)
    for i in range(lenth):
        tmp.append([])
    f = open('dict.txt', 'r')
    for i in range(lenth):
        tmp[i].append(words[i])
        for line in f.xreadlines():
            line_word_list = line.strip().split(' ')
            line_word = line_word_list[0].decode('utf-8')
            differ_char = 0
            if (len(line_word) != len(words[i])):
                continue
            for j in range(len(line_word)):
                if line_word[j] != words[i][j]:
                    differ_char += 1
            if differ_char == 1:
                tmp[i].append(line_word)
    f.close()
    if lenth == 1:
        for item in tmp[0]:
            if len(results) > 30:
                break
            else:
                results.append(item)
    elif lenth == 2:
        for item0 in tmp[0]:
            for item1 in tmp[1]:
                if len(results) > 30:
                    break
                else:
                    results.append(item0 + item1)
    elif lenth == 3:
        for item0 in tmp[0]:
            for item1 in tmp[1]:
                for item2 in tmp[2]:
                    if len(results) > 30:
                        break
                    else:
                        results.append(item0 + item1 + item2)
    return results


def search_site(command):
    STORE_DIR = "WebPageIndex"
    directory = SimpleFSDirectory(File(STORE_DIR))
    searcher = IndexSearcher(DirectoryReader.open(directory))
    analyzer = WhitespaceAnalyzer(Version.LUCENE_CURRENT)
    raw_command = command
    site = ''
    command = ''
    try:
        p = re.compile('(.*)singer:(.*)')
        m = p.match(raw_command)
        command = m.group(1)
        site = m.group(2)
    except:
         pass
    if site == '':
        command = raw_command
    seg_list = jieba.cut(command)
    command = " ".join(seg_list)

    if site == '':
        query = QueryParser(Version.LUCENE_CURRENT, "contents",
                            analyzer).parse(command)
        scoreDocs = searcher.search(query, 50).scoreDocs
        results = []
        results.append(similar(command))
        for scoreDoc in scoreDocs:
            result = []
            doc = searcher.doc(scoreDoc.doc)
            result.append(doc.get("album"))
            result.append(doc.get("subalbum"))
            result.append(doc.get("singer"))
            result.append(doc.get("url"))
            result.append(doc.get("reviews"))
            result.append(doc.get("imgurl"))
            result.append(doc.get("imgnum"))
            results.append(result)
    else:
        querys = BooleanQuery()
        query_contents = QueryParser(Version.LUCENE_CURRENT, "contents",
                            analyzer).parse(command)
        querys.add(query_contents, BooleanClause.Occur.MUST)
        query_domain = QueryParser(Version.LUCENE_CURRENT, "singer",
                            analyzer).parse(site)
        querys.add(query_domain, BooleanClause.Occur.MUST)
        scoreDocs = searcher.search(querys, 50).scoreDocs
        results = []
        results.append(similar(command))
        for scoreDoc in scoreDocs:
            result = []
            doc = searcher.doc(scoreDoc.doc)
            result.append(doc.get("album"))
            result.append(doc.get("subalbum"))
            result.append(doc.get("singer"))
            result.append(doc.get("url"))
            result.append(doc.get("reviews"))
            result.append(doc.get("imgurl"))
            result.append(doc.get("imgnum"))
            results.append(result)
    del searcher

    return results


# 计算颜色值方图的(G,B,R)三维向量
def histograph(img):
    shape = img.shape[:2]
    B = G = R = 0.0
    for y in range(shape[0]):
        for x in range(shape[1]):
            B += img[y][x][0]
            G += img[y][x][1]
            R += img[y][x][2]
    vector = [B/(B+G+R), G/(B+G+R), R/(B+G+R)]
    return vector


# 计算图片img的12维特征向量
def eigenvector(img):
    shape = img.shape[:2]
    mid_y = shape[0]/2
    mid_x = shape[1]/2
    H1 = np.zeros((mid_y, mid_x, 3))  # 图片拆分成四个部分
    H2 = np.zeros((mid_y, shape[1]-mid_x, 3))
    H3 = np.zeros((shape[0]-mid_y, mid_x, 3))
    H4 = np.zeros((shape[0]-mid_y, shape[1]-mid_x, 3))
    sub_parts = [H1, H2, H3, H4]  # 这四个部分一起作为一个列表 代表原图
    for y in range(mid_y):
        for x in range(mid_x):
            H1[y][x] = img[y][x][:3]
    for y in range(mid_y):
        for x in range(mid_x, shape[1]):
            H2[y][x - mid_x] = img[y][x][:3]
    for y in range(mid_y, shape[0]):
        for x in range(mid_x):
            H3[y - mid_y][x] = img[y][x][:3]
    for y in range(mid_y, shape[0]):
        for x in range(mid_x, shape[1]):
            H4[y - mid_y][x - mid_x] = img[y][x][:3]
    eigenvector = []  # 初始化特征向量
    for part in sub_parts:  # 对每一部分调用histograph计算RGB
        vector = histograph(part)
        for item in vector:  # 进行量化
            if 0 <= item < 0.3:
                item = 0
            elif 0.3 <= item < 0.6:
                item = 1
            else:
                item = 2
            eigenvector.append(item)  # 结果存入特征向量并返回
    return eigenvector


# 生成一组n个每个m位的哈希函数
def Hash(n, m, C=2):
    hashlist = [[6, 10, 18, 19], [2, 7, 10, 21], [3, 5, 6, 23]]  # 经尝试选择的一组合适哈希
    '''hashlist = []  # 随机产生一组n个m位的哈希函数 特征向量的每位对应C位海明码 默认C=2
    while len(hashlist) < n:
        randomdata = range(1, 12*C+1)
        randomlist = random.sample(randomdata, m)
        randomlist = sorted(randomlist)
        if randomlist not in hashlist:
            hashlist.append(randomlist)'''
    return hashlist  # 返回包含了n个哈希函数的列表


# 将特征向量p转化为海明码
def Hamming(p, C=2):
    hamming = []
    for item in p:  # 每一段C位
        for i in range(item):  # 前pi个为1
            hamming.append(1)
        for i in range(C-item):  # 后面为0
            hamming.append(0)
    return hamming


#  将海明码投影到哈希函数上 即截取某几位
def project(hamming, hash):
    projection = []
    for item in hash:
        projection.append(hamming[item-1])
    return projection  # 返回海明码的投影


# 若需要精确匹配
def accurate_match(foldername, target, to_match):
    if len(to_match) != 0:
        orb = cv2.ORB()  # 下面是与NN搜索相同的过程 方便控制变量进行比较
        target_kp, target_des = orb.detectAndCompute(target, None)
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        result = {}
        for img_number in to_match:
            img = cv2.imread(foldername+"/%s.jpg" % (img_number), cv2.IMREAD_COLOR)
            kp, des = orb.detectAndCompute(img, None)
            matches = bf.match(target_des, des)
            result[img_number] = len(matches)
        output = []
        inorder = sorted(result.values())[::-1]
        pre = 0
        for item in inorder:
            if pre == item:
                continue
            else:
                pre = item
                for i in range(len(result)):
                    if result.values()[i] == item:
                        output.append(result.keys()[i])
                        break
    return output


def read_statistic(filename):
    f = open(filename, 'r')
    statistic = [{}, {}, {}]
    n = -1
    tmp_key = ''
    for line in f.xreadlines():
        for element in line.strip().split('\t'):
            if len(element) == 1:
                n += 1
            elif len(element) == 4:
                statistic[n][element] = []
                tmp_key = element
            else:
                p = re.compile('\[(.*)\]')
                m = p.match(element)
                if m.group(1) != '':
                    for k in m.group(1).strip().split(', '):
                        statistic[n][tmp_key].append(int(k))
    f.close()
    return statistic


def match_imgs(filename):
    n = 3  # 每组哈希函数个数
    m = 4  # 每个哈希函数长度
    hashlist = Hash(n, m)  # 生成哈希数列表
    statistic = read_statistic('img_index.txt')
    target = cv2.imread(filename, cv2.IMREAD_COLOR)  # 读取目标图片进行相同的操作
    p = eigenvector(target)
    hamming = Hamming(p)
    to_match = []
    for i in range(n):  # 初始化to_match
        to_match.append([])
    for i in range(n):  # 每一组桶中都去匹配
        projection = project(hamming, hashlist[i])
        key = ''
        for item in projection:
            key += str(item)
        for img_number in statistic[i][key]:
            if img_number not in to_match[i]:
                to_match[i].append(img_number)
    tmp = to_match[0]
    for i in range(1, n):  # 求结果的交集 即为lsh的匹配结果
        tmp = list(set(to_match[i]).intersection(set(tmp)))
    intersection = tmp
    output = accurate_match('imgs', target, intersection)  # 进一步精确匹配
    return output


def search_img(output):
    STORE_DIR = "WebPageIndex"
    directory = SimpleFSDirectory(File(STORE_DIR))
    searcher = IndexSearcher(DirectoryReader.open(directory))
    analyzer = WhitespaceAnalyzer(Version.LUCENE_CURRENT)
    results = []
    results.append([])
    for num in output:
        imgnum = str(num)
        query = QueryParser(Version.LUCENE_CURRENT, "imgnum",
                            analyzer).parse(imgnum)
        scoreDocs = searcher.search(query, 1).scoreDocs
        for scoreDoc in scoreDocs:
            result = []
            doc = searcher.doc(scoreDoc.doc)
            result.append(doc.get("album"))
            result.append(doc.get("subalbum"))
            result.append(doc.get("singer"))
            result.append(doc.get("url"))
            result.append(doc.get("reviews"))
            result.append(doc.get("imgurl"))
            result.append(doc.get("imgnum"))
            results.append(result)
    del searcher
    return results


urls = (
    '/', 'index',
    '/im', 'index_img',
    '/t', 'text',
    '/i', 'image',
)

render = web.template.render('templates')

class index:
    def GET(self):
        return render.HomePage_text()

class index_img:
    def GET(self):
        return render.HomePage_pic()

class text:
    def GET(self):
        i = web.input()
        ikeyword = i.keyword
        if ikeyword=="":
            return render.result_text(ikeyword, [[]], 0)
        vm_env = lucene.getVMEnv()
        vm_env.attachCurrentThread()
        results = search_site(ikeyword)
        print len(results[0])
        length = len(results)
        return render.result_text(ikeyword, results, length)



class image:
    def POST(self):
        i = web.input(myfile={})
        f=open('target.jpg','w')
        f.write(str(i['myfile'].value))
        f.close()
        ikeyword='blank'
        if i.myfile.value == "":
            return render.result_pic(ikeyword,[[]], 0)
        vm_env = lucene.getVMEnv()
        vm_env.attachCurrentThread()
        results = search_img(match_imgs("target.jpg"))
        length = len(results)
        return render.result_pic(ikeyword, results, length)


if __name__ == "__main__":
    vm_env = lucene.initVM()
    app = web.application(urls, globals())
    app.run()