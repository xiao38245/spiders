# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pymysql
from .settings import logger

SERVER_HOST = "192.168.24.101"
SERVER_PORT = 3306
SERVER_DB = "statistics_data"
SERVER_USER = "crawler"
SERVER_PASS = "crawler"


class BaiduPipeline(object):
    def __init__(self):
        self.server = pymysql.connect(host=SERVER_HOST, port=SERVER_PORT, user=SERVER_USER,
                                      password=SERVER_PASS, database=SERVER_DB)

    def insertTB(self, sql):

        try:
            cursor = self.server.cursor()
            cursor.execute(sql)
            cursor.close()
            self.server.commit()
        except Exception as e:
            logger.error(e)

    def process_item(self, item, spider):
        col_name = "title,search,search_url,data"
        # valuses = "'%s','%s','%s','%s'" % \
        #     (item['title'], item['search'], item['search_url'], item['data'])
        sql = "insert into t_baidu(%s) values('%s','%s','%s','%s');" % (
            col_name, item['title'].replace("'", "''").replace('"', '""'), item['search'], item['search_url'], item['data'].replace("'", "''").replace('"', '""'))
        self.insertTB(sql)
