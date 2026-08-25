# 金融市场信息聚合系统

一个实时聚合中国金融市场新闻和公告的 Web 应用，从多个权威数据源抓取信息，自动计算热度，并以可视化仪表盘展示。

## 功能特性

- **多源聚合**: 财联社、金十数据、华尔街见闻、巨潮资讯网、上交所、深交所、证监会、中国证券报、上海证券报、证券时报
- **实时更新**: 每30秒自动刷新，支持手动触发刷新
- **热度引擎**: 基于关键词匹配、时间衰减、来源权重等多维度计算每条信息的热度分值
- **可视化仪表盘**: 暗色主题界面，热度等级标识（爆/热/温/凉/冷），关键词云，数据源状态监控
- **搜索与筛选**: 按数据源、热度等级筛选，关键词搜索

## 快速启动

### Windows

双击 `run.bat` 即可，脚本会自动检查环境并安装依赖。

### 手动启动

```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用
python app.py
```

浏览器访问 http://127.0.0.1:5000

## 项目结构

```
fin_market_aggregator/
├── app.py                  # Flask 主应用，提供 API 和页面
├── config.py               # 配置（数据源、关键词、刷新间隔）
├── heat_engine.py          # 热度计算引擎
├── requirements.txt        # Python 依赖
├── run.bat                 # Windows 启动脚本
├── fetchers/               # 数据源抓取模块
│   ├── base.py             # 抓取基类
│   ├── cls_fetcher.py      # 财联社
│   ├── jin10_fetcher.py    # 金十数据
│   ├── wallstreetcn_fetcher.py  # 华尔街见闻
│   ├── cninfo_fetcher.py   # 巨潮资讯网
│   ├── exchange_fetcher.py # 交易所（上交所/深交所）
│   ├── csrc_fetcher.py     # 证监会
│   └── securities_fetcher.py  # 三大证券报
├── templates/
│   └── index.html          # 仪表盘页面
└── static/
    ├── css/style.css       # 样式
    └── js/main.js          # 前端逻辑
```

## API 接口

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 仪表盘页面 |
| `/api/news` | GET | 获取新闻列表（支持 source/level/search 参数） |
| `/api/status` | GET | 数据源状态 |
| `/api/keywords` | GET | 热门关键词统计 |
| `/api/refresh` | POST | 手动触发刷新 |
| `/api/heat_levels` | GET | 热度等级配置 |

## 热度计算规则

每条信息的热度分由以下因素综合计算：

1. **关键词匹配** (权重最高): 标题和内容匹配重大关键词 +15分/词，重要关键词 +8分/词
2. **时间衰减**: 5分钟内 +40分，15分钟内 +25分，30分钟内 +15分，以此递减
3. **来源权重**: 证监会 ×1.3，财联社/金十 ×1.2，华尔街见闻/交易所 ×1.1
4. **重要标记**: 来源标记为重要的信息额外 +25分

热度等级: 爆(≥80) / 热(≥50) / 温(≥30) / 凉(≥15) / 冷(<15)

## 技术栈

- **后端**: Python + Flask
- **数据抓取**: requests + BeautifulSoup4
- **定时任务**: threading + time
- **前端**: 原生 HTML/CSS/JavaScript（无框架依赖）

## 注意事项

- 部分数据源网站可能有反爬机制，如遇到数据获取失败，状态栏会显示红色标记
- 数据仅供信息参考，不构成投资建议
- 建议在网络稳定的环境下运行
