"""
爬虫配置文件 - 目标网站、UA、请求配置
"""
import os
from fake_useragent import UserAgent

# 项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "travel_data")
ATTRACTIONS_DIR = os.path.join(DATA_DIR, "attractions")
GUIDES_DIR = os.path.join(DATA_DIR, "guides")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

# 确保目录存在
for d in [ATTRACTIONS_DIR, GUIDES_DIR, CACHE_DIR]:
    os.makedirs(d, exist_ok=True)

# UA 池
ua = UserAgent()

# 目标网站列表
TARGET_SITES = {
    "mafengwo": {
        "name": "马蜂窝",
        "base_url": "https://www.mafengwo.cn",
        "search_url": "https://www.mafengwo.cn/search/q.php?q={keyword}",
        "attraction_url": "https://www.mafengwo.cn/poi/{poi_id}.html",
        "guide_url": "https://www.mafengwo.cn/gonglve/",
    },
    "ctrip": {
        "name": "携程",
        "base_url": "https://you.ctrip.com",
        "search_url": "https://you.ctrip.com/searchsite/?query={keyword}",
        "attraction_url": "https://you.ctrip.com/sight/{city_pinyin}/{sight_id}.html",
    },
    "qyer": {
        "name": "穷游",
        "base_url": "https://www.qyer.com",
        "search_url": "https://www.qyer.com/search?q={keyword}",
    },
    "qunar": {
        "name": "去哪儿",
        "base_url": "https://travel.qunar.com",
        "search_url": "https://travel.qunar.com/search/place/{keyword}",
    },
    "dianping": {
        "name": "大众点评",
        "base_url": "https://www.dianping.com",
        "search_url": "https://www.dianping.com/search/keyword/0/0_{keyword}",
    },
}

# Crawl4AI 配置
CRAWL4AI_CONFIG = {
    "headless": True,
    "verbose": False,
    "timeout": 30000,  # 30秒超时
    "wait_until": "networkidle",
    "bypass_cache": False,
    "magic_mode": True,        # 自动处理反爬
    "simulate_user": True,     # 模拟真实用户
    "override_navigator": True, # 覆盖navigator属性
}

# 缓存配置
CACHE_TTL = {
    "attraction": 86400 * 7,   # 景点数据缓存7天
    "guide": 86400 * 3,        # 攻略数据缓存3天
    "weather": 3600,           # 天气1小时
    "place": 86400,            # 地点1天
}

# 请求频率控制 (请求/秒)
RATE_LIMIT = {
    "mafengwo": 1.0,
    "ctrip": 1.5,
    "qyer": 2.0,
    "qunar": 1.5,
    "dianping": 1.0,
}

# 各城市拼音映射（用于携程URL）
CITY_PINYIN = {
    "北京": "beijing",
    "上海": "shanghai",
    "广州": "guangzhou",
    "深圳": "shenzhen",
    "成都": "chengdu",
    "杭州": "hangzhou",
    "南京": "nanjing",
    "西安": "xian",
    "重庆": "chongqing",
    "厦门": "xiamen",
    "昆明": "kunming",
    "大理": "dali",
    "丽江": "lijiang",
    "三亚": "sanya",
    "青岛": "qingdao",
    "大连": "dalian",
    "桂林": "guilin",
    "张家界": "zhangjiajie",
    "武汉": "wuhan",
    "长沙": "changsha",
    "苏州": "suzhou",
    "天津": "tianjin",
    "贵阳": "guiyang",
    "哈尔滨": "haerbin",
}

def get_headers():
    """生成随机请求头"""
    return {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
