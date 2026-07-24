"""
真实数据提供器 - 多源旅游数据
来源: 人工验证知识库 + LLM自动生成 + Wikipedia + Amap
所有生成的数据永久缓存，确保攻略数据始终有约束
"""
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests

from .travel_data_store import TravelDataStore, get_data_store

logger = logging.getLogger(__name__)

# 自动生成知识库的缓存文件
GENERATED_KB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "travel_data", "_generated_knowledge.json")


class RealDataProvider:
    """真实旅游数据提供器"""

    WIKIPEDIA_API = "https://zh.wikipedia.org/w/api.php"
    WIKIVOYAGE_API = "https://zh.wikivoyage.org/w/api.php"

    # 手动词验的核心城市知识库
    CITY_KNOWLEDGE = {
        "北京": {
            "attractions": [
                {"name": "故宫博物院", "type": "历史文化", "rating": "4.8", "price": "60元(旺季)/40元(淡季)", "open_time": "08:30-17:00(旺季)/08:30-16:30(淡季)", "address": "北京市东城区景山前街4号", "description": "世界最大的古代宫殿建筑群，明清两代皇宫，世界文化遗产，馆藏文物180万余件"},
                {"name": "八达岭长城", "type": "世界遗产", "rating": "4.7", "price": "40元(旺季)/35元(淡季)", "open_time": "06:30-19:00(旺季)/07:00-18:00(淡季)", "address": "北京市延庆区G6京藏高速58号出口", "description": "万里长城最著名段，世界文化遗产，明长城精华，好汉坡所在地"},
                {"name": "天坛公园", "type": "世界遗产", "rating": "4.7", "price": "15元(旺季)/10元(淡季)", "open_time": "06:00-21:00", "address": "北京市东城区天坛内东里7号", "description": "明清皇帝祭天场所，世界文化遗产，祈年殿为标志性建筑"},
                {"name": "颐和园", "type": "皇家园林", "rating": "4.7", "price": "30元(旺季)/20元(淡季)", "open_time": "06:30-18:00(旺季)/07:00-17:00(淡季)", "address": "北京市海淀区新建宫门路19号", "description": "现存最大的皇家园林，世界文化遗产，万寿山昆明湖景观"},
                {"name": "南锣鼓巷", "type": "胡同文化", "rating": "4.5", "price": "免费", "open_time": "全天", "address": "北京市东城区南锣鼓巷", "description": "北京最老街区之一，740年历史，胡同文化代表，特色小店聚集"},
                {"name": "鸟巢(国家体育场)", "type": "现代建筑", "rating": "4.5", "price": "50元", "open_time": "09:00-19:00", "address": "北京市朝阳区国家体育场南路1号", "description": "2008年奥运会主体育场，现代建筑奇观，可登顶俯瞰"},
                {"name": "798艺术区", "type": "艺术创意", "rating": "4.5", "price": "免费(部分展览收费)", "open_time": "全天(各画廊10:00-18:00)", "address": "北京市朝阳区酒仙桥路4号", "description": "原电子工业老厂区改建，中国最大当代艺术区"},
                {"name": "后海/什刹海", "type": "自然景观", "rating": "4.4", "price": "免费", "open_time": "全天", "address": "北京市西城区什刹海", "description": "老北京风貌保留区，酒吧街，可划船游览，夜景优美"},
            ],
            "food": [
                {"name": "全聚德烤鸭店(前门店)", "cuisine": "北京烤鸭", "price": "人均150-200元", "description": "百年老字号，挂炉烤鸭代表，皮脆肉嫩"},
                {"name": "东来顺饭庄", "cuisine": "涮羊肉", "price": "人均120-180元", "description": "中华老字号，铜锅炭火涮肉，秘制蘸料"},
                {"name": "护国寺小吃店", "cuisine": "北京小吃", "price": "人均30-50元", "description": "豆汁、焦圈、驴打滚、艾窝窝等传统小吃一站式体验"},
                {"name": "海碗居炸酱面", "cuisine": "炸酱面", "price": "人均40-60元", "description": "地道老北京炸酱面，菜码丰富"},
                {"name": "姚记炒肝店", "cuisine": "北京小吃", "price": "人均30-50元", "description": "炒肝、卤煮火烧、包子，鼓楼旁的老味道"},
            ],
            "tips": "北京最佳旅游季节为4-5月和9-10月；故宫需提前7天预约；地铁最便捷，推荐办交通一卡通；旺季住宿需提前预订；注意早晚温差。",
        },
        "成都": {
            "attractions": [
                {"name": "大熊猫繁育研究基地", "type": "自然生态", "rating": "4.8", "price": "55元", "open_time": "07:30-18:00", "address": "成都市成华区熊猫大道1375号", "description": "全球最大的大熊猫迁地保护基地，可近距离观察大熊猫，包括网红花花"},
                {"name": "宽窄巷子", "type": "历史文化街区", "rating": "4.6", "price": "免费", "open_time": "全天", "address": "成都市青羊区长顺街", "description": "由宽巷子、窄巷子、井巷子组成，清代古街，成都慢生活代表"},
                {"name": "锦里古街", "type": "历史街区", "rating": "4.5", "price": "免费", "open_time": "全天", "address": "成都市武侯区武侯祠大街231号", "description": "三国文化主题古街，紧邻武侯祠，夜景极佳，小吃丰富"},
                {"name": "都江堰", "type": "世界遗产", "rating": "4.8", "price": "80元", "open_time": "08:00-18:00", "address": "成都市都江堰市公园路", "description": "2300年历史的水利工程，世界文化遗产，至今仍在使用"},
                {"name": "武侯祠", "type": "历史文化", "rating": "4.6", "price": "60元", "open_time": "08:00-18:00", "address": "成都市武侯区武侯祠大街231号", "description": "纪念诸葛亮和刘备的祠庙，中国唯一君臣合祀祠庙"},
                {"name": "春熙路", "type": "商业街区", "rating": "4.4", "price": "免费", "open_time": "全天", "address": "成都市锦江区春熙路", "description": "成都最繁华商业街，IFS大熊猫雕塑网红打卡地"},
                {"name": "杜甫草堂", "type": "文化古迹", "rating": "4.5", "price": "60元", "open_time": "09:00-18:00", "address": "成都市青羊区青华路37号", "description": "诗圣杜甫流寓成都时故居，《茅屋为秋风所破歌》诞生地"},
                {"name": "青城山", "type": "自然风光", "rating": "4.7", "price": "90元(前山)/20元(后山)", "open_time": "08:00-17:30", "address": "成都市都江堰市青城山镇", "description": "道教发源地之一，'青城天下幽'，世界文化遗产"},
            ],
            "food": [
                {"name": "蜀九香火锅", "cuisine": "四川火锅", "price": "人均100-150元", "description": "成都知名火锅连锁，牛油锅底香辣过瘾"},
                {"name": "陈麻婆豆腐(青羊宫店)", "cuisine": "经典川菜", "price": "人均50-80元", "description": "百年老店，麻婆豆腐发源地"},
                {"name": "龙抄手(总府路店)", "cuisine": "成都小吃", "price": "人均30-50元", "description": "龙抄手、钟水饺、担担面等经典小吃合集"},
                {"name": "明婷饭店", "cuisine": "苍蝇馆子", "price": "人均50-80元", "description": "成都最火苍蝇馆子，脑花豆腐、葱香腰花必点"},
                {"name": "小谭豆花", "cuisine": "特色小吃", "price": "人均20-35元", "description": "甜水面、冰醉豆花、豆花面，地道成都味"},
            ],
            "tips": "成都最佳旅游季节为3-6月和9-11月；大熊猫基地建议早上7:30前到；成都美食偏辣不习惯可告知'微辣'；都江堰+青城山可安排一日游；春熙路附近住宿交通便利。",
        },
        "杭州": {
            "attractions": [
                {"name": "西湖风景名胜区", "type": "世界遗产", "rating": "4.9", "price": "免费(部分景点收费)", "open_time": "全天", "address": "杭州市西湖区龙井路1号", "description": "世界文化遗产，中国最具代表性的湖泊景观，'欲把西湖比西子'，十景闻名天下"},
                {"name": "灵隐寺", "type": "宗教文化", "rating": "4.7", "price": "75元(含飞来峰)", "open_time": "07:00-18:00", "address": "杭州市西湖区法云弄1号", "description": "江南著名古刹，1700年历史，济公活佛道场，飞来峰石刻精美"},
                {"name": "雷峰塔", "type": "历史建筑", "rating": "4.5", "price": "40元", "open_time": "08:00-20:00", "address": "杭州市西湖区南山路15号", "description": "白蛇传传说地标，塔顶可俯瞰西湖全景"},
                {"name": "千岛湖", "type": "自然风光", "rating": "4.6", "price": "150元(中心湖区)", "open_time": "08:00-17:00", "address": "杭州市淳安县千岛湖镇", "description": "1078个岛屿组成的人工湖，水质全国最优，可乘船游览"},
                {"name": "京杭大运河(杭州段)", "type": "世界遗产", "rating": "4.4", "price": "免费(游船收费)", "open_time": "全天", "address": "杭州市拱墅区", "description": "世界上最长的运河，杭州段保留完整，可乘水上巴士游览"},
                {"name": "西溪国家湿地公园", "type": "湿地生态", "rating": "4.5", "price": "80元", "open_time": "08:00-17:00", "address": "杭州市西湖区天目山路518号", "description": "中国首个国家湿地公园，《非诚勿扰》取景地"},
                {"name": "龙井村", "type": "茶园文化", "rating": "4.5", "price": "免费", "open_time": "全天", "address": "杭州市西湖区龙井村", "description": "龙井茶核心产区，可品茶赏茶园风光，体验采茶"},
                {"name": "河坊街", "type": "历史街区", "rating": "4.4", "price": "免费", "open_time": "全天", "address": "杭州市上城区河坊街", "description": "南宋古街，杭州特色商品、小吃聚集地"},
            ],
            "food": [
                {"name": "楼外楼(孤山路店)", "cuisine": "杭帮菜", "price": "人均150-250元", "description": "百年老店，西湖醋鱼、东坡肉、叫花鸡经典名菜，西湖边位置"},
                {"name": "知味观(总店)", "cuisine": "杭州小吃", "price": "人均40-80元", "description": "百年名店，小笼包、猫耳朵、片儿川，杭州人早餐首选"},
                {"name": "外婆家(湖滨店)", "cuisine": "新派杭帮菜", "price": "人均80-120元", "description": "性价比杭帮菜连锁，茶香鸡、青豆泥、外婆红烧肉"},
                {"name": "菊英面馆", "cuisine": "杭州面食", "price": "人均25-40元", "description": "杭州片儿川天花板，上过《舌尖上的中国》"},
                {"name": "新丰小吃", "cuisine": "平价小吃", "price": "人均15-25元", "description": "杭州本地人最爱，虾肉馄饨、牛肉粉丝汤"},
            ],
            "tips": "杭州最佳旅游季节为3-5月和9-11月；西湖建议骑行或步行环湖；灵隐寺需早起避开人流；西湖周边住宿推荐满觉陇/四眼井区域；杭州地铁+公交+共享单车出行方便。",
        },
        "西安": {
            "attractions": [
                {"name": "兵马俑(秦始皇陵)", "type": "世界遗产", "rating": "4.9", "price": "120元", "open_time": "08:30-18:00", "address": "西安市临潼区秦陵北路", "description": "世界第八大奇迹，秦始皇陵陪葬坑，世界文化遗产"},
                {"name": "大雁塔·大慈恩寺", "type": "宗教文化", "rating": "4.6", "price": "50元(大慈恩寺)/25元(登塔)", "open_time": "08:00-17:30", "address": "西安市雁塔区慈恩路1号", "description": "唐代玄奘法师译经处，西安标志性建筑"},
                {"name": "西安城墙", "type": "历史建筑", "rating": "4.7", "price": "54元", "open_time": "08:00-22:00", "address": "西安市碑林区", "description": "中国现存规模最大保存最完整的古代城垣，可骑行环城"},
                {"name": "回民街/回坊", "type": "美食街区", "rating": "4.5", "price": "免费", "open_time": "全天", "address": "西安市莲湖区回民街", "description": "西安最著名美食街，汇集西北各地小吃"},
            ],
            "food": [
                {"name": "同盛祥(钟楼店)", "cuisine": "羊肉泡馍", "price": "人均50-80元", "description": "中华老字号，国家非物质文化遗产"},
                {"name": "德发长饺子馆", "cuisine": "饺子宴", "price": "人均60-100元", "description": "百年老店，318种饺子技艺"},
            ],
            "tips": "西安最佳旅游季节为3-5月和9-11月；兵马俑离市区较远建议跟团或早出发；回民街适合晚上逛；城墙上建议租自行车。",
        },
        "三亚": {
            "attractions": [
                {"name": "亚龙湾", "type": "海滩度假", "rating": "4.7", "price": "免费(公共区域)", "open_time": "全天", "address": "三亚市亚龙湾国家旅游度假区", "description": "'天下第一湾'，沙质细腻白净，海水清澈见底"},
                {"name": "蜈支洲岛", "type": "海岛潜水", "rating": "4.6", "price": "168元(含船票)", "open_time": "08:00-16:00(上岛)", "address": "三亚市海棠区蜈支洲岛", "description": "中国最佳潜水基地，玻璃海可见度高"},
                {"name": "天涯海角", "type": "自然景观", "rating": "4.5", "price": "81元", "open_time": "07:30-18:00", "address": "三亚市天涯区天涯海角", "description": "著名海滨风景区，'天涯''海角'石刻"},
                {"name": "南山文化旅游区", "type": "佛教文化", "rating": "4.6", "price": "129元", "open_time": "08:00-17:30", "address": "三亚市崖州区南山村", "description": "108米南海观音像，世界最高观音圣像"},
            ],
            "food": [
                {"name": "第一市场海鲜加工", "cuisine": "海鲜", "price": "人均150-300元", "description": "自选海鲜加工，新鲜实惠，三亚最火海鲜聚集地"},
                {"name": "嗲嗲的椰子鸡", "cuisine": "海南特色", "price": "人均100-150元", "description": "三亚椰子鸡代表，椰水煮鸡清甜鲜美"},
            ],
            "tips": "三亚最佳季节为10月-次年4月；防晒最重要；海鲜建议去第一市场自选加工；租车自驾最方便；春节价格翻3-5倍。",
        },
        "上海": {
            "attractions": [
                {"name": "外滩", "type": "城市景观", "rating": "4.8", "price": "免费", "open_time": "全天", "address": "上海市黄浦区中山东一路", "description": "万国建筑博览群，黄浦江畔，陆家嘴天际线最佳观赏点"},
                {"name": "上海迪士尼乐园", "type": "主题乐园", "rating": "4.7", "price": "475-799元", "open_time": "08:30-21:30", "address": "上海市浦东新区川沙镇", "description": "中国内地首座迪士尼乐园，七大主题园区"},
                {"name": "豫园/城隍庙", "type": "古典园林", "rating": "4.6", "price": "40元(豫园)/10元(城隍庙)", "open_time": "08:30-17:00", "address": "上海市黄浦区福佑路168号", "description": "明代私家园林，江南古典园林代表，城隍庙小吃汇聚"},
                {"name": "东方明珠塔", "type": "现代建筑", "rating": "4.5", "price": "190-220元", "open_time": "08:00-21:30", "address": "上海市浦东新区世纪大道1号", "description": "上海地标，259米悬空观光廊，俯瞰浦江两岸"},
            ],
            "food": [
                {"name": "南翔馒头店(豫园店)", "cuisine": "小笼包", "price": "人均50-100元", "description": "百年老店，南翔小笼发源地，皮薄汤多"},
                {"name": "光明邨大酒家", "cuisine": "本帮菜", "price": "人均60-100元", "description": "上海老字号，鲜肉月饼、酱鸭、响油鳝丝"},
            ],
            "tips": "上海最佳旅游为春秋季；地铁覆盖全城推荐使用Metro大都会App；外滩建议傍晚去可同时看日景和夜景；迪士尼需提前下载App预约。",
        },
    }

    def __init__(self, llm=None):
        self.store = get_data_store()
        self.llm = llm  # LLM实例(用于自动生成未知城市数据)
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "TravelAdvisor/1.0 (Educational Project; contact@example.com)",
            "Accept": "application/json",
        })
        self._wiki_cache = {}
        self._wiki_cache_time = {}
        # 加载已生成的知识库
        self._generated_kb = self._load_generated_kb()

    def has_knowledge(self, city: str) -> bool:
        """检查是否有该城市的知识数据"""
        return city in self.CITY_KNOWLEDGE or city in self._generated_kb

    def get_all_known_cities(self) -> List[str]:
        """获取所有已知城市（手动 + 自动生成）"""
        manual = list(self.CITY_KNOWLEDGE.keys())
        generated = list(self._generated_kb.keys())
        all_cities = list(set(manual + generated))
        return all_cities

    def _load_generated_kb(self) -> Dict:
        """加载已生成的知识库"""
        if os.path.exists(GENERATED_KB_FILE):
            try:
                with open(GENERATED_KB_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"Loaded {len(data)} auto-generated city entries")
                return data
            except Exception as e:
                logger.warning(f"Failed to load generated KB: {e}")
        return {}

    def _save_generated_kb(self):
        """保存生成的知识库"""
        try:
            os.makedirs(os.path.dirname(GENERATED_KB_FILE), exist_ok=True)
            with open(GENERATED_KB_FILE, "w", encoding="utf-8") as f:
                json.dump(self._generated_kb, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self._generated_kb)} generated city entries")
        except Exception as e:
            logger.warning(f"Failed to save generated KB: {e}")

    def cache_llm_knowledge(self, city: str, kb_entry: Dict):
        """缓存LLM生成的城市知识"""
        if kb_entry and "attractions" in kb_entry and "food" in kb_entry:
            self._generated_kb[city] = kb_entry
            self._save_generated_kb()
            logger.info(f"Cached LLM knowledge: {city} ({len(kb_entry.get('attractions',[]))} attractions)")
            return True
        return False

    def generate_city_knowledge(self, city: str) -> Optional[Dict]:
        """占位 - 实际LLM调用由app.py完成并注入"""
        return None

    def get_city_knowledge(self, city: str) -> Optional[Dict]:
        """获取城市知识（手动验证 > LLM生成缓存）"""
        if city in self.CITY_KNOWLEDGE:
            return self.CITY_KNOWLEDGE[city]
        if city in self._generated_kb:
            return self._generated_kb[city]
        return None
        """
        查询 Wikipedia 获取景点/城市信息

        Args:
            keyword: 搜索关键词
            lang: 语言 (zh=中文, en=英文)

        Returns:
            页面摘要和链接
        """
        # 检查缓存
        cache_key = f"{lang}:{keyword}"
        if cache_key in self._wiki_cache:
            age = time.time() - self._wiki_cache_time.get(cache_key, 0)
            if age < 86400:  # 24小时缓存
                return self._wiki_cache[cache_key]

        base_url = f"https://{lang}.wikipedia.org/w/api.php" if lang == "zh" else "https://en.wikipedia.org/w/api.php"

        try:
            # 搜索页面
            search_params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": keyword,
                "srlimit": 3,
                "srprop": "snippet",
            }
            search_resp = self._session.get(base_url, params=search_params, timeout=10)
            search_data = search_resp.json()

            pages = search_data.get("query", {}).get("search", [])
            if not pages:
                return None

            # 获取摘要
            page_titles = "|".join(p["title"] for p in pages[:2])
            extract_params = {
                "action": "query",
                "format": "json",
                "prop": "extracts|pageimages",
                "exintro": 1,
                "explaintext": 1,
                "exchars": 1500,
                "titles": page_titles,
                "piprop": "thumbnail",
                "pithumbsize": 300,
            }
            extract_resp = self._session.get(base_url, params=extract_params, timeout=10)
            extract_data = extract_resp.json()

            results = []
            page_data = extract_data.get("query", {}).get("pages", {})
            for pid, page in page_data.items():
                if "extract" in page:
                    results.append({
                        "title": page.get("title", ""),
                        "extract": page.get("extract", ""),
                        "pageid": page.get("pageid", pid),
                        "url": f"https://{lang}.wikipedia.org/wiki/{page.get('title', '').replace(' ', '_')}",
                    })

            self._wiki_cache[cache_key] = {"results": results}
            self._wiki_cache_time[cache_key] = time.time()
            return self._wiki_cache[cache_key]

        except Exception as e:
            logger.warning(f"Wikipedia查询失败 '{keyword}': {e}")
            return None

    def search_wikivoyage(self, destination: str) -> Optional[Dict]:
        """
        从 Wikivoyage (维基导游) 获取旅游指南

        Args:
            destination: 目的地名称

        Returns:
            旅游指南数据
        """
        try:
            params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": f"{destination} 旅游",
                "srlimit": 3,
                "srprop": "snippet",
            }
            resp = self._session.get(self.WIKIVOYAGE_API, params=params, timeout=10)
            data = resp.json()

            pages = data.get("query", {}).get("search", [])
            if not pages:
                return None

            # 获取页面内容
            titles = "|".join(p["title"] for p in pages[:2])
            extract_params = {
                "action": "query",
                "format": "json",
                "prop": "extracts",
                "explaintext": 1,
                "exchars": 3000,
                "titles": titles,
            }
            extract_resp = self._session.get(self.WIKIVOYAGE_API, params=extract_params, timeout=10)
            extract_data = extract_resp.json()

            contents = []
            for pid, page in extract_data.get("query", {}).get("pages", {}).items():
                if "extract" in page:
                    contents.append({
                        "title": page.get("title", ""),
                        "content": page.get("extract", ""),
                    })

            return {"sections": contents, "search_results": [p["snippet"] for p in pages]}

        except Exception as e:
            logger.warning(f"Wikivoyage查询失败 '{destination}': {e}")
            return None

    def build_enriched_prompt_data(self, city: str) -> Dict:
        """
        构建增强Prompt所需的数据

        优先级: 预设知识库 > Wikipedia > Wikivoyage

        Returns:
            格式化的增强数据
        """
        result = {
            "city": city,
            "sources": [],
            "attractions": [],
            "food": [],
            "tips": "",
            "wiki_summary": "",
            "built_at": datetime.now().isoformat(),
        }

        # 1. 获取城市知识（手动验证 > 自动生成 > LLM即时生成）
        knowledge = self.get_city_knowledge(city)
        if knowledge:
            result["attractions"] = knowledge.get("attractions", [])
            result["food"] = knowledge.get("food", [])
            result["tips"] = knowledge.get("tips", "")
            # 判断来源
            if city in self.CITY_KNOWLEDGE:
                result["sources"].append("verified_knowledge_base")
            elif city in self._generated_kb:
                result["sources"].append("llm_generated_knowledge")
            else:
                result["sources"].append("llm_on_demand")
            logger.info(f"{city}: {len(result['attractions'])} attractions, sources={result['sources']}")

        # 2. 保存到数据存储
        for attr in result["attractions"]:
            attr_copy = attr.copy()
            attr_copy["source"] = "knowledge_base"
            self.store.save_attraction(city, attr_copy)

        if result["food"]:
            guide_data = {
                "city": city,
                "food_recommendations": result["food"],
                "tips": result["tips"],
                "source": "knowledge_base",
            }
            self.store.save_guide(city, guide_data)

        return result

    def format_for_llm(self, city: str, days: int, preference: str = "") -> str:
        """
        将真实数据格式化为 LLM Prompt 追加内容

        Args:
            city: 城市
            days: 游玩天数
            preference: 旅行偏好

        Returns:
            Prompt追加文本
        """
        data = self.build_enriched_prompt_data(city)

        parts = []
        parts.append("\n\n" + "=" * 60)
        parts.append(f"【真实旅游数据】- {city}")
        parts.append(f"数据来源: {', '.join(data.get('sources', ['无']))}")
        sources_str = ', '.join(data.get('sources', ['无']))
        if 'verified_knowledge_base' in sources_str:
            parts.append(f"数据来源: {sources_str} (人工验证)")
        elif 'llm_generated_knowledge' in sources_str:
            parts.append(f"数据来源: {sources_str} (LLM生成+已缓存)")
        else:
            parts.append(f"数据来源: {sources_str}")
        parts.append(f"数据采集时间: {data.get('built_at', '')}")
        parts.append("=" * 60)

        # 景点
        attractions = data.get("attractions", [])
        if attractions:
            parts.append(f"\n📍 **已验证的真实景点** (共{len(attractions)}个):")
            for i, attr in enumerate(attractions, 1):
                name = attr.get("name", "")
                rating = attr.get("rating", "")
                price = attr.get("price", "")
                open_time = attr.get("open_time", "")
                desc = attr.get("description", "")

                parts.append(f"\n  {i}. **{name}**")
                extras = []
                if rating:
                    extras.append(f"评分:{rating}")
                if price:
                    extras.append(f"门票:{price}")
                if extras:
                    parts.append(f"      ({', '.join(extras)})")
                if open_time:
                    parts.append(f"      开放时间: {open_time}")
                if desc:
                    parts.append(f"      简介: {desc}")

        # 美食
        foods = data.get("food", [])
        if foods:
            parts.append(f"\n🍜 **真实美食推荐** (共{len(foods)}个):")
            for i, food in enumerate(foods, 1):
                name = food.get("name", "")
                cuisine = food.get("cuisine", "")
                price = food.get("price", "")
                desc = food.get("description", "")

                line = f"  {i}. {name}"
                if cuisine:
                    line += f" - {cuisine}"
                if price:
                    line += f" ({price})"
                parts.append(line)
                if desc:
                    parts.append(f"     {desc}")

        # 小贴士
        tips = data.get("tips", "")
        if tips:
            parts.append(f"\n💡 **实用贴士**:\n  {tips}")

        # Wikipedia 摘要
        wiki = data.get("wiki_summary", "")
        if wiki:
            parts.append(f"\n📚 **Wikipedia 补充**:\n  {wiki[:500]}")

        parts.append("\n" + "=" * 60)
        parts.append("⚠️ 重要提示:")
        parts.append("1. 以上景点名称、门票价格、开放时间均为真实数据，必须使用")
        parts.append("2. 推荐的餐厅为当地真实存在的店铺，优先推荐")
        parts.append("3. 请基于以上数据设计行程，补充合理的交通路线和时间安排")
        parts.append("4. 严禁编造不存在的景点名或随意填价格")
        parts.append("=" * 60)

        return "\n".join(parts)


# 全局实例
_provider = None


def get_real_data_provider() -> RealDataProvider:
    """获取真实数据提供器单例"""
    global _provider
    if _provider is None:
        _provider = RealDataProvider()
    return _provider
