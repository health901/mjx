#!/usr/bin/python
# -*- coding: UTF-8 -*-

import hashlib
import json
import time
import requests
import os
import http.cookiejar as cookielib
import threading
import threadpool
import sys


def hex_md5(s):
    m = hashlib.md5()
    m.update(s.encode('UTF-8'))
    return m.hexdigest()


class request:
    apiUrl = 'https://acs.m.taobao.com/h5/mtop.taobao.social.feed.aggregate/1.0/'
    appKey = '12574478'
    cookieJar = 'cookie.txt'
    session = requests.session()
    thread_pool = []
    fails = []
    dir_path = ''
    sellerId = 0

    def __init__(self):
        self.session.cookies = cookielib.LWPCookieJar(filename=self.cookieJar)
        if os.path.exists(self.cookieJar):
            self.session.cookies.load(ignore_discard=True)

    def set_seller(self, id):
        self.sellerId = id
        self.dir_path = str(self.sellerId)
        if not os.path.exists(self.dir_path):
            os.mkdir(self.dir_path, 755)

    def get_shop_page(self, index, num):
        data = {
            'params': json.dumps({
                'nodeId': '',
                'sellerId': self.sellerId,
                'pagination': {
                    'direction': 1,
                    'hasMore': 'true',
                    'pageNum': index,
                    'pageSize': num,
                }
            }),
            'cursor': index,
            'pageNum': index,
            'pageId': 5703,
            'env': 1
        }
        dataJson = json.dumps(data)
        params = {
            'appKey': self.appKey,
            'data': dataJson
        }
        params = self.sign(params)
        print('加载第' + str(index) + '页数据')

        fn = self.dir_path + '/' + str(index) + '.json'
        if not os.path.exists(fn):
            json_str = self.session.get(self.apiUrl, params=params)
            item = json.loads(json_str.text)

            if item['ret'][0] == u'SUCCESS::调用成功':
                # 第一页有21条，第一条无用
                self.save_list(index, item['data']['list'][-num:])
                if item['data']['pagination']['hasMore'] == 'true':
                    time.sleep(0.5)
                    self.get_shop_page(index + 1, num)
            else:
                time.sleep(1)
                self.get_shop_page(index, num)
        else:
            self.get_shop_page(index + 1, num)

    def sign(self, params):
        cookies = self.get_cookie(params)
        token = cookies['_m_h5_tk'].split('_')[0]
        t = str(int(time.time() * 1000))
        sign_str = token + '&' + t + '&' + self.appKey + '&' + params['data']
        sign = hex_md5(sign_str)
        params['sign'] = sign
        params['t'] = t
        return params

    def get_cookie(self, params):
        cookies = self.cookie_obj()
        
        if '_m_h5_tk' not in cookies.keys():
            html = self.session.get(self.apiUrl, params=params)
            cookies = html.cookies
            self.session.cookies.save()
            cookies = self.cookie_obj()
            print('cookie get')

        return cookies

    def cookie_obj(self):
        cookies = {}
        for cookie in self.session.cookies:
            cookies[cookie.name] = cookie.value
        return cookies

    def save_list(self, page, lst):
        fn = self.dir_path + '/' + str(page) + '.json'
        fp = open(fn, 'w+')
        fp.write(json.dumps(lst))
        fp.close()

    def save_img(self):
        print('开始下载图片/视频')
        dir_path = self.dir_path + '/images'
        if not os.path.exists(dir_path):
            os.mkdir(dir_path, 755)

        i = 0
        exist = True
        tasks = []

        while exist:
            i += 1
            fn = self.dir_path + '/' + str(i) + '.json'
            exist = os.path.exists(fn)
            if exist:
                tasks.append(i)

        pool = threadpool.ThreadPool(5)
        reqs = threadpool.makeRequests(self.download, tasks)

        for req in reqs:
            pool.putRequest(req)
        pool.wait()

    def download(self, args=None):
        self.fails = []
        fn = self.dir_path + '/' + str(args) + '.json'
        f = open(fn)
        data = json.loads(f.read())
        f.close()
        for l in data:
            for pic in l['pics']:
                self.download_img(pic['id'], pic['path'])

            for v in l['videos']:
                self.download_video(v['videoId'], v['videoPath'])

        # for i in [1, 2, 3]:
        #     self.download_fail()

    def download_img(self, id, link):
        dir_path = self.dir_path + '/images'
        path = dir_path + '/' + str(id) + '.jpg'
        self.download_file(link, path)

    def download_video(self, id, link):
        dir_path = self.dir_path + '/images'
        path = dir_path + '/' + str(id) + '.mp4'
        self.download_file(link, path)

    def download_fail(self):
        fails = self.fails
        self.fails = []
        for fail in fails:
            self.download_file(fail['link'], fail['path'])

    def download_file(self, link, path):
        if os.path.exists(path):
            return

        print('download: ' + link)
        r = requests.get(link)
        if len(r.content) != 49:
            with open(path, "wb") as f:
                f.write(r.content)
            f.close()
        else:
            self.fails.append({'link': link, 'path': path})

        time.sleep(0.5)


def main():
    if len(sys.argv) < 2:
        print('请传入店铺ID')
        exit(0)

    sellId = sys.argv[1]

    req = request()
    req.set_seller(sellId)
    req.get_shop_page(1, 20)
    req.save_img()
    print('完成')


if __name__ == '__main__':
    main()
