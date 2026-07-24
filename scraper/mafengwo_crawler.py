"""
马蜂窝爬虫 - 爬取景点信息、游记攻略、目的地数据
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import List, Dict, Optional

from bs4 import BeautifulSoup

from .base_crawler import BaseCrawler
from .config import ATTRACTIONS_DIR, GUIDES_DIR, CACHE_TTL, get_headers

logger = logging.getLogger(__name__)


class MafengwoCrawler(BaseCrawler):
    """马蜂窝旅游网爬虫"""

    def __init__(self):
        super().__init__("mafengwo", rate_limit=1.0)

    async def search_destination(self, keyword: str) -> Dict:
        """
        搜索目的地信息

        Args:
            keyword: 目的地名称(如"大理"、"成都")

        Returns:
            目的地基础信息
        """
        url = f"https://www.mafengwo.cn/search/q.php?q={keyword}"
        result = await self.fetch_page(
            url,
            cache_type="destination",
            ttl=CACHE_TTL["guide"],
            wait_for=".search-list",
        )

        if not result.get("success"):
            return {"keyword": keyword, "source": "mafengwo", "error": "搜索失败"}

        # 解析搜索结果
        info = self._parse_search_result(result["cleaned_html"], keyword)
        info["keyword"] = keyword
        info["source"] = "mafengwo"
        info["crawled_at"] = datetime.now().isoformat()

        return info

    def _parse_search_result(self, html: str, keyword: str) -> Dict:
        """解析马蜂窝搜索结果"""
        soup = BeautifulSoup(html, "lxml")
        info = {"pois": [], "guides": []}

        # 提取景点信息
        for item in soup.select(".search-list .list-item")[:10]:
            try:
                name_elem = item.select_one(".title")
                desc_elem = item.select_one(".intro")
                link_elem = item.select_one("a[href]")

                if name_elem:
                    poi = {
                        "name": name_elem.get_text(strip=True),
                        "description": desc_elem.get_text(strip=True) if desc_elem else "",
                        "link": link_elem.get("href", "") if link_elem else "",
                    }
                    if poi["name"] and poi["name"] != keyword:
                        info["pois"].append(poi)
            except Exception:
                continue

        return info

    async def get_attraction_detail(self, url: str) -> Dict:
        """
        获取景点详情页

        Args:
            url: 景点页面URL

        Returns:
            景点详细信息
        """
        result = await self.fetch_page(
            url,
            cache_type="attraction",
            ttl=CACHE_TTL["attraction"],
            extract_content=True,
        )

        if not result.get("success"):
            return {"error": "获取失败", "url": url}

        # 用 BeautifulSoup 做结构化提取
        soup = BeautifulSoup(result["cleaned_html"], "lxml")

        detail = {
            "name": self._extract_attraction_name(soup),
            "rating": self._extract_rating(soup),
            "price": self._extract_price(soup),
            "open_time": self._extract_open_time(soup),
            "address": self._extract_address(soup),
            "description": self._extract_description(result["content"]),
            "tips": self._extract_tips(result["content"]),
            "url": url,
            "source": "mafengwo",
            "crawled_at": datetime.now().isoformat(),
        }

        return detail

    @staticmethod
    def _extract_attraction_name(soup: BeautifulSoup) -> str:
        for selector in ["h1.title", ".poi-title", "h1"]:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        return ""

    @staticmethod
    def _extract_rating(soup: BeautifulSoup) -> str:
        for selector in [".score", ".rating-score", ".star-level"]:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        return ""

    @staticmethod
    def _extract_price(soup: BeautifulSoup) -> str:
        for selector in [".price", ".ticket-price", ".admission"]:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        # 从文本中提取价格
        price_patterns = [
            r'门票[：:]\s*[¥￥]?\s*(\d+[\d,.]*)',
            r'价格[：:]\s*[¥￥]?\s*(\d+[\d,.]*)',
        ]
        text = soup.get_text()
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                return f"¥{match.group(1)}"
        return ""

    @staticmethod
    def _extract_open_time(soup: BeautifulSoup) -> str:
        for selector in [".open-time", ".opening-hours", ".business-hours"]:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        # 从文本提取
        text = soup.get_text()
        patterns = [
            r'开放时间[：:]\s*(.+?)(?:\n|$)',
            r'营业时间[：:]\s*(.+?)(?:\n|$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_address(soup: BeautifulSoup) -> str:
        for selector in [".address", ".location", ".poi-address"]:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        return ""

    @staticmethod
    def _extract_description(content: str) -> str:
        """从 Markdown 内容中提取景点描述"""
        # 提取前几段有意义的内容
        lines = content.split("\n")
        desc_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("!") and len(line) > 20:
                desc_lines.append(line)
            if len(desc_lines) >= 5:
                break
        return "\n".join(desc_lines)

    @staticmethod
    def _extract_tips(content: str) -> str:
        """提取旅游小贴士"""
        keywords = ["贴士", "注意", "提示", "建议", "攻略", "TIPS"]
        relevant_lines = []
        for line in content.split("\n"):
            for kw in keywords:
                if kw in line:
                    relevant_lines.append(line.strip())
                    break
        return "\n".join(relevant_lines[:10])

    async def get_travel_guide(self, city: str) -> Dict:
        """
        获取城市攻略

        Args:
            city: 城市名称

        Returns:
            攻略数据
        """
        url = f"https://www.mafengwo.cn/gonglve/zt.php?q={city}"
        result = await self.fetch_page(
            url,
            cache_type="guide",
            ttl=CACHE_TTL["guide"],
            extract_content=True,
        )

        if not result.get("success"):
            return {"city": city, "source": "mafengwo", "error": "获取失败"}

        # 用 LLM 擅长的内容提取关键词区域
        guide_data = {
            "city": city,
            "source": "mafengwo",
            "url": url,
            "content_sections": self._split_guide_sections(result["content"]),
            "recommended_attractions": self._extract_attraction_list(result["content"]),
            "food_recommendations": self._extract_food_list(result["content"]),
            "crawled_at": datetime.now().isoformat(),
        }

        return guide_data

    @staticmethod
    def _split_guide_sections(content: str) -> Dict[str, str]:
        """将攻略按标题分段"""
        sections = {}
        current_title = "概述"
        current_content = []

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("##") or line.startswith("###"):
                if current_content:
                    sections[current_title] = "\n".join(current_content)
                current_title = line.lstrip("#").strip()
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            sections[current_title] = "\n".join(current_content)

        return sections

    @staticmethod
    def _extract_attraction_list(content: str) -> List[Dict]:
        """从攻略中提取景点推荐"""
        attractions = []
        # 匹配列表项或加粗的景点名
        patterns = [
            r'[\-\*\d+\.]\s*\*\*(.+?)\*\*[：:]?(.+?)(?:\n|$)',
            r'[\-\*\d+\.]\s*(.{2,20})\s*[—\-：:]\s*(.+?)(?:\n|$)',
            r'\*\*(.{2,20})\*\*[—\-：:]?\s*(.+?)(?:\n|$)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for name, desc in matches:
                name = name.strip()
                desc = desc.strip()
                if len(name) >= 2 and len(name) <= 30:
                    attractions.append({"name": name, "description": desc})
            if len(attractions) >= 5:
                break

        return attractions[:10]

    @staticmethod
    def _extract_food_list(content: str) -> List[Dict]:
        """从攻略中提取美食推荐"""
        foods = []
        food_keywords = ["美食", "餐厅", "小吃", "推荐", "必吃", "特色"]

        for line in content.split("\n"):
            for kw in food_keywords:
                if kw in line and len(line) > 10:
                    foods.append({"name": line.strip()[:80], "keyword": kw})
                    break
                if len(foods) >= 10:
                    break

        return foods[:10]
