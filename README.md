# 🌍 旅游顾问小助手

一款基于 Flask 和 AI 的智能旅游行程规划助手，支持输入目的地和游玩天数生成个性化旅游攻略，包含天气查询、地图查看等功能。

## ✨ 功能特色

- 📝 **智能攻略生成**：输入目的地和天数，AI 自动生成详细的旅游攻略
- 🏙️ **多城市规划**：支持省份级别的多城市行程规划（如云南、四川等）
- 🌤️ **天气查询**：查询目的地未来7天天气预报
- 🗺️ **地图查看**：搜索地点，查看周边景点、美食、酒店
- 📜 **历史记录**：保存和管理历史行程记录
- ⚙️ **个性化设置**：主题切换、通知设置、数据管理

## 🛠️ 技术栈

- **后端框架**：Flask 3.1.3
- **AI模型**：Kimi (kimi-k2.7-code-highspeed)
- **地图服务**：高德地图API
- **天气服务**：Open-Meteo API
- **前端**：HTML5 + CSS3 + JavaScript

## 📁 项目结构

```
实验1/
├── app.py                 # Flask后端应用
├── templates/
│   └── travel_assistant.html  # 前端页面
├── travel_env/            # Python虚拟环境
└── README.md              # 项目说明文档
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 已安装 Flask、requests、langchain_openai 等依赖

### 启动方式

1. **激活虚拟环境**（推荐）

```bash
# Windows
e:\FDE-training\7.15旅行规划\实验1\travel_env\Scripts\activate

# 使用虚拟环境启动
e:\FDE-training\7.15旅行规划\实验1\travel_env\python.exe e:\FDE-training\7.15旅行规划\实验1\app.py
```

2. **直接启动**

```bash
python app.py
```

3. **访问应用**

打开浏览器访问：http://127.0.0.1:5000

## 📖 使用指南

### 1. 生成旅游攻略

1. 在首页或「生成攻略」标签页输入目的地（支持城市或省份）
2. 选择游玩天数（1-15天）
3. 可选：设置偏好（如休闲、亲子、美食等）
4. 点击「生成攻略」按钮

### 2. 多城市行程规划

输入省份名称（如云南、四川、浙江等），系统会自动规划多个城市的行程：

- 云南：昆明 → 大理 → 丽江 → 香格里拉 → 西双版纳
- 四川：成都 → 九寨沟 → 都江堰 → 青城山 → 乐山

### 3. 地图查看

1. 在搜索框输入地点名称（如：故宫、西湖）
2. 点击搜索，地图定位到该地点
3. 自动显示周边景点列表
4. 点击列表中的景点可切换地图焦点

### 4. 天气查询

1. 进入「天气查询」标签页
2. 输入城市名称
3. 点击查询，显示未来7天天气预报

## 🔌 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页 |
| `/api/generate_plan` | POST | 生成旅游攻略 |
| `/api/weather` | GET | 查询天气 |
| `/api/search_places` | GET | 搜索景点 |
| `/api/geocode` | GET | 地理编码 |
| `/api/place_detail` | GET | 地点详情 |
| `/api/search_around` | GET | 周边搜索 |

### 示例请求

**生成攻略**
```bash
POST /api/generate_plan
Content-Type: application/json

{
    "destination": "云南",
    "days": "5",
    "preference": "休闲"
}
```

**查询天气**
```bash
GET /api/weather?city=北京
```

**周边搜索**
```bash
GET /api/search_around?location=116.404,39.915&radius=2000&keywords=景点
```

## ⚙️ 配置说明

### 依赖安装

```bash
pip install -r requirements.txt
```

### API Key 配置

在 `app.py` 中配置以下API Key：

| 服务 | 配置变量 | 获取地址 |
|------|----------|----------|
| 高德地图 | `AMAP_KEY` | https://lbs.amap.com/ |
| 和风天气 | `QWEATHER_API_KEY` | https://dev.qweather.com/ |
| Kimi AI | `api_key` | https://platform.moonshot.cn/ |

### 缓存设置

- 景点数据缓存时间：1小时
- 支持多线程并行获取景点数据

## 📝 注意事项

1. **攻略生成时间**：根据目的地和天数不同，生成时间可能需要10-40秒
2. **网络要求**：需要联网访问高德地图API和Kimi模型
3. **浏览器要求**：建议使用 Chrome、Edge 等现代浏览器
4. **地图功能**：需要允许浏览器定位权限

## 🐛 常见问题

### Q: 生成攻略失败怎么办？
A: 请检查网络连接，或稍后重试。攻略生成涉及多个API调用，可能受网络影响。

### Q: 地图显示空白？
A: 请确保网络正常，高德地图API需要联网加载。

### Q: 某些城市无法搜索到？
A: 目前支持中国大陆主要城市和省份，部分偏远地区可能数据有限。

## 📄 许可证

MIT License

## 📧 联系方式

如有问题或建议，请联系开发者。
