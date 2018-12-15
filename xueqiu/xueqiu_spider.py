import requests
import time
from lxml import etree
from task import logger


data = {
    'page': '2',
    'size': '90',
    'order': 'desc',
    'orderby': 'percent',
    'type': '11, 12'
}

headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
}

start_url = 'https://xueqiu.com/'

url = 'https://xueqiu.com/stock/cata/stocklist.json?page=2&size=90&order=desc&orderby=percent&type=11%2C12'


def get_url():
    session = requests.session()
    html = session.get(start_url, headers=headers)
    response = session.get(url, headers=headers, data=data).text
    print(response)


get_url()
