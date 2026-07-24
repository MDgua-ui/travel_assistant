"""
数据增强器 - 将爬取的旅游数据整合到攻略生成流程中
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .base_crawler import BaseCrawler
from .mafengwo_crawler import MafengwoCrawler
from .ctrip_crawler import CtripCrawler
from .travel_data_store import TravelDataStore, get_data_store

logger = logging.getLogger(__name__)


class TravelDataEnricher:
    """
    旅游数据增强器
    负责采集、整合、格式化多源旅游数据，注入到AI攻略生成流程
    """

    def __init__(self):
        self.store = get_data_store()
        self._mafengwo: Optional[MafengwoCrawler] = None
        self._ctrip: Optional[CtripCrawler] = None

    async def _get_mafengwo(self) -> MafengwoCrawler:
        if self._mafengwo is None:
            self._mafengwo = MafengwoCrawler()
        return self._mafengwo

    async def _get_ctrip(self) -> CtripCrawler:
        if self._ctrip is None:
            self._ctrip = CtripCrawler()
        return self._ctrip

    async def close(self):
        """关闭所有爬虫"""
        for crawler in [self._mafengwo, self._ctrip]:
            if crawler:
                await crawler.close()

    async def enrich_city_data(self, city: str, force_refresh: bool = False) -> Dict:
        """
        为城市采集和整合多源数据

        Args:
            city: 城市名称
            force_refresh: 是否强制刷新

        Returns:
            整合后的城市数据
        """
        result = {
            "city": city,
            "enriched_at": datetime.now().isoformat(),
            "sources": [],
            "attractions": [],
            "food": [],
            "guide_content": {},
            "stats": {},
        }

        # 1. 从存储中查找已有数据
        if not force_refresh:
            existing_guide = self.store.get_guide(city)
            existing_attractions = self.store.get_attractions(city)

            if existing_guide:
                result["guide_content"] = existing_guide
                result["sources"].append("local_guide")
                logger.info(f"📦 {city} - 使用已有攻略数据")

            if existing_attractions:
                result["attractions"] = existing_attractions
                result["sources"].append("local_attractions")
                logger.info(f"📦 {city} - 使用已有景点数据({len(existing_attractions)}个)")

            if existing_guide and existing_attractions:
                result["stats"] = {
                    "attraction_count": len(existing_attractions),
                    "has_guide": True,
                    "data_sources": result["sources"],
                }
                return result

        # 2. 爬取马蜂窝数据
        try:
            mafengwo = await self._get_mafengwo()

            # 爬取攻略
            guide_data = await mafengwo.get_travel_guide(city)
            if guide_data and not guide_data.get("error"):
                self.store.save_guide(city, guide_data)
                result["guide_content"] = guide_data
                result["sources"].append("mafengwo_guide")
                # 提取美食推荐
                foods = guide_data.get("food_recommendations", [])
                if foods:
                    result["food"].extend(foods)

            # 搜索目的地
            dest_data = await mafengwo.search_destination(city)
            if dest_data and not dest_data.get("error"):
                pois = dest_data.get("pois", [])
                for poi in pois[:8]:
                    result["attractions"].append({
                        "name": poi.get("name", ""),
                        "description": poi.get("description", ""),
                        "source": "mafengwo",
                    })
                result["sources"].append("mafengwo_search")

        except Exception as e:
            logger.warning(f"马蜂窝数据采集失败({city}): {e}")

        # 3. 爬取携程数据
        try:
            ctrip = await self._get_ctrip()

            # 获取热门景点
            hot_data = await ctrip.search_attractions(city)
            if hot_data and not hot_data.get("error"):
                ctrip_attractions = hot_data.get("attractions", [])
                for attr in ctrip_attractions:
                    # 去重
                    name = attr.get("name", "")
                    if name and not any(a.get("name") == name for a in result["attractions"]):
                        result["attractions"].append({
                            "name": name,
                            "rating": attr.get("rating", ""),
                            "price": attr.get("price", ""),
                            "source": "ctrip",
                        })
                result["sources"].append("ctrip")
                logger.info(f"✅ 携程数据: {city} - {len(ctrip_attractions)}个景点")

        except Exception as e:
            logger.warning(f"携程数据采集失败({city}): {e}")

        # 4. 保存景点数据
        for attr in result["attractions"]:
            self.store.save_attraction(city, attr)

        # 5. 统计
        result["stats"] = {
            "attraction_count": len(result["attractions"]),
            "food_count": len(result["food"]),
            "has_guide": bool(result.get("guide_content")),
            "data_sources": result["sources"],
        }

        logger.info(f"📊 {city} 数据采集完成: {result['stats']}")
        return result

    def format_for_llm_prompt(
        self,
        city: str,
        days: int,
        preference: str = "",
        enriched_data: Optional[Dict] = None,
    ) -> str:
        """
        将采集的数据格式化为 LLM 提示词中的数据部分

        Args:
            city: 目标城市
            days: 游玩天数
            preference: 旅行偏好
            enriched_data: 增强后的数据(如未提供则从存储获取)

        Returns:
            格式化后的数据字符串，可直接拼接到 Prompt 中
        """
        if enriched_data is None:
            enriched_data = {
                "city": city,
                "attractions": [],
                "food": [],
                "guide_content": {},
                "sources": [],
            }

            # 从存储获取
            stored_guide = self.store.get_guide(city)
            stored_attractions = self.store.get_attractions(city)

            if stored_guide:
                enriched_data["guide_content"] = stored_guide
                foods = stored_guide.get("food_recommendations", [])
                enriched_data["food"] = [{"name": f.get("name", "")} for f in foods]
                enriched_data["sources"].append("mafengwo")

            if stored_attractions:
                enriched_data["attractions"] = stored_attractions
                for attr in stored_attractions:
                    if attr.get("source") and attr["source"] not in enriched_data["sources"]:
                        enriched_data["sources"].append(attr["source"])

        parts = []
        parts.append("=" * 60)
        parts.append(f"【真实旅游数据】- {city}")
        parts.append(f"数据来源: {', '.join(enriched_data.get('sources', ['无']))}")
        parts.append(f"采集时间: {enriched_data.get('enriched_at', '未知')}")
        parts.append("=" * 60)

        # 景点信息
        attractions = enriched_data.get("attractions", [])
        if attractions:
            parts.append(f"\n📍 **真实景点数据** (共{len(attractions)}个):")
            for i, attr in enumerate(attractions[:15], 1):
                name = attr.get("name", "")
                rating = attr.get("rating", "")
                price = attr.get("price", "")
                desc = attr.get("description", "")
                source = attr.get("source", "")

                line = f"  {i}. {name}"
                extras = []
                if rating:
                    extras.append(f"评分:{rating}")
                if price:
                    extras.append(f"门票:{price}")
                if extras:
                    line += f" ({', '.join(extras)})"
                if source:
                    line += f" [来源:{source}]"
                if desc:
                    line += f"\n     简介: {desc[:120]}"
                parts.append(line)

        # 美食推荐
        foods = enriched_data.get("food", [])
        if foods:
            parts.append(f"\n🍜 **真实美食推荐**:")
            for i, food in enumerate(foods[:10], 1):
                name = food.get("name", "")
                if name:
                    parts.append(f"  {i}. {name}")

        # 攻略摘要
        guide = enriched_data.get("guide_content", {})
        if isinstance(guide, dict) and guide:
            content_sections = guide.get("content_sections", {})
            if content_sections:
                parts.append(f"\n📝 **攻略内容摘要**:")
                for title, content in list(content_sections.items())[:5]:
                    summary = content[:200] if content else ""
                    if summary:
                        parts.append(f"\n  ### {title}")
                        parts.append(f"  {summary}")
            elif guide.get("content"):
                parts.append(f"\n📝 **攻略内容**:")
                parts.append(guide["content"][:500])

        parts.append("\n" + "=" * 60)
        parts.append("⚠️ 请基于以上真实数据生成攻略。确保:")
        parts.append("1. 景点名称、门票价格、开放时间必须与采集数据一致")
        parts.append("2. 美食推荐优先使用真实数据中的餐厅")
        parts.append("3. 如果数据来源标注来自蚂蜂窝/携程，优先参考该数据")
        parts.append("4. 补充合理的时间安排和交通路线")
        parts.append("=" * 60)

        return "\n".join(parts)

    def get_city_data_prompt(self, city: str, days: int, preference: str = "") -> str:
        """
        同步版本的获取增强数据 Prompt

        Args:
            city: 城市
            days: 天数
            preference: 偏好

        Returns:
            数据 Prompt 片段
        """
        return self.format_for_llm_prompt(city, days, preference)


def run_async_enrich(city: str, force_refresh: bool = False) -> Dict:
    """同步运行数据增强"""
    async def _run():
        enricher = TravelDataEnricher()
        try:
            result = await enricher.enrich_city_data(city, force_refresh)
            return result
        finally:
            await enricher.close()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(_run())
        return loop.run_until_complete(_run())
    except RuntimeError:
        return asyncio.run(_run())
