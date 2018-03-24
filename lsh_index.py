# -*- coding:utf-8 -*-
import cv2
import numpy as np
import random
import os
import re
import time

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


#  读取一个文件夹中所有的图片建立索引
def read_folder(foldername, n, m, hashlist):
    statistic = []  # 统计结果 即索引
    for i in range(n):
        statistic.append({})  # 初始化统计结果
    for i in range(n):
        for j in range(2 ** m):
            key = ('{0:0%sb}' % m).format(j)  # key为'0000'到‘1111’
            statistic[i][key] = []  # value为列表

    for root, dirnames, filenames in os.walk(foldername):  # 遍历pic文件夹下的文件
        for filename in filenames:
            print "adding", filename
            path = os.path.join(root, filename)
            p = re.compile('(.*)\.jpg')
            m = p.match(filename)
            img_number = int(m.group(1))
            # 以彩色方式读取图片
            target = cv2.imread(path, cv2.IMREAD_COLOR)
            p = eigenvector(target)  # 计算特征向量
            hamming = Hamming(p)  # 计算海明码
            for i in range(n):  # 所有的图片对每一个哈希函数都要进行一遍投影
                projection = project(hamming, hashlist[i])  # 计算投影
                key = ''
                for item in projection:
                    key += str(item)
                statistic[i][key].append(img_number)  # 装入桶中
        return statistic


def main():
    n = 3  # 每组哈希函数个数
    m = 4  # 每个哈希函数长度
    start = time.clock()
    hashlist = Hash(n, m)  # 生成哈希数列表
    statistic = read_folder('imgs', n, m, hashlist)  # 建立索引
    index = open('img_index.txt', 'a')
    for i in range(n):
        index.write(str(i) + '\n')
        items = statistic[i].items()
        for item in items:
            index.write(item[0] + '\t' + str(item[1]) + '\n')
    index.close()

    print statistic[0].items()
    end = time.clock()
    print end-start  # 得出唯一结果总用时
main()