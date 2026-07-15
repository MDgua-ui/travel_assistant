from flask import Flask, request, jsonify, render_template
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import os
import requests
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

places_cache = {}
cache_expire_time = 3600

llm = ChatOpenAI(
    model="kimi-k2.7-code-highspeed",
    api_key="sk-y26L4uFq1QLSNBn2Ksts0JjP3Fno5ivh0jIN2f0jZTr1O0cB",
    base_url="https://tokenhub.tencentmaas.com/v1",
    temperature=1,
    max_tokens=15000,
)

provinces_data = {
    "云南": ["昆明", "大理", "丽江", "香格里拉", "西双版纳", "腾冲", "普洱"],
    "四川": ["成都", "九寨沟", "都江堰", "青城山", "乐山", "峨眉山", "稻城亚丁"],
    "广东": ["广州", "深圳", "珠海", "佛山", "东莞", "中山", "惠州"],
    "浙江": ["杭州", "宁波", "温州", "绍兴", "嘉兴", "湖州", "金华", "舟山", "台州", "丽水"],
    "江苏": ["南京", "苏州", "无锡", "常州", "扬州", "镇江", "南通", "泰州"],
    "湖南": ["长沙", "张家界", "岳阳", "常德", "衡阳", "湘潭", "株洲"],
    "湖北": ["武汉", "宜昌", "襄阳", "荆州", "十堰", "黄石", "黄冈"],
    "河南": ["郑州", "开封", "洛阳", "安阳", "许昌", "商丘", "南阳"],
    "山东": ["济南", "青岛", "烟台", "威海", "潍坊", "淄博", "泰安"],
    "福建": ["福州", "厦门", "泉州", "漳州", "莆田", "宁德", "南平"],
    "安徽": ["合肥", "黄山", "芜湖", "蚌埠", "淮南", "马鞍山", "安庆"],
    "江西": ["南昌", "九江", "景德镇", "萍乡", "新余", "鹰潭", "赣州"],
    "陕西": ["西安", "宝鸡", "咸阳", "铜川", "渭南", "延安", "汉中"],
    "甘肃": ["兰州", "嘉峪关", "金昌", "白银", "天水", "酒泉", "张掖"],
    "青海": ["西宁", "海东", "海北", "黄南", "海南", "果洛", "玉树"],
    "贵州": ["贵阳", "遵义", "安顺", "毕节", "铜仁", "六盘水", "黔东南"],
    "广西": ["南宁", "桂林", "柳州", "梧州", "玉林", "贵港", "钦州"],
    "河北": ["石家庄", "唐山", "秦皇岛", "邯郸", "邢台", "保定", "张家口"],
    "山西": ["太原", "大同", "阳泉", "长治", "晋城", "朔州", "晋中"],
    "辽宁": ["沈阳", "大连", "鞍山", "抚顺", "本溪", "丹东", "锦州"],
    "吉林": ["长春", "吉林", "四平", "辽源", "通化", "白山", "松原"],
    "黑龙江": ["哈尔滨", "齐齐哈尔", "牡丹江", "佳木斯", "大庆", "鸡西", "双鸭山"],
    "内蒙古": ["呼和浩特", "包头", "乌海", "赤峰", "通辽", "鄂尔多斯", "呼伦贝尔"],
    "新疆": ["乌鲁木齐", "克拉玛依", "吐鲁番", "哈密", "阿克苏", "喀什", "和田"],
    "西藏": ["拉萨", "日喀则", "山南", "林芝", "昌都", "那曲", "阿里"],
    "海南": ["海口", "三亚", "文昌", "琼海", "万宁", "五指山", "东方"],
    "北京": ["北京"],
    "上海": ["上海"],
    "天津": ["天津"],
    "重庆": ["重庆"],
    "台湾": ["台北", "高雄", "台南", "台中", "新竹", "嘉义", "基隆"],
    "香港": ["香港"],
    "澳门": ["澳门"]
}

@app.route('/')
def index():
    return render_template('travel_assistant.html')



QWEATHER_API_KEY = "38554c1b2d74235ca5c8b5a1f839adeb"
QWEATHER_API_HOST = ""

AMAP_KEY = "1ee93aec7338f278ad571853c5cfcb55"

@app.route('/api/weather', methods=['GET'])
def get_weather():
    try:
        city = request.args.get('city', '')
        if not city:
            return jsonify({'error': '请输入城市名称'}), 400
        
        if QWEATHER_API_HOST:
            geo_url = f"https://{QWEATHER_API_HOST}/geo/v2/city/lookup?location={city}&key={QWEATHER_API_KEY}&range=cn&number=1"
            geo_response = requests.get(geo_url)
            
            if not geo_response.ok:
                return jsonify({'error': '无法找到该城市'}), 404
            
            geo_data = geo_response.json()
            
            if geo_data.get('code') != '200' or not geo_data.get('location'):
                return jsonify({'error': '无法找到该城市，请尝试其他名称'}), 404
            
            location = geo_data['location'][0]
            city_id = location['id']
            name = location['name']
            
            weather_url = f"https://{QWEATHER_API_HOST}/v7/weather/7d?location={city_id}&key={QWEATHER_API_KEY}"
            weather_response = requests.get(weather_url)
            
            if not weather_response.ok:
                return jsonify({'error': '获取天气数据失败'}), 500
            
            weather_data = weather_response.json()
            
            if weather_data.get('code') != '200':
                return jsonify({'error': '获取天气数据失败'}), 500
            
            daily = weather_data.get('daily', [])
            
            result_data = {
                'name': name,
                'daily': {
                    'time': [day.get('fxDate', '') for day in daily],
                    'temperature_2m_max': [int(day.get('tempMax', 0)) for day in daily],
                    'temperature_2m_min': [int(day.get('tempMin', 0)) for day in daily],
                    'weathercode': [day.get('textDay', '') for day in daily],
                    'weather_desc': [day.get('textDay', '') for day in daily]
                }
            }
            
            return jsonify(result_data)
        else:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=zh&format=json"
            geo_response = requests.get(geo_url)
            
            if not geo_response.ok:
                return jsonify({'error': '无法找到该城市'}), 404
            
            geo_data = geo_response.json()
            
            if not geo_data.get('results') or len(geo_data['results']) == 0:
                return jsonify({'error': '无法找到该城市，请尝试其他名称'}), 404
            
            result = geo_data['results'][0]
            latitude = result['latitude']
            longitude = result['longitude']
            name = result['name']
            
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=Asia/Shanghai&forecast_days=7"
            weather_response = requests.get(weather_url)
            
            if not weather_response.ok:
                return jsonify({'error': '获取天气数据失败'}), 500
            
            weather_data = weather_response.json()
            
            return jsonify({
                'name': name,
                'latitude': latitude,
                'longitude': longitude,
                'daily': weather_data['daily']
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search_places', methods=['GET'])
def search_places():
    try:
        city = request.args.get('city', '')
        keywords = request.args.get('keywords', '景点')
        if not city:
            return jsonify({'error': '请输入城市名称'}), 400
        
        places = get_places(city, keywords)
        
        if places:
            return jsonify({'city': city, 'places': [{'name': p} for p in places]})
        else:
            return jsonify({'city': city, 'places': [], 'message': '未找到该城市的景点数据，请尝试其他城市'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/geocode', methods=['GET'])
def geocode():
    try:
        address = request.args.get('address', '')
        if not address:
            return jsonify({'error': '请输入地址'}), 400
        
        url = f"https://restapi.amap.com/v3/geocode/geo?address={address}&output=json&key={AMAP_KEY}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == '1' and data.get('geocodes'):
                result = data['geocodes'][0]
                location = result.get('location', '')
                if location:
                    lng, lat = location.split(',')
                    return jsonify({
                        'address': address,
                        'latitude': float(lat),
                        'longitude': float(lng),
                        'formatted_address': result.get('formatted_address', '')
                    })
            else:
                logger.warning(f"地理编码失败: {address}, status={data.get('status')}")
        
        return jsonify({'error': '地理编码失败'}), 500
    except Exception as e:
        logger.error(f"地理编码异常: {address}, error={str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/place_detail', methods=['GET'])
def place_detail():
    try:
        name = request.args.get('name', '')
        city = request.args.get('city', '')
        if not name:
            return jsonify({'error': '请输入地点名称'}), 400
        
        url = f"https://restapi.amap.com/v3/place/text?keywords={name}&city={city}&output=json&key={AMAP_KEY}&offset=1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == '1' and data.get('pois'):
                result = data['pois'][0]
                location = result.get('location', '')
                if location:
                    lng, lat = location.split(',')
                    return jsonify({
                        'name': result.get('name', ''),
                        'latitude': float(lat),
                        'longitude': float(lng),
                        'address': result.get('address', ''),
                        'detail': result.get('tel', ''),
                        'uid': result.get('id', '')
                    })
            else:
                logger.warning(f"地点查询失败: {name}, status={data.get('status')}")
        
        return jsonify({'error': '地点查询失败'}), 500
    except Exception as e:
        logger.error(f"地点查询异常: {name}, error={str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search_around', methods=['GET'])
def search_around():
    try:
        location = request.args.get('location', '')
        radius = request.args.get('radius', '1000')
        keywords = request.args.get('keywords', '景点')
        if not location:
            return jsonify({'error': '请输入坐标'}), 400
        
        url = f"https://restapi.amap.com/v3/place/around?keywords={keywords}&location={location}&radius={radius}&output=json&key={AMAP_KEY}&offset=20"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == '1':
                places = []
                for result in data.get('pois', []):
                    location = result.get('location', '')
                    if location:
                        lng, lat = location.split(',')
                        places.append({
                            'name': result.get('name', ''),
                            'latitude': float(lat),
                            'longitude': float(lng),
                            'address': result.get('address', ''),
                            'distance': result.get('distance', '')
                        })
                return jsonify({'places': places})
            else:
                logger.warning(f"周边搜索失败: location={location}, status={data.get('status')}")
        
        return jsonify({'places': []})
    except Exception as e:
        logger.error(f"周边搜索异常: location={location}, error={str(e)}")
        return jsonify({'error': str(e)}), 500

def get_places(city, keywords='景点'):
    try:
        cache_key = f"{city}_{keywords}"
        if cache_key in places_cache:
            cached = places_cache[cache_key]
            if time.time() - cached['time'] < cache_expire_time:
                logger.info(f"使用缓存数据: {city}")
                return cached['places']
        
        url = f"https://restapi.amap.com/v3/place/text?keywords={keywords}&city={city}&output=json&key={AMAP_KEY}&offset=15"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == '1':
                places = []
                for result in data.get('pois', []):
                    name = result.get('name', '')
                    if name and name not in places:
                        places.append(name)
                places = places[:15]
                places_cache[cache_key] = {'places': places, 'time': time.time()}
                logger.info(f"高德地图API成功获取: {city}, {len(places)}个景点")
                return places
            else:
                logger.warning(f"高德地图API状态异常: {city}, status={data.get('status')}, message={data.get('info')}")
        
        return []
    except Exception as e:
        logger.error(f"获取景点失败: {city}, error={str(e)}")
        return []

def generate_plan_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            if response and response.content:
                return response.content
        except Exception as e:
            logger.error(f"LLM调用失败 (尝试 {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
    return None

@app.route('/api/generate_plan', methods=['POST'])
def generate_plan():
    try:
        data = request.get_json()
        destination = data.get('destination', '')
        days = data.get('days', '3')
        preference = data.get('preference', '')

        if not destination:
            return jsonify({'error': '请输入目的地'}), 400

        days_num = int(days)
        if days_num > 15:
            return jsonify({'error': '最多支持15天的行程规划'}), 400

        is_province = destination in provinces_data
        
        if is_province:
            province_cities = provinces_data[destination]
            selected_cities = province_cities[:min(days_num, len(province_cities))]
            
            if len(selected_cities) < days_num:
                repeat_cities = []
                while len(selected_cities) + len(repeat_cities) < days_num:
                    repeat_cities.extend(selected_cities)
                selected_cities.extend(repeat_cities[:days_num - len(selected_cities)])
            
            all_places = {}
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_city = {executor.submit(get_places, city): city for city in selected_cities}
                for future in as_completed(future_to_city):
                    city = future_to_city[future]
                    try:
                        places = future.result()
                        if places:
                            all_places[city] = places[:6]
                    except Exception as e:
                        logger.warning(f"获取{city}景点失败: {e}")
            
            places_info = ""
            if all_places:
                for city, places in all_places.items():
                    places_info += f"{city}：{', '.join(places)}\n"
            
            prompt = f"请为我设计一份{destination}{days}日游旅行计划，涵盖以下城市：{', '.join(selected_cities)}。\n"
            if places_info:
                prompt += f"\n各城市推荐景点：\n{places_info}\n"
            prompt += f"\n要求：\n\n"
            prompt += f"1. 将行程合理分配到{days}天，每天去不同的城市或地区\n"
            prompt += f"2. 每天详细的时间安排（以休闲为主，08:00后出发）\n"
            prompt += f"3. 每个城市的核心景点推荐（必须给出具体景点名称），包含门票价格、开放时间\n"
            prompt += f"4. 城市之间的交通路线和预计费用\n"
            prompt += f"5. 每个城市推荐的当地特色餐厅名称、特色菜品、人均消费\n"
            prompt += f"6. 每天的预算估算\n"
            prompt += f"7. 每个城市的住宿推荐\n"
            prompt += f"8. 实用的旅行小贴士\n"
            
            if preference:
                prompt += f"\n特别偏好：{preference}\n"

            prompt += "\n请直接输出HTML内容片段（不要包含<html><head><body>标签），使用<h2>-<h4>、<p>、<ul><li>、<strong>等标签。"
        else:
            places = get_places(destination)
            
            attractions_str = ""
            if places:
                attractions_str = f"（推荐景点：{', '.join(places[:8])}）"

            prompt = f"请为我设计一份{destination}{days}日游旅行计划{attractions_str}。要求：\n\n"
            prompt += f"1. 每天详细的时间安排（以休闲为主，08:00后出发），每天去不同的景点\n"
            prompt += f"2. 每个景点的详细介绍、门票价格、开放时间\n"
            prompt += f"3. 具体的交通路线和预计费用\n"
            prompt += f"4. 推荐的当地特色餐厅名称、特色菜品、人均消费\n"
            prompt += f"5. 每天的预算估算\n"
            prompt += f"6. 住宿推荐\n"
            prompt += f"7. 实用的旅行小贴士\n"
            
            if preference:
                prompt += f"\n特别偏好：{preference}\n"

            prompt += "\n请直接输出HTML内容片段（不要包含<html><head><body>标签），使用<h2>-<h4>、<p>、<ul><li>、<strong>等标签。"

        logger.info(f"开始生成攻略: {destination}, {days}天")
        plan_content = generate_plan_with_retry(prompt)
        
        if plan_content:
            logger.info(f"攻略生成成功: {destination}, 长度={len(plan_content)}")
            
            weather_data = None
            try:
                main_city = is_province and selected_cities[0] or destination
                geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={main_city}&count=1&language=zh&format=json"
                geo_response = requests.get(geo_url, timeout=5)
                if geo_response.ok:
                    geo_data = geo_response.json()
                    if geo_data.get('results') and len(geo_data['results']) > 0:
                        result = geo_data['results'][0]
                        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={result['latitude']}&longitude={result['longitude']}&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=Asia/Shanghai&forecast_days=7"
                        weather_response = requests.get(weather_url, timeout=5)
                        if weather_response.ok:
                            weather_data = {
                                'name': result['name'],
                                'latitude': result['latitude'],
                                'longitude': result['longitude'],
                                'daily': weather_response.json()['daily']
                            }
            except Exception as e:
                logger.warning(f"获取天气失败: {e}")
            
            return jsonify({'plan': plan_content, 'is_province': is_province, 'locations': [], 'weather': weather_data})
        else:
            logger.error(f"攻略生成失败: {destination}")
            return jsonify({'error': '生成攻略失败，请稍后重试'}), 500

    except Exception as e:
        logger.error(f"生成攻略异常: {str(e)}")
        return jsonify({'error': f'生成攻略失败: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)