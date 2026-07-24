"""
旅游数据存储层 - 管理爬取数据、索引、检索
所有爬取的数据统一存储为 JSON 文件，带索引检索
"""
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from .config import DATA_DIR, ATTRACTIONS_DIR, GUIDES_DIR, CACHE_DIR

logger = logging.getLogger(__name__)


class TravelDataStore:
    """旅游数据存储和检索"""

    def __init__(self):
        self._index: Dict[str, Dict] = {}
        self._ensure_dirs()
        self._load_index()

    def _ensure_dirs(self):
        """确保数据目录存在"""
        for d in [DATA_DIR, ATTRACTIONS_DIR, GUIDES_DIR, CACHE_DIR]:
            os.makedirs(d, exist_ok=True)

    def _load_index(self):
        """加载数据索引"""
        index_file = os.path.join(DATA_DIR, "_index.json")
        if os.path.exists(index_file):
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
                logger.info(f"📑 已加载数据索引: {len(self._index)} 条记录")
            except Exception as e:
                logger.warning(f"索引加载失败: {e}")
                self._index = {}

    def _save_index(self):
        """保存数据索引"""
        index_file = os.path.join(DATA_DIR, "_index.json")
        try:
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(self._index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"索引保存失败: {e}")

    def save_attraction(self, city: str, attraction_data: Dict) -> str:
        """
        保存景点数据

        Args:
            city: 所属城市
            attraction_data: 景点信息

        Returns:
            文件路径
        """
        name = attraction_data.get("name", f"unknown_{int(time.time())}")
        safe_name = self._safe_filename(name)
        file_path = os.path.join(ATTRACTIONS_DIR, f"{city}_{safe_name}.json")

        data = {
            **attraction_data,
            "city": city,
            "saved_at": datetime.now().isoformat(),
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 更新索引
            key = f"attraction:{city}:{name}"
            self._index[key] = {
                "type": "attraction",
                "city": city,
                "name": name,
                "file": file_path,
                "source": attraction_data.get("source", "unknown"),
                "updated_at": data["saved_at"],
            }
            self._save_index()

            logger.info(f"✅ 景点数据已保存: {city} - {name}")
            return file_path
        except Exception as e:
            logger.error(f"景点数据保存失败: {e}")
            return ""

    def save_guide(self, city: str, guide_data: Dict) -> str:
        """
        保存攻略数据

        Args:
            city: 城市名称
            guide_data: 攻略数据

        Returns:
            文件路径
        """
        safe_name = self._safe_filename(city)
        file_path = os.path.join(GUIDES_DIR, f"guide_{safe_name}.json")

        data = {
            **guide_data,
            "city": city,
            "saved_at": datetime.now().isoformat(),
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            key = f"guide:{city}"
            self._index[key] = {
                "type": "guide",
                "city": city,
                "file": file_path,
                "source": guide_data.get("source", "unknown"),
                "updated_at": data["saved_at"],
            }
            self._save_index()

            logger.info(f"✅ 攻略数据已保存: {city}")
            return file_path
        except Exception as e:
            logger.error(f"攻略数据保存失败: {e}")
            return ""

    def get_attractions(self, city: str, limit: int = 15) -> List[Dict]:
        """
        获取城市景点数据

        Args:
            city: 城市名称
            limit: 返回数量限制

        Returns:
            景点数据列表
        """
        results = []

        # 从索引中查找
        for key, meta in self._index.items():
            if meta.get("type") == "attraction" and meta.get("city") == city:
                try:
                    file_path = meta["file"]
                    if os.path.exists(file_path):
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        results.append(data)
                except Exception as e:
                    logger.warning(f"读取景点数据失败: {meta.get('name')}, {e}")
            if len(results) >= limit:
                break

        # 如果索引中不够，扫描目录
        if len(results) < limit:
            for filename in os.listdir(ATTRACTIONS_DIR):
                if filename.startswith(city) and filename.endswith(".json"):
                    try:
                        file_path = os.path.join(ATTRACTIONS_DIR, filename)
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if data not in results:
                            results.append(data)
                    except Exception:
                        continue
                if len(results) >= limit:
                    break

        return results[:limit]

    def get_guide(self, city: str) -> Optional[Dict]:
        """
        获取城市攻略

        Args:
            city: 城市名称

        Returns:
            攻略数据
        """
        # 先从索引查找
        key = f"guide:{city}"
        if key in self._index:
            file_path = self._index[key]["file"]
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    logger.warning(f"读取攻略失败: {e}")

        # 扫描目录
        safe_name = self._safe_filename(city)
        file_path = os.path.join(GUIDES_DIR, f"guide_{safe_name}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        return None

    def search_by_keyword(self, keyword: str, data_type: str = "all") -> List[Dict]:
        """
        关键词搜索

        Args:
            keyword: 搜索关键词
            data_type: 数据类型 (attraction/guide/all)

        Returns:
            匹配的数据列表
        """
        results = []

        for key, meta in self._index.items():
            if data_type != "all" and meta.get("type") != data_type:
                continue

            name = meta.get("name", "")
            city = meta.get("city", "")

            if keyword in name or keyword in city or keyword in key:
                file_path = meta["file"]
                if os.path.exists(file_path):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        data["_match_score"] = self._calc_match_score(keyword, data)
                        results.append(data)
                    except Exception:
                        continue

        results.sort(key=lambda x: x.get("_match_score", 0), reverse=True)
        return results[:20]

    def get_stats(self) -> Dict:
        """
        获取数据统计

        Returns:
            统计信息
        """
        stats = {
            "total_indexed": len(self._index),
            "attractions": 0,
            "guides": 0,
            "cities_covered": set(),
            "sources": set(),
        }

        for key, meta in self._index.items():
            if meta.get("type") == "attraction":
                stats["attractions"] += 1
            elif meta.get("type") == "guide":
                stats["guides"] += 1
            if meta.get("city"):
                stats["cities_covered"].add(meta["city"])
            if meta.get("source"):
                stats["sources"].add(meta["source"])

        stats["cities_covered"] = list(stats["cities_covered"])
        stats["sources"] = list(stats["sources"])
        return stats

    def clear_expired(self, max_age_days: int = 30):
        """
        清理过期数据

        Args:
            max_age_days: 最大保留天数
        """
        cutoff = time.time() - max_age_days * 86400
        expired_keys = []

        for key, meta in self._index.items():
            updated = meta.get("updated_at", "")
            try:
                dt = datetime.fromisoformat(updated)
                if dt.timestamp() < cutoff:
                    expired_keys.append(key)
                    file_path = meta["file"]
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"🗑️ 已删除过期数据: {key}")
            except (ValueError, OSError):
                continue

        for key in expired_keys:
            del self._index[key]

        if expired_keys:
            self._save_index()
            logger.info(f"🧹 清理完成: 删除了 {len(expired_keys)} 条过期记录")

    @staticmethod
    def _safe_filename(name: str) -> str:
        """生成安全的文件名"""
        import re
        safe = re.sub(r'[\\/:*?"<>|]', '_', name)
        return safe.strip()[:60]

    @staticmethod
    def _calc_match_score(keyword: str, data: Dict) -> int:
        """计算匹配度评分"""
        score = 0
        kw_lower = keyword.lower()
        data_str = json.dumps(data, ensure_ascii=False).lower()

        # 精确匹配加分
        score += data_str.count(kw_lower) * 10
        # 名称匹配额外加分
        name = data.get("name", "").lower()
        if kw_lower in name:
            score += 50
        # 城市匹配加分
        city = data.get("city", "").lower()
        if kw_lower in city:
            score += 30

        return score


# 全局单例
_store_instance = None


def get_data_store() -> TravelDataStore:
    """获取数据存储单例"""
    global _store_instance
    if _store_instance is None:
        _store_instance = TravelDataStore()
    return _store_instance
