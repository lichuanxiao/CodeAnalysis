# -*- encoding: utf-8 -*-
"""
配置文件
"""

import os
from datetime import timedelta
from os.path import join
from settings.edition import *


# ========================
# 版本号声明
# ========================
VERSION = 20211231.1


#========================
# 日志级别
#========================
DEBUG = False


#========================
# 操作系统与机器标签
#========================
# 操作系统对应的名称
PLATFORMS = {
    'linux2': 'linux',
    'linux': 'linux',
    'win32': 'windows',
    'darwin': 'mac'
    }
# 操作系统对应的机器标签
OS_TAG_MAP = {
    'linux2': 'Codedog_Linux',
    'linux': 'Codedog_Linux',
    'win32': 'Codedog_Windows',
    'darwin': 'Codedog_Mac'
}

#========================
# 目录与文件路径
#========================
# puppy根目录
BASE_DIR = os.path.abspath(os.curdir)
# 数据目录
DATA_DIR = join(BASE_DIR, "data")
# 源码存放目录
SOURCE_DIR = join(DATA_DIR, "sourcedirs")
# 任务工作目录名
WORK_DIR = "workdir"
# p2p传输的临时目录
TEMP_PTP_DIR = join(DATA_DIR, 'temp_ptp')
# 本地项目资源与工具缓存配置文本
CACHE_FILE = join(DATA_DIR, "cache.json")
# PUPPY所需的第三方工具目录
LIB_BASE_DIR = join(BASE_DIR, 'lib')


#========================
# 任务执行设置
#========================
# 任务目录
TASK_DIR = join(DATA_DIR, "taskdirs")
# 任务超时秒数,设置为10天,以最大限度满足所有任务
TASK_EXPIRED = timedelta(hours=240)
# 本地私有进程任务执行超时时间（包括远端进程+本地私有进程总和）,设置为10小时,以秒为单位
LOCAL_TASK_EXPIRED = 10 * 60 * 60
# 轮询结果的时间间隔,以秒为单位
POLLING_INTERVAL = 15
# 扫描结果轮询的超时时间(5小时)
POLLING_TMEOUT = 5 * 60 * 60
# 扫描结束后等待数据入库的时间(20s)
RESULT_INTO_DB_TIME = 20


#========================
# 扫描工具拉取和更新设置
#========================
# 默认从Git拉取工具；如果使用本地工具，可以在config.ini中配置该值为True，将不自动拉取内置工具和配置文件
USE_LOCAL_TOOL = False
# 默认的工具目录，即puppy根目录下的data/tools目录
DEFAULT_TOOL_BASE_DIR = join(BASE_DIR, "data/tools")
# 扫描工具目录
TOOL_BASE_DIR = join(DATA_DIR, "tools")
# 扫描工具配置文件地址，需要在config.ini中配置
TOOL_CONFIG_URL = ""

# ========================
# 配置文件名
# ========================
CONFIG_NAME = "codedog.ini"

# ========================
# 初始化工具拉取账号密码,需要在config.ini中配置
# ========================
TOOL_LOAD_ACCOUNT = {
    "USERNAME": None,
    "PASSWORD": None
}

# ========================
# scm密码解密秘钥,需要在config.ini中配置
# ========================
PASSWORD_KEY = ""

# ========================
# 文件服务器设置,需要在config.ini中配置
# ========================
FILE_SERVER = {
    'URL': '',
    'TOKEN': ''
    }

# ========================
# SERVER地址, 需要在config.ini中配置
# ========================
SERVER_URL = {
    "URL": ""
}