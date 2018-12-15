import json
import re
import time
from newspaper import Article
import chardet

import requests
from lxml import etree

# from task import insertTB, logger, selectTB

# from baidu_spider.baidu.baidu.spiders.article_extractor import extract_article
from article_extractor import extract_article
from task import logger

headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
}

baidu_headers = {
    'user-agent': 'Baiduspider'
}


def get_baidu(search_data, page):
    print('aaa')
    start_url = 'https://www.baidu.com/s?wd={}&pn={}'.format(search_data, page)
    try:
        text = requests.get(start_url, headers=headers,
                            allow_redirects=False, timeout=1).text
    except TimeoutError as e:
        logger.warning(e)
    x_res = etree.HTML(text)
    # 存储爬取的数据，字典
    data = {}
    data['search_data'] = search_data
    for i in range(1, 11):
        try:
            search_url = x_res.xpath('//*[@id="{}"]/h3/a/@href'.format(i))[0]
            title = x_res.xpath('//*[@id="{}"]/h3'.format(i))
            title = title[0].xpath(
                'string(.)').replace(' ', '').replace('\n', '')
            data['title'] = title
            get_search(search_url, data)
        except IndexError as e:
            print(e)
            break


def get_search(search_url, data):
    response = requests.get(search_url, allow_redirects=False, headers=headers)
    try:
        if response.status_code == 200:
            search_url = re.search(
                r'URL=\'(.*?)\'', response.text.encode('utf-8'), re.S)
        elif response.status_code == 302:
            search_url = response.headers.get('location')
        data['search_url'] = search_url
        # 将整个网页数据写入数据库，中间要加降噪算法处理，这里先放在这里
        response = requests.get('https://www.cmeii.com/xingdaoshulei/2418.html', headers=baidu_headers,
                                allow_redirects=False, timeout=1)

        print(chardet.detect(response.content))
        print(response.text.encode('UTF-8-SIG'))

        # print(extract_article('https://www.cmeii.com/xingdaoshulei/2418.html', response.text))
        print('111')

        if response.status_code == 200:
            text = requests.get(search_url, headers=headers,
                                allow_redirects=False, timeout=1).text

            # 降噪，存储数据
            data_save(data, text)
            return search_url, 1
        else:
            return search_url, -1
    except Exception as e:
        logger.warning(e)
        return search_url, -1


def data_save(data, text):
    pass


data = '重阳木 疾病'
get_baidu(data, 3)
