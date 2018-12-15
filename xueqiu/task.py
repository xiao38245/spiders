# -*- coding:utf-8 -*-
import pymysql
import redis
import requests
import logging
import random

# mysql数据库
SERVER_HOST = "192.168.24.28"
SERVER_PORT = 3306
SERVER_DB = "statistics_data"
SERVER_USER = "crawler"
SERVER_PASS = "crawler"

# redis数据库
REDIS_KEY = 'proxy'
REDIS_HOST = "192.168.24.28"
REDIS_PORT = 6379
REDIS_PASSWORD = 'JVqbpWLgvtaSHF2n'

redis_server = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=0)

# 连接数据库


def connect_mysql():
    conn = pymysql.connect(host=SERVER_HOST, port=SERVER_PORT,
                           user=SERVER_USER, password=SERVER_PASS,
                           database=SERVER_DB)
    return conn

# 断开数据库


def close_mysql(conn):
    conn.close()


conn = connect_mysql()

# 创建表---feiliao


def create_table_feiliao():
    cursor = conn.cursor()
    sql = """create table `t_crawl_feiliao` (
        `id` int(10) NOT NULL PRIMARY KEY AUTO_INCREMENT,
        `company_name` text COMMENT '公司名称',
        `product_generic_name` text COMMENT '产品通用名',
        `product_name` text COMMENT '产品商品名',
        `product_form` text COMMENT '产品形态',
        `registration_technical_indicators` text COMMENT '登记技术指标',
        `applicable_crops` text COMMENT '适用作物',
        `registration_number` text COMMENT '登记证号')"""
    cursor.execute(sql)
    cursor.close()
    conn.commit()


"""
    reg_code        登记证号
    effective_time  登记日期
    cutoff_time     截止日期
    reg_name        登记名称
    poison          毒性
    formulation     剂型
    manufacturer    生产公司
    country         国家
    pest_type       农药类型
    content         总含量
    label_url       标签地址
    component       有效成分
    dosage          制药信息
    """


def create_table_nongyao():
    cursor = conn.cursor()
    sql = """create table `t_crawl_nongyao` (
        `id` int(10) NOT NULL PRIMARY KEY AUTO_INCREMENT,
        `reg_code` text COMMENT '登记证号',
        `effective_time` text COMMENT '登记日期',
        `cutoff_time` text COMMENT '截止日期',
        `reg_name` text COMMENT '登记名称',
        `poison` text COMMENT '毒性',
        `formulation` text COMMENT '剂型',
        `manufacturer` text COMMENT '生产公司',
        `country` text COMMENT '国家',
        `pest_type` text COMMENT '农药类型',
        `content` text COMMENT '总含量',
        `label_url` text COMMENT '标签地址',
        `component` text COMMENT '有效成分',
        `dosage` text COMMENT '制药信息')"""
    cursor.execute(sql)
    cursor.close()
    conn.commit()


def insertTB(sql):
    """
    :return:
    """
    cursor = conn.cursor()
    cursor.execute(sql)
    cursor.close()
    conn.commit()


def selectTB(sql):
    cursor = conn.cursor()
    cursor.execute(sql)
    search_list = cursor.fetchall()
    cursor.close()
    conn.commit()
    return search_list

# 获取ip


def getip():
    ip_url = 'http://mvip.piping.mogumiao.com/proxy/api/get_ip_bs?appKey=1a212c92f429422e811d06b4446f8ec5&count=100&expiryDate=0&format=1&newLine=2'
    # 判断一下键长度,如果低于20,请求接口获取json数据,写进redis
    if redis_server.llen(REDIS_KEY) < 30:
        ip_json = requests.get(ip_url).json()
        if ip_json["code"] == '0':
            for i in ip_json['msg']:
                proxy = 'http://{}:{}'.format(i['ip'], i['port'])
                redis_server.lpush(REDIS_KEY, proxy)
            check_ip()
        else:
            print(ip_json["code"])
            print('ip获取失败')
    else:
        check_ip()

# 校验ip是否可用


def check_ip():
    proxy_ip = redis_server.blpop(REDIS_KEY)
    post = str(proxy_ip[1], encoding='utf-8')
    proxy = {'http': post}
    headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
    }
    try:
        res = requests.get("http://www.baidu.com",
                           proxies=proxy, headers=headers, timeout=1)
        if res.status_code == 200:
            redis_server.rpush(REDIS_KEY, proxy)
            print(proxy)
            return proxy
        else:
            getip()
    except Exception as e:
        print(proxy, e)
        getip()


# 日志模块
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
handler = logging.FileHandler('outlog.log')
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y/%m/%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)


# 定义随机ua
def random_ua():
    user_agent_list = [
        'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.60 Safari/537.17',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1309.0 Safari/537.17',
        'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0)',
        'Mozilla/5.0 (Windows; U; MSIE 7.0; Windows NT 6.0; en-US)',
        'Mozilla/5.0 (Windows; U; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 2.0.50727)',
        'Mozilla/6.0 (Windows NT 6.2; WOW64; rv:16.0.1) Gecko/20121011 Firefox/16.0.1',
        'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:15.0) Gecko/20100101 Firefox/15.0.1',
        'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:15.0) Gecko/20120910144328 Firefox/15.0.2']
    ua = random.choice(user_agent_list)
    return ua


if __name__ == '__main__':
    getip()
