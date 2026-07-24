"""
预加载旅游数据 - 在启动前爬取热门城市数据
运行: python preload_data.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import run_async_enrich, get_data_store
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 热门旅游城市列表
POPULAR_CITIES = [
    "北京", "上海", "成都", "杭州",
    "西安", "三亚", "厦门", "重庆",
    "大理", "丽江", "桂林", "张家界",
]

if __name__ == "__main__":
    print("=" * 60)
    print("🌍 智能旅游顾问 - 数据预加载")
    print("=" * 60)

    store = get_data_store()
    stats_before = store.get_stats()
    print(f"\n📊 当前数据: {stats_before['total_indexed']} 条记录")

    for city in POPULAR_CITIES:
        print(f"\n🔍 正在采集: {city}...")
        try:
            result = run_async_enrich(city, force_refresh=False)
            stats = result.get('stats', {})
            print(f"  ✅ {city}: {stats.get('attraction_count', 0)}个景点, "
                  f"来源: {', '.join(stats.get('data_sources', []))}")
        except Exception as e:
            print(f"  ⚠️ {city}: 采集失败 - {e}")

    stats_after = store.get_stats()
    print(f"\n{'=' * 60}")
    print(f"📊 预加载完成!")
    print(f"  总记录数: {stats_before['total_indexed']} → {stats_after['total_indexed']}")
    print(f"  景点数: {stats_after.get('attractions', 0)}")
    print(f"  覆盖城市: {len(stats_after.get('cities_covered', []))}")
    print(f"{'=' * 60}")
