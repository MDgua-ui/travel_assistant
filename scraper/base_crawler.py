"""
基于 Crawl4AI 的基础爬虫类
提供统一的爬取接口，支持 JS 渲染、反爬处理、结果提取
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from .config import (
    CRAWL4AI_CONFIG, CACHE_DIR, CACHE_TTL, get_headers
)

logger = logging.getLogger(__name__)


class BaseCrawler:
    """Crawl4AI 基础爬虫"""

    def __init__(self, site_name: str, rate_limit: float = 1.0):
        self.site_name = site_name
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self._crawler: Optional[AsyncWebCrawler] = None

    async def _get_crawler(self) -> AsyncWebCrawler:
        """获取或创建爬虫实例"""
        if self._crawler is None:
            self._crawler = AsyncWebCrawler(
                headless=CRAWL4AI_CONFIG["headless"],
                verbose=CRAWL4AI_CONFIG["verbose"],
            )
            await self._crawler.__aenter__()
        return self._crawler

    async def close(self):
        """关闭爬虫"""
        if self._crawler:
            try:
                await self._crawler.__aexit__(None, None, None)
            except Exception:
                pass
            self._crawler = None

    async def _rate_limit_wait(self):
        """请求频率控制"""
        elapsed = time.time() - self.last_request_time
        min_interval = 1.0 / self.rate_limit if self.rate_limit > 0 else 0
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self.last_request_time = time.time()

    def _cache_key(self, url: str, cache_type: str) -> str:
        """生成缓存文件名"""
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return os.path.join(CACHE_DIR, f"{cache_type}_{self.site_name}_{url_hash}.json")

    def _load_cache(self, cache_key: str, ttl: int) -> Optional[Dict]:
        """加载缓存数据"""
        if not os.path.exists(cache_key):
            return None
        try:
            with open(cache_key, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached_time = data.get("_cached_at", 0)
            if time.time() - cached_time < ttl:
                logger.info(f"[{self.site_name}] 📦 命中缓存: {os.path.basename(cache_key)}")
                return data
        except Exception:
            pass
        return None

    def _save_cache(self, cache_key: str, data: Dict):
        """保存缓存"""
        data["_cached_at"] = time.time()
        data["_source"] = self.site_name
        try:
            with open(cache_key, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"[{self.site_name}] 💾 已缓存: {os.path.basename(cache_key)}")
        except Exception as e:
            logger.warning(f"[{self.site_name}] 缓存保存失败: {e}")

    async def fetch_page(
        self,
        url: str,
        cache_type: str = "page",
        ttl: int = 3600,
        extract_content: bool = True,
        wait_for: Optional[str] = None,
        js_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        爬取页面

        Args:
            url: 目标URL
            cache_type: 缓存类型标识
            ttl: 缓存有效期(秒)
            extract_content: 是否提取主要内容
            wait_for: 等待某个 CSS 选择器出现
            js_code: 页面加载后执行的 JS 代码

        Returns:
            {
                "url": 原始URL,
                "title": 页面标题,
                "content": Markdown格式内容,
                "cleaned_html": 清洗后的HTML,
                "raw_html": 原始HTML,
                "links": 页面链接列表,
                "metadata": 元数据,
                "from_cache": 是否来自缓存,
            }
        """
        # 1. 检查缓存
        cache_key = self._cache_key(url, cache_type)
        if ttl > 0:
            cached = self._load_cache(cache_key, ttl)
            if cached:
                cached["from_cache"] = True
                return cached

        # 2. 频率控制
        await self._rate_limit_wait()

        # 3. 爬取页面
        crawler = await self._get_crawler()

        # 配置内容过滤
        md_generator = DefaultMarkdownGenerator(
            content_filter=PruningContentFilter() if extract_content else None,
        )

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS if not CRAWL4AI_CONFIG["bypass_cache"] else CacheMode.BYPASS,
            magic=CRAWL4AI_CONFIG["magic_mode"],
            simulate_user=CRAWL4AI_CONFIG["simulate_user"],
            override_navigator=CRAWL4AI_CONFIG["override_navigator"],
            markdown_generator=md_generator,
            wait_until=CRAWL4AI_CONFIG["wait_until"],
            page_timeout=CRAWL4AI_CONFIG["timeout"],
            js_code=js_code,
            wait_for=wait_for,
        )

        try:
            logger.info(f"[{self.site_name}] 🌐 爬取: {url[:100]}")
            result = await crawler.arun(url=url, config=config)

            if not result.success:
                logger.warning(f"[{self.site_name}] ⚠️ 爬取失败: {result.error_message}")
                return {
                    "url": url,
                    "title": "",
                    "content": "",
                    "cleaned_html": "",
                    "raw_html": "",
                    "links": [],
                    "metadata": {"error": result.error_message},
                    "from_cache": False,
                    "success": False,
                }

            # 提取链接
            links = []
            if result.links:
                for link in result.links:
                    links.append({
                        "href": link.get("href", ""),
                        "text": link.get("text", ""),
                    })

            data = {
                "url": result.url or url,
                "title": result.metadata.get("title", "") if result.metadata else "",
                "content": result.markdown or "",
                "cleaned_html": result.cleaned_html or "",
                "raw_html": result.html or "",
                "links": links,
                "metadata": {
                    "status_code": result.status_code,
                    "response_time_ms": result.response_time_ms if hasattr(result, 'response_time_ms') else None,
                },
                "from_cache": False,
                "success": True,
            }

            # 4. 保存缓存
            if ttl > 0:
                self._save_cache(cache_key, data)

            return data

        except Exception as e:
            logger.error(f"[{self.site_name}] ❌ 爬取异常: {url}, 错误: {str(e)}")
            return {
                "url": url,
                "title": "",
                "content": "",
                "cleaned_html": "",
                "raw_html": "",
                "links": [],
                "metadata": {"error": str(e)},
                "from_cache": False,
                "success": False,
            }

    async def fetch_multiple(
        self,
        urls: List[str],
        cache_type: str = "page",
        ttl: int = 3600,
        extract_content: bool = True,
    ) -> List[Dict[str, Any]]:
        """批量爬取多个页面"""
        tasks = [
            self.fetch_page(url, cache_type, ttl, extract_content)
            for url in urls
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[{self.site_name}] 批量爬取失败[{i}]: {result}")
                output.append({
                    "url": urls[i] if i < len(urls) else "",
                    "success": False,
                    "metadata": {"error": str(result)},
                })
            else:
                output.append(result)
        return output

    @staticmethod
    def extract_text_by_keywords(content: str, keywords: List[str], context_lines: int = 3) -> str:
        """
        从内容中提取包含关键词的段落

        Args:
            content: 原始内容（Markdown）
            keywords: 关键词列表
            context_lines: 上下文行数

        Returns:
            提取的相关段落
        """
        lines = content.split("\n")
        result_lines = []
        matched_indices = set()

        for i, line in enumerate(lines):
            for kw in keywords:
                if kw in line:
                    for j in range(
                        max(0, i - context_lines),
                        min(len(lines), i + context_lines + 1)
                    ):
                        matched_indices.add(j)
                    break

        for i in sorted(matched_indices):
            result_lines.append(lines[i])

        return "\n".join(result_lines)


def run_async(coro):
    """同步方式运行异步协程"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已有运行中的事件循环，创建新的
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        return loop.run_until_complete(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
