import scrapy
import requests
import re
from ..settings import logger, redis_server, mysql_server
import hashlib
from ..items import BaiduItem


class MySpider(scrapy.Spider):
    name = 'baiduspider'
    start_urls = ['https://www.baidu.com']

    def __init__(self):
        super(MySpider, self).__init__()
        # 初始化 md5
        self.md5 = hashlib.md5()
        self.redis_server = redis_server
        self.mysql_server = mysql_server
        self.search_list = []
        dbconn = self.mysql_server.cursor()
        sql = "select distinct name,crop_name  from t_crop_diseases"
        dbconn.execute(sql)
        data = dbconn.fetchall()
        for i in data:
            search = i[0] + ' ' + i[1]
            self.search_list.append(search)

    def start_requests(self):
        start_url = 'https://www.baidu.com/s?wd={}&pn={}'
        try:
            # 搜索词
            try:
                search_index = self.search_list.index(
                    self.redis_server.get('search').decode('utf8'))
            except ValueError as e:
                print(e)
                search_index = 0
            except AttributeError as e:
                print(e)
                search_index = 0
            # 从搜索词开始循环
            for index in range(search_index, len(self.search_list)):
                # 页码,从redis里获取
                search = self.search_list[index]
                # 从页码开始循环
                for i in range(50):
                    page = i
                    i = i * 10
                    url = start_url.format(search, str(i))
                    yield scrapy.Request(url, meta={'dont_redirect': True, 'search': search, 'page': page, 'i': i})

        except TimeoutError as e:
            logger.warning(e)

    def parse(self, response):
        search = response.meta['search']
        page = response.meta['page']
        search_id = response.meta['i']
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
        }
        for i in range(1, 11):
            try:
                search_url = response.xpath(
                    '//*[@id="{}"]/h3/a/@href'.format(int(search_id)+i)).extract_first()
                if search_url is None:
                    break
                title = response.xpath(
                    '//*[@id="{}"]/h3'.format(int(search_id)+i))
                try:
                    title = title[0].xpath(
                        'string(.)').extract_first().replace(' ', '').replace('\n', '')
                except Exception:
                    title = ''
                res = requests.get(
                    search_url, allow_redirects=False, headers=headers)
                if res.status_code == 200:
                    search_url = re.search(
                        r'URL=\'(.*?)\'', res.text.encode('utf-8'), re.S)
                elif res.status_code == 302:
                    search_url = res.headers.get('location')
                # 对网址加密
                self.md5.update(search_url.encode('utf-8'))
                # 判断网址
                if not self.redis_server.sismember('search_url', self.md5.hexdigest()):
                    # 添加url
                    yield scrapy.Request(search_url, callback=self.parse_detail, meta={
                        'title': title, 'search_url': search_url, 'search': search, 'page': page})
            except TimeoutError as e:
                logger.error(e)
                continue

    def parse_detail(self, response):
        item = BaiduItem()
        try:
            title = response.meta['title']
            search = response.meta['search']
            search_url = response.meta['search_url']
            page = response.meta['page']
            data = response.text
            item['title'] = title
            item['search'] = search
            item['search_url'] = search_url
            item['data'] = str(data)
            self.redis_server.sadd('search_url', self.md5.hexdigest())
            # 添加搜索词
            self.redis_server.set('search', search)
            # 保存爬去到那一页
            self.redis_server.set('page', page)
            yield item
        except Exception as e:
            logger.error(e)
