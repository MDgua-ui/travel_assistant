"""
携程爬虫 - 爬取景点详情、用户评价、门票价格
"""
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional

from bs4 import BeautifulSoup

from .base_crawler import BaseCrawler
from .config import CITY_PINYIN, CACHE_TTL

logger = logging.getLogger(__name__)


class CtripCrawler(BaseCrawler):
    """携程旅行网爬虫"""

    def __init__(self):
        super().__init__("ctrip", rate_limit=1.5)

    async def search_attractions(self, city: str, keyword: str = "景点") -> Dict:
        """
        搜索城市景点

        Args:
            city: 城市名称
            keyword: 搜索关键词

        Returns:
            景点列表
        """
        city_pinyin = CITY_PINYIN.get(city, city.lower())
        url = f"https://you.ctrip.com/searchsite/?query={city}+{keyword}"

        result = await self.fetch_page(
            url,
            cache_type="attraction_search",
            ttl=CACHE_TTL["place"],
            wait_for=".scenic-list, .list_wide",
        )

        if not result.get("success"):
            logger.warning(f"携程搜索失败，尝试备用URL")
            # 备用: 直接访问城市页面
            url = f"https://you.ctrip.com/sight/{city_pinyin}12.html"
            result = await self.fetch_page(
                url,
                cache_type="attraction_list",
                ttl=CACHE_TTL["place"],
            )

        attractions = self._parse_attraction_list(result.get("cleaned_html", ""), result.get("content", ""))
        return {
            "city": city,
            "attractions": attractions,
            "source": "ctrip",
            "crawled_at": datetime.now().isoformat(),
        }

    def _parse_attraction_list(self, html: str, content: str) -> List[Dict]:
        """解析景点列表"""
        attractions = []
        soup = BeautifulSoup(html, "lxml")

        # 携程景点列表选择器
        for item in soup.select(".scenic-item, .list_wide .list-item, .sight-item")[:15]:
            try:
                name_elem = item.select_one(".name, .title, h3 a")
                score_elem = item.select_one(".score, .rating")
                price_elem = item.select_one(".price, .ticket")
                img_elem = item.select_one("img")
                link_elem = item.select_one("a[href]")

                attraction = {
                    "name": name_elem.get_text(strip=True) if name_elem else "",
                    "rating": score_elem.get_text(strip=True) if score_elem else "",
                    "price": price_elem.get_text(strip=True) if price_elem else "",
                    "image": img_elem.get("src") or img_elem.get("data-src", "") if img_elem else "",
                    "link": link_elem.get("href", "") if link_elem else "",
                }
                if attraction["name"] and len(attraction["name"]) >= 2:
                    attractions.append(attraction)
            except Exception:
                continue

        # 备用：从 Markdown 内容中提取
        if not attractions and content:
            attractions = self._extract_from_markdown(content)

        return attractions[:15]

    @staticmethod
    def _extract_from_markdown(content: str) -> List[Dict]:
        """从 Markdown 内容中提取景点信息"""
        attractions = []
        lines = content.split("\n")
        for line in lines:
            # 匹配景点名称模式
            match = re.match(r'[\-\*\d+\.]\s*\*?\*?(.{2,25})\*?\*?\s*[—\-：:]\s*(.+)', line)
            if match:
                attractions.append({
                    "name": match.group(1).strip(),
                    "description": match.group(2).strip()[:100],
                })
        return attractions[:15]

    async def get_attraction_detail(self, url: str) -> Dict:
        """
        获取景点详情

        Args:
            url: 携程景点详情页URL

        Returns:
            景点详细信息
        """
        result = await self.fetch_page(
            url,
            cache_type="attraction_detail",
            ttl=CACHE_TTL["attraction"],
            extract_content=True,
            js_code="""
                // 展开完整描述
                document.querySelectorAll('.show-more, .view-more').forEach(el => el.click());
            """,
        )

        if not result.get("success"):
            return {"error": "获取失败", "url": url}

        soup = BeautifulSoup(result.get("cleaned_html", ""), "lxml")

        detail = {
            "name": self._get_text(soup, "h1.name, .sight-name"),
            "english_name": self._get_text(soup, ".english-name"),
            "rating": self._get_text(soup, ".score, .star"),
            "price": self._extract_price_info(soup, result.get("content", "")),
            "open_time": self._extract_open_info(soup, result.get("content", "")),
            "address": self._get_text(soup, ".address, .location"),
            "transport": self._get_text(soup, ".traffic, .transport"),
            "description": self._extract_long_text(result.get("content", ""), "景点介绍", "开放时间"),
            "tips": self._extract_long_text(result.get("content", ""), "贴士", "交通"),
            "url": url,
            "source": "ctrip",
            "crawled_at": datetime.now().isoformat(),
        }

        return detail

    @staticmethod
    def _get_text(soup: BeautifulSoup, selector: str) -> str:
        elem = soup.select_one(selector)
        return elem.get_text(strip=True) if elem else ""

    @staticmethod
    def _extract_price_info(soup: BeautifulSoup, content: str) -> str:
        """提取价格信息"""
        for selector in [".price-box", ".ticket-price", ".price-detail"]:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)

        patterns = [
            r'门票[：:][^。\n]{0,50}',
            r'价格[：:][^。\n]{0,50}',
            r'[¥￥]\d+[^。\n]{0,30}',
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group().strip()
        return ""

    @staticmethod
    def _extract_open_info(soup: BeautifulSoup, content: str) -> str:
        """提取开放时间"""
        for selector in [".open-time", ".business-hours"]:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)

        patterns = [
            r'开放时间[：:][^。\n]{0,80}',
            r'营业时间[：:][^。\n]{0,80}',
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group().strip()
        return ""

    @staticmethod
    def _extract_long_text(content: str, start_kw: str, end_kw: str = "") -> str:
        """提取两个关键词之间的长文本"""
        start_idx = content.find(start_kw)
        if start_idx == -1:
            return ""
        text = content[start_idx:]
        if end_kw:
            end_idx = text.find(end_kw, len(start_kw))
            if end_idx != -1:
                text = text[:end_idx]
        return text[:500].strip()

    async def get_city_hot_attractions(self, city: str) -> Dict:
        """
        获取城市热门景点排名

        Args:
            city: 城市名称

        Returns:
            热门景点列表及排名
        """
        city_pinyin = CITY_PINYIN.get(city, city.lower())
        url = f"https://you.ctrip.com/sight/{city_pinyin}12.html"

        result = await self.fetch_page(
            url,
            cache_type="hot_attractions",
            ttl=CACHE_TTL["place"],
            extract_content=True,
        )

        soup = BeautifulSoup(result.get("cleaned_html", ""), "lxml")
        content = result.get("content", "")

        hot_list = []
        for item in soup.select(".scenic-rank-item, .hot-sight-item, .rank-item")[:20]:
            try:
                name_elem = item.select_one(".name, .title, h3")
                rank_elem = item.select_one(".rank-num, .ranking")
                score_elem = item.select_one(".score, .rating")
                comment_count_elem = item.select_one(".comment-count, .reviews")

                hot_list.append({
                    "name": name_elem.get_text(strip=True) if name_elem else "",
                    "rank": rank_elem.get_text(strip=True) if rank_elem else "",
                    "rating": score_elem.get_text(strip=True) if score_elem else "",
                    "comment_count": comment_count_elem.get_text(strip=True) if comment_count_elem else "",
                })
            except Exception:
                continue

        # 从内容中补充
        if not hot_list and content:
            hot_list = self._extract_ranked_from_content(content)

        return {
            "city": city,
            "hot_attractions": hot_list[:20],
            "source": "ctrip",
            "crawled_at": datetime.now().isoformat(),
        }

    @staticmethod
    def _extract_ranked_from_content(content: str) -> List[Dict]:
        """从内容中提取排名列表"""
        items = []
        # 匹配 "第N名" 或 "TOP N" 或 编号列表
        for line in content.split("\n"):
            match = re.match(r'.*?(?:第(\d+)[名位]|TOP\s*(\d+)|(\d+)[\.\)、]\s*(.{2,30}))', line, re.IGNORECASE)
            if match:
                rank = match.group(1) or match.group(2) or match.group(3) or ""
                name = match.group(4) or line[:50]
                items.append({"name": name.strip(), "rank": rank})
        return items[:20]
