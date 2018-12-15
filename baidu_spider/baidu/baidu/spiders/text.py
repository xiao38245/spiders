from article_extractor import extract_article
import logging
import pymysql
import traceback

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


def func(num):
    dbconn = mysql_server.cursor()
    sql = "select title,search,search_url,data from t_baidu where id = {}".format(
        num)
    dbconn.execute(sql)
    data = dbconn.fetchall()
    # for i in data:
    #     try:
    #         text = extract_article(i[2], i[3])
    #     except ValueError as e:
    #         s = traceback.format_exc()
    #         logger.error(s)
    #         print(s)
    #         continue
    #     except AttributeError as e:
    #         s = traceback.format_exc()
    #         logger.error(s)
    #         print(s)
    #         continue
    #     col_name = "title,search,search_url,data"
    #     sql = "insert into t_clean_baidu(%s) values('%s','%s','%s','%s');" % (
    #         col_name, i[0], i[1], i[2], str(text).replace("'", "''").replace('"', '""'))
    #     if sql_to_TB(sql):
    #         print('清洗成功')
    #         logger.info(num)
    #     else:
    #         print('清洗失败')

def sql_to_TB(sql):
    """
    :return:
    """
    try:
        cursor = mysql_server.cursor()
        cursor.execute(sql)
        cursor.close()
        mysql_server.commit()
        return True
    except Exception as e:
        logger.error(e)
        return False


def select_db(num):
    dbconn = mysql_server.cursor()
    sql = "select title,search,search_url,data from t_baidu where id = {}".format(
        num)
    dbconn.execute(sql)
    data = dbconn.fetchall()


num = 67655
while True:
    num += 1
    func(num)
