# -*-coding:utf-8 -*-
import requests
import time
from lxml import etree
from task import logger

headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
}


def get_city():
    # 获取json形式的编码
    try:
        code_url = 'https://www.zhipin.com/common/data/city.json'
        r = requests.get(code_url, headers=headers).json()
        city_list = r['data']['cityList']
        code_dict = {}
        for city in city_list:
            sub_list = city['subLevelModelList']
            for sub in sub_list:
                code = sub['code']
                name = sub['name']
                code_dict[name] = code
        return code_dict
    except Exception as e:
        logger.warning(e)


def parse(text):
    detail_url = 'https://www.zhipin.com'
    x_res = etree.HTML(text)
    try:
        url_xpath = x_res.xpath(
            '//*[@id="main"]/div/div[@class="job-list"]/ul/li')
    except Exception as e:
        logger.warning(e)
    try:
        for url in url_xpath:
            time.sleep(10.1)
            a = url.xpath('./div/div[@class="info-primary"]/h3/a/@href')[0]
            url = detail_url + a
            response = requests.get(url, headers=headers)
            parse_detail(response.text)
    except Exception as e:
        logger.warning(e)
        print(e)


def parse_detail(text):
    """
    jobs        招聘岗位
    time        发布时间
    money       工资区间
    city        城市
    requirement 经验要求
    education   学历
    tag         标签
    company     招聘公司
    company_info  公司简介
    sec         具体要求

    """
    time.sleep(4)
    data = {}
    r_xpath = etree.HTML(text)
    data['jobs'] = r_xpath.xpath(
        '//*[@id="main"]/div[@class="job-banner"]/div/div/div[@class="info-primary"]/div[@class="name"]/h1/text()')[0]
    data['time'] = r_xpath.xpath(
        '//*[@id="main"]/div[@class="job-banner"]/div/div/div[@class="info-primary"]/div[@class="job-author"]/span/text()')[0]
    data['money'] = r_xpath.xpath(
        '//*[@id="main"]/div[1]/div/div/div[2]/div[2]/span/text()')[0].replace(' ', '').replace('\n', '')
    data['city'] = r_xpath.xpath(
        '//*[@id="main"]/div[@class="job-banner"]/div/div/div[@class="info-primary"]/p/text()')[0].split('：')[-1]
    data['requirement'] = r_xpath.xpath(
        '//*[@id="main"]/div[@class="job-banner"]/div/div/div[@class="info-primary"]/p/text()')[1].split('：')[-1]
    data['education'] = r_xpath.xpath(
        '//*[@id="main"]/div[@class="job-banner"]/div/div/div[@class="info-primary"]/p/text()')[2].split('：')[-1]
    data['tag'] = r_xpath.xpath(
        '//*[@id="main"]/div[1]/div/div/div[2]/div[3]/span/text()')
    data['company'] = r_xpath.xpath(
        '//*[@id="main"]/div[1]/div/div/div[3]/h3/a/text()')
    data['company_info'] = r_xpath.xpath(
        '//*[@id="main"]/div[1]/div/div/div[3]/p/text()')
    data['sec'] = r_xpath.xpath(
        '//*[@id="main"]/div[3]/div/div[2]/div[3]/div[1]/div/text()')
    with open('a.csv', 'a') as file:
        file.write(str(data))
        file.write('\n')


def main():
    start_url = 'https://www.zhipin.com/c{}/?query=%E6%95%B0%E6%8D%AE%E6%8C%96%E6%8E%98&page={}'
    code_dict = get_city()
    for name in code_dict:
        if name == '北京' or name == '长春':
            continue
        code = code_dict[name]
        logger.info('开始爬取{}的岗位'.format(name))
        for i in range(1, 11):
            url = start_url.format(code, i)
            time.sleep(10.3)
            text = requests.get(url, headers=headers).text
            parse(text)


if __name__ == '__main__':
    main()
