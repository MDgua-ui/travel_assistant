"""
旅游数据爬虫模块 - 基于 Crawl4AI 的多源旅游数据采集系统

支持的网站:
    - 马蜂窝 (mafengwo.cn): 攻略、景点、游记
    - 携程 (ctrip.com): 景点排名、门票、评价
    - 更多网站持续接入中...

核心类:
    - TravelDataEnricher: 数据增强器(推荐入口)
    - MafengwoCrawler: 马蜂窝爬虫
    - CtripCrawler: 携程爬虫
    - TravelDataStore: 数据存储与检索
    - BaseCrawler: 基础爬虫(基于Crawl4AI)
"""

from .base_crawler import BaseCrawler
from .config import TARGET_SITES, CRAWL4AI_CONFIG, CITY_PINYIN
from .mafengwo_crawler import MafengwoCrawler
from .ctrip_crawler import CtripCrawler
from .travel_data_store import TravelDataStore, get_data_store
from .data_enricher import TravelDataEnricher, run_async_enrich
from .real_data_provider import RealDataProvider, get_real_data_provider

__all__ = [
    "BaseCrawler",
    "MafengwoCrawler",
    "CtripCrawler",
    "TravelDataStore",
    "TravelDataEnricher",
    "RealDataProvider",
    "get_data_store",
    "get_real_data_provider",
    "run_async_enrich",
    "TARGET_SITES",
    "CRAWL4AI_CONFIG",
    "CITY_PINYIN",
]

__version__ = "1.0.0"
