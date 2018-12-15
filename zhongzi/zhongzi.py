import json
import re
import time

import requests
from lxml import etree

from task import insertTB, logger, selectTB

headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
}


def start_request(page):

    start_url = 'http://202.127.42.47:6010/SDSite/Home/GetVarietyAuthorizeMainSearch?rows=100&page='
    url = start_url + str(page)
    varietyinfo = {}
    response = requests.get(url, headers=headers).json()['rows']

    # 检验数据库是否有数据
    sql = 'select distinct judgementno from t_crawl_seed;'
    data = selectTB(sql)
    data = {x[0] for x in data}

    for row in response:
        # 编号
        judgementno = row['JudgementNo']
        if judgementno in data:
            logger.info('该数据已经存在数据库，' + str(judgementno))
            continue
        # 作物名称
        cropID = row['CropID']
        # 品种名称
        varietyname = row['VarietyName']
        # 地区id
        judgementregionID = row['JudgementRegionID']
        # 年份
        judgementyear = row['JudgementYear']
        # 申请单位
        applycompany = row['ApplyCompany']
        # 是否转基因
        istransgenosis = row['IsTransgenosis']
        # 品种是否有许可证
        varietyhaslincense = row['VarietyHasLincense']
        # 公司是否有许可证
        companyhaslincense = row['CompanyHasLincense']
        # 是否有品种权
        hasgrant = row['HasGrant']
        # 是否有品种推广
        haspromotion = row['HasPromotion']

        # 写入字典，存入数据库
        varietyinfo['judgementno'] = judgementno
        varietyinfo['cropID'] = cropID
        varietyinfo['varietyname'] = varietyname
        varietyinfo['judgementregionID'] = judgementregionID
        varietyinfo['judgementyear'] = judgementyear
        varietyinfo['applycompany'] = applycompany
        varietyinfo['istransgenosis'] = istransgenosis
        varietyinfo['varietyhaslincense'] = varietyhaslincense
        varietyinfo['companyhaslincense'] = companyhaslincense
        varietyinfo['hasgrant'] = hasgrant
        varietyinfo['haspromotion'] = haspromotion

        # 品种推广历史
        if haspromotion == '1':
            time.sleep(0.4)
            promotion = requests.post(
                'http://202.127.42.47:6010/SDSite/Home/GetPromotionInfo?VarietyName=' +
                str(varietyname),
                headers=headers, data={'VarietyName': varietyname}).json()
            varietyinfo['promotion'] = promotion
        else:
            varietyinfo['promotion'] = ''

        # 审批号信息
        time.sleep(0.5)
        json = requests.post(
            'http://202.127.42.47:6010/SDSite/Home/GetAnnouncementInfo',
            headers=headers, data={'judgementNo': judgementno}).json()
        varietyinfo = judgementnoinfo(json, varietyinfo)

        # 品种权信息
        if hasgrant == '1':
            time.sleep(0.5)
            jsons = requests.post(
                'http://202.127.42.47:6010/SDSite/Home/GetGrantInfo', headers=headers,
                data={'varietyName': varietyname, 'type': '2'}).json()
            grant(jsons, varietyinfo)
        else:
            varietyinfo['grant'] = ''
        # 写入数据库
        to_db(varietyinfo)

        # # 品种许可证
        # if varietyhaslincense == '1':
        #     time.sleep(0.5)
        #     jsons = requests.post(
        #         'http://202.127.42.47:6010/SDSite/Home/GetLicenceInfoByVarietyName',
        #         headers=headers, data={'varietyName': varietyname}).json()
        #     variety(str(jsons))


def to_db(varietyinfo):
    col_name = "judgementno,cropID,varietyname,judgementregionID,judgementyear,applycompany,istransgenosis,varietyhaslincense," \
        "companyhaslincense,hasgrant,haspromotion,varietysource,varietycharacter,outputexpression,plantrequirment," \
        "judgementsuggestion,grants,promotion"
    valuses = "'%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s'" % \
        (varietyinfo['judgementno'], varietyinfo['cropID'],
         varietyinfo['varietyname'], varietyinfo['judgementregionID'],
         varietyinfo['judgementyear'], varietyinfo['applycompany'],
         varietyinfo['istransgenosis'], varietyinfo['varietyhaslincense'],
         varietyinfo['companyhaslincense'], varietyinfo['hasgrant'],
         varietyinfo['haspromotion'], varietyinfo['varietysource'],
         varietyinfo['varietycharacter'], varietyinfo['outputexpression'],
         varietyinfo['plantrequirment'], varietyinfo['judgementsuggestion'],
         varietyinfo['grant'], varietyinfo['promotion'])
    sql = "insert into t_crawl_seed(%s) values(%s);" % (
        col_name, valuses)
    try:
        insertTB(sql)
    except Exception as e:
        print('写入数据库失败', e)
        logger.warning(e)


# 审批号信息
def judgementnoinfo(jsons, varietyinfo):
    try:
        # 将字符串转化成json
        jsons = json.loads(jsons)[0]
        # 品种来源
        varietysource = jsons['VarietySource']
        # 品种特征
        varietycharacter = jsons['VarietyCharacter']
        # 产量表现
        outputexpression = jsons['OutputExpression']
        # 栽培要求
        plantrequirment = jsons['PlantRequirment']
        # 审定意见
        judgementsuggestion = jsons['JudgementSuggestion']

        varietyinfo['varietysource'] = varietysource
        varietyinfo['varietycharacter'] = varietycharacter
        varietyinfo['outputexpression'] = outputexpression
        varietyinfo['plantrequirment'] = plantrequirment
        varietyinfo['judgementsuggestion'] = judgementsuggestion
        return varietyinfo
    except Exception as e:
        print(e)
        logger.warning(e)
        varietyinfo['varietysource'] = ''
        varietyinfo['varietycharacter'] = ''
        varietyinfo['outputexpression'] = ''
        varietyinfo['plantrequirment'] = ''
        varietyinfo['judgementsuggestion'] = ''
        return varietyinfo


# 品种权
def grant(jsons, varietyinfo):
    grant = jsons.replace(' ', '')
    varietyinfo['grant'] = grant


# 品种许可证信息
def variety(jsons):
    jsons = eval(jsons)
    for i in jsons:
        licence_info = {}
        # 许可证号
        licence_no = i['LicenceNo']
        # 公司名称
        apply_company_name = i['ApplyCompanyName']
        # 经营范围
        production_manage_crops = i['ProductionManageCrops']
        # 发证机关
        issuing_uthority_caption = i['IssuingAuthorityCaption']
        # 发证日期
        publish_date = i['PublishDate']
        # 有效日期
        expire_date = i['ExpireDate']

        # 主证
        try:
            main_how = i['MainShow']
            # 主证id
            main_id = main_how.split('id=')[-1]
            time.sleep(0.3)
            res = requests.get(
                'http://202.127.42.178:4000/SeedSearch/SeedSolution/Business/TempLicenseSelect.ashx',
                data={'Type': 'SLImpLicence', 'LicenceID': main_id}, headers=headers).json()
            main_info = re.findall(
                "left: 48.5%;'\s?>(.*?)</span>", res['ResultData'])
        except AttributeError as e:
            logger.warning(e)
            continue

        # 副证
        try:
            deputy_show = i['DeputyShow']
            # 副证id
            deputy_id = deputy_show.split('id=')[-1]
            deputy_url = 'http://202.127.42.47:8016/TwoLicenceManage/MainLicence/TwoLincenceSubWordBigData.aspx?showall=1&id='
            url = deputy_url+deputy_id
            time.sleep(0.3)
            res = requests.get(url, headers=headers, data={
                            'showall': '1', 'id': deputy_id})
        except AttributeError as e:
            logger.warning(e)
            continue
            
        res_xpath = etree.HTML(res.text)
        text = res_xpath.xpath('/html/body/div[2]/div/div//text()')
        # 副证信息
        deputy_info = []
        for i in text:
            i = i.replace(' ', '').replace('\r', '').replace('\n', '')
            if i != '':
                deputy_info.append(i)

        # 写入数据库
        licence_info['licence_no'] = licence_no
        licence_info['apply_company_name'] = apply_company_name
        licence_info['production_manage_crops'] = production_manage_crops
        licence_info['issuing_uthority_caption'] = issuing_uthority_caption
        licence_info['publish_date'] = publish_date
        licence_info['expire_date'] = expire_date
        licence_info['main_info'] = main_info
        licence_info['deputy_info'] = deputy_info

        col_name = "licence_no,apply_company_name,production_manage_crops,issuing_uthority_caption,publish_date,expire_date,main_info,deputy_info"
        valuses = "'%s','%s','%s','%s','%s','%s','%s','%s'" % \
            (licence_info['licence_no'], licence_info['apply_company_name'],
                licence_info['production_manage_crops'], licence_info['issuing_uthority_caption'],
                licence_info['publish_date'], licence_info['expire_date'],
                str(licence_info['main_info']).replace("'", "''"), str(licence_info['deputy_info']).replace("'", "''"))
        sql = "insert into t_crawl_company_licence(%s) values(%s);" % (
            col_name, valuses)
        try:
            insertTB(sql)
        except Exception as e:
            print('写入数据库失败', e)
            logger.warning(e)


def main():
    for i in range(180, 200):
        time.sleep(0.3)
        logger.info('开始爬取{}页信息'.format(i))
        start_request(i)
        logger.info('已经爬取{}页信息'.format(i))


if __name__ == '__main__':
    main()
