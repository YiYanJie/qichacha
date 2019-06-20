#!/usr/bin/python
# -*- coding:utf-8 -*-
# author: oyj
# CreateTime: 2019/5/22
# software-version: python 3.7
import json
import urllib

import os

import pymongo
import pytesseract
from PIL import Image
from collections import defaultdict
import requests
import time
from io import BytesIO
from PIL import Image
import os
import numpy as np
# 获取验证码的网址
from click._compat import raw_input
from requests import RequestException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from time import sleep, time
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
import tesserocr
import re
from urllib.request import urlretrieve
from PIL import Image, ImageEnhance
from bs4 import BeautifulSoup
from pyquery import PyQuery as pq

class GetHospitalInfomation(object):
    """
    爬取企查查下的医院的信息
    """
    # 初始化
    def __init__(self):
        """
         初始化爬虫执行代理，使用chrome访问
         """
        # 定义为全局变量，方便其他模块使用
        global base_url, true_url, browser, wait, collection
        # 登录网址
        base_url = "https://www.qichacha.com/user_qqlogin?back=&replace=1"
        # 官网网址
        true_url = "https://www.qichacha.com"
        # 实例化一个chrome浏览器
        # chrome_options = Options()
        # 无头浏览
        # chrome_options.add_argument('--headless')
        # browser = webdriver.Chrome(r'C:\Users\YIYANJIE\AppData\Local\Programs\Python\Python37-32\Scripts\chromedriver',chrome_options=chrome_options)
        browser = webdriver.Chrome()
        # 设置等待超时
        wait = WebDriverWait(browser, 20)
        # 连接数据库
        client = pymongo.MongoClient(host='localhost', port=27017)
        db = client.test
        collection = db['qichacha']

    # 访问普通html或js加载页面
    def get_page(self, url):
        try:
            # 打开登录页面
            browser.get(url)
            # 将页面放到最大
            browser.maximize_window()
            return browser.page_source
        except RequestException:
            return None

    # 访问ifram页面
    def get_ifram_page(self,url):
        try:
            # 打开登录页面
            browser.get(url)
            # 将页面放到最大
            browser.maximize_window()
            iframe = browser.find_elements_by_tag_name('iframe')[0]
            browser.switch_to.frame(iframe)  # 最重要的一步
            return browser.page_source
        except RequestException:
            return None

    # 登录
    def login(self):
        self.get_ifram_page(base_url)
        # 点击使用此QQ账号登录
        loginLink = WebDriverWait(browser, 30).until(lambda x: x.find_element_by_xpath('//div[@id="qlogin_list"]/a'))
        loginLink.click()
        sleep(5)

    # 获取主要内容
    def parser_one_page(self):
        try:
            for i in range(1, 6):
                if i == 1:
                    html = self.get_page(true_url + '/search/?key=医院#p:' + str(i))
                else:
                    browser.find_element_by_class_name('pagination').find_element_by_tag_name('input').send_keys(i)
                    browser.find_element_by_id('jumpPage').click()
                    html = browser.page_source
                # 打开登录页面
                doc = pq(html)
                items = doc('#search-result tr').items()
                for item in items:
                    company_name = item.find('td').eq(2).find('.ma_h1').text()  # 公司名称
                    company_owner_name = self.selectdb()
                    if company_name in company_owner_name:
                        print("公司已存在，跳过该公司...")
                        continue
                    company_link = "https:"+item.find('td').eq(2).find('.ma_h1').attr('href')  # 公司详细链接
                    company_status = item.find('.statustd .nstatus').text()  # 公司状态
                    if item.find('.search-tags span') == None:
                        # 股票类型
                        stock_type = '暂无'
                        # 股票代码
                        stock_code = '暂无'
                    elif item.find('.search-tags span .m-l-xs') == None:
                        # 股票类型
                        stock_type = item.find('.search-tags span').text()
                        # 股票代码
                        stock_code = '暂无'
                    else:
                        # 股票类型
                        stock_type = item.find('.search-tags span').text().split('|', 1)[0]
                        # 股票代码
                        stock_code = item.find('.search-tags .m-l-xs').text()
                    # 法定代表人
                    company_represent = item.find('.m-t-xs').eq(0).find('a').text()
                    # 注册资本
                    registered_capital = item.find('.m-t-xs').eq(0).find('span').eq(0).text().replace("注册资本：", "")
                    # 成立日期
                    register_date = item.find('.m-t-xs').eq(0).find('span').eq(1).text().replace("成立日期：", "")
                    # 电话
                    phone = item.find('.m-t-xs').eq(1).find('span').text().replace("电话：", "")
                    # 邮箱
                    item.find('.m-t-xs').eq(1).find('span').remove()
                    item.find('.m-t-xs').eq(1).find('a').remove()
                    mailbox = item.find('.m-t-xs').eq(1).text().replace("邮箱：", "")
                    # 地址
                    address = item.find('.m-t-xs').eq(2).text()
                    print(company_name)
                    print(company_link)
                    print(company_status)
                    print(stock_type)
                    print(stock_code)
                    print(company_represent)
                    print(registered_capital)
                    print(register_date)
                    print(mailbox)
                    print(phone)
                    print(address)
                    yield {
                        'company_name': company_name,
                        'company_link': company_link,
                        'company_status': company_status,
                        'stock_type': stock_type,
                        'stock_code': stock_code,
                        'company_represent': company_represent,
                        'registered_capital': registered_capital,
                        'register_date': register_date,
                        'mailbox': mailbox,
                        'phone': phone,
                        'address': address
                    }
        except IndexError as e:
            self.parser_one_page()

    # 写入文件
    def write_to_file(self, c):  # 写入文本
        with open('qichacha.txt', 'a', encoding='utf-8') as f:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')

    # 插入数据库
    def insertdb(self, item):
        collection.insert_many([item])  # 插入数据

    # 查询数据库已拥有的公司
    def selectdb(self):
        company_list = collection.distinct("company_name")
        return company_list

    # 主程序
    def main(self):
        # 登录
        self.login()
        for item in self.parser_one_page():
            self.write_to_file(item)
            self.insertdb(item)

# 程序入口
if __name__ == '__main__':
    qichacha2 = GetHospitalInfomation()
    qichacha2.main()