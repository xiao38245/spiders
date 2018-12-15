from __future__ import with_statement  # Required in 2.5

import logging
import signal
import time
import traceback
from contextlib import contextmanager
from multiprocessing import Pool

import pymysql

from article_extractor import extract_article

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
handler = logging.FileHandler('outlog.log')
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y/%m/%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)


SERVER_HOST = "192.168.24.101"
SERVER_PORT = 3306
SERVER_DB = "statistics_data"
SERVER_USER = "crawler"
SERVER_PASS = "crawler"
mysql_server = pymysql.connect(host=SERVER_HOST, port=SERVER_PORT, user=SERVER_USER,
                               password=SERVER_PASS, database=SERVER_DB)



class TimeoutException(Exception): 
    pass

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def select_db(num):
    dbconn = mysql_server.cursor()
    sql = "select title,search,search_url,data,id from t_baidu where id >= {} and id <={}".format(
        num * 100, (num +1) * 100)
    dbconn.execute(sql)
    data = dbconn.fetchall()
    return data


def sql_to_TB(sql):
    try:
        cursor = mysql_server.cursor()
        with time_limit(10):
            cursor.execute(sql)
        cursor.close()
        mysql_server.commit()
        return True
    except TimeoutException:
        print("Timed out!")
        return False
    except Exception as e:
        s = traceback.format_exc()
        logger.error(s)
        print(s)
        return False


def run(data):
    try:
        # 做超时判断，如果十分钟没有清洗成功，报超时错误
        with time_limit(600):
            # 调用已经写好的算法，清洗数据
            text = extract_article(data[2], data[3])
        # 写入数据库
        col_name = "title,search,search_url,data"
        sql = "insert into t_clean_baidu(%s) values('%s','%s','%s','%s');" % (
            col_name, data[0], data[1], data[2], str(text).replace("'", "''").replace('"', '""'))
        if sql_to_TB(sql):
            logger.info(data[4])
            a = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
            print('{} 清洗成功'.format(a))
        else:
            b = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
            print('{} 清洗失败'.format(b))
    
    except TimeoutException:
        print("超时退出")

    except ValueError:
        s = traceback.format_exc()
        logger.error(s)
        print(s)

    except AttributeError:
        s = traceback.format_exc()
        logger.error(s)
        print(s)
    


for num in range(1069, 14256):
    datas = select_db(num)
    p = Pool()
    for data in datas:
        p.apply_async(run, args=(data,))
    p.close()
    p.join()
