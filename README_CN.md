# CS2 价格抓取器 + 交易机器人

[English](README.md) | **中文**

开源 CS2 饰品价格抓取器，内置**交易机器人**，与服务器同步运行。从 Steam 社区市场、Youpin（悠悠有品）、Buff163 和 Skinport 获取实时价格。检测跨平台套利机会，并生成针对 CS2 市场的投资信号。

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)](https://docker.com)

## 快速开始（任选其一）

### 方案 1：独立 EXE（最简单 — 无需 Python）

从 [Releases](https://github.com/juggperc/uupinfetch/releases) 下载并解压 `CS2PriceScraper.zip`，然后双击 `CS2PriceScraper.exe`。

- 在**系统托盘**中运行
- **自动打开**浏览器进入机器人界面
- 服务器 + 交易机器人自动启动
- 右键托盘图标：控制台、机器人界面、触发扫描、查看日志、退出

### 方案 2：一键启动（Windows）

```bat
git clone https://github.com/juggperc/uupinfetch.git
cd uupinfetch
start-easy.bat    :: 自动安装依赖、启动服务器、打开浏览器
```

**搞定。** 浏览器会自动打开交易机器人界面 `http://localhost:8000/bot`

### 方案 3：一键启动（Linux/Mac）

```bash
git clone https://github.com/juggperc/uupinfetch.git
cd uupinfetch
./start-easy.sh   # 自动安装依赖、启动服务器、打开浏览器
```

### 方案 4：Docker

```bash
docker compose up -d
```

然后打开 `http://localhost:8000/bot`

## 功能一览

### 交易机器人（自动启动）
机器人随服务器自动启动，持续扫描以下机会：

| 功能 | 说明 |
|---------|-------------|
| **套利扫描器** | 跨平台价格差（Steam vs Buff vs Youpin vs Skinport） |
| **箱子投资** | 掉落池轮换分析，预测囤货回报率 |
| **贴纸/胶囊** | Major 期间买入策略，3-6 个月后卖出 |
| **磨损套利** | 低磨损战痕皮肤被错误定价 |
| **市场洞察** | 实时市场动量和机会情报 |

### Web 界面
- **机器人控制台** (`/bot`) - 实时套利、投资信号、市场洞察
- **饰品搜索** (`/search`) - 浏览皮肤并查看价格图表
- **API 文档** (`/api/docs`) - 交互式 Swagger 文档
- **仪表盘** (`/dashboard`) - 服务器状态、API 快速测试

### REST API（开放 — 无需认证）
所有接口均开放，可直接接入你的交易机器人。

```python
import requests

BASE = "http://localhost:8000"

# 搜索饰品
r = requests.get(f"{BASE}/api/v1/items/search?q=AK-47")
for item in r.json()["items"]:
    print(f"{item['name']}: {item['price']} CNY")

# 获取套利机会
r = requests.get(f"{BASE}/api/v1/bot/arbitrage")
for opp in r.json():
    print(f"低价买入 {opp['item_name']} @ {opp['buy_price']} -> 高价卖出 @ {opp['sell_price']}")

# 获取投资建议
r = requests.get(f"{BASE}/api/v1/bot/recommendations")
for rec in r.json():
    print(f"{rec['item_name']}: 预期 +{rec['expected_roi_pct']}% 回报率")
```

## API 接口

### 价格数据
| 接口 | 说明 |
|----------|-------------|
| `GET /api/v1/health` | 健康检查 |
| `GET /api/v1/items/search?q=AK-47` | 跨平台搜索饰品 |
| `GET /api/v1/items/{id}` | 饰品详情与价格历史 |
| `GET /api/v1/items/popular` | 数据库中的热门饰品 |
| `GET /api/v1/categories` | 饰品分类/筛选 |

### 机器人智能
| 接口 | 说明 |
|----------|-------------|
| `GET /api/v1/bot/status` | 机器人运行状态 |
| `GET /api/v1/bot/arbitrage` | 实时套利机会 |
| `GET /api/v1/bot/recommendations` | 投资建议 |
| `GET /api/v1/bot/insights` | 市场洞察与情报 |
| `GET /api/v1/bot/stats` | 聚合机器人统计 |
| `POST /api/v1/bot/trigger-scan` | 手动触发扫描 |
| `GET /api/v1/bot/watchlist` | 价格预警关注列表 |
| `POST /api/v1/bot/watchlist` | 添加关注项 |
| `DELETE /api/v1/bot/watchlist/{id}` | 移除关注项 |
| `GET /api/v1/bot/history` | 每日机会历史 |
| `GET /api/v1/bot/export/arbitrage` | 套利数据 CSV 导出 |
| `GET /api/v1/bot/export/recommendations` | 建议数据 CSV 导出 |

## 交易机器人示例

见 `examples/` 目录中的现成机器人集成：

### `examples/basic_bot.py`
简单交易机器人，监控价格并检测套利：
```bash
python examples/basic_bot.py
```

### `examples/advanced_bot.py`
基于 SQLite 的机器人，含趋势分析、关注列表和预警：
```bash
python examples/advanced_bot.py
```

## 构建独立 EXE（Windows）

```bash
pip install -r requirements.txt
python build.py
```

输出：`dist/CS2PriceScraper/CS2PriceScraper.exe`（约 110 MB 文件夹，双击运行）

## 项目架构

```
app/
  main.py                 # FastAPI 入口 + 机器人启动器
  api/v1/
    endpoints.py          # 价格数据 API（开放）
    bot.py                # 机器人智能 API
    auth.py               # 可选用户认证
  services/
    bot_engine.py         # CS2 交易机器人引擎
    steam.py              # Steam 抓取器（公开，无需认证）
    youpin.py             # Youpin 抓取器（公开端点，搜索需认证）
    buff.py               # Buff 抓取器（需认证）
    skinport.py           # Skinport API 抓取器（公开，需 Brotli）
    scraper.py            # 后台价格抓取器
  models/                 # 数据库模型
  schemas/                # Pydantic 模式
launcher.py               # 系统托盘启动器（自动浏览器、服务器管理）
build.py                  # PyInstaller 构建脚本（独立 EXE）
examples/
  basic_bot.py            # 简单机器人示例
  advanced_bot.py         # 趋势分析机器人
templates/
  bot.html                # 交易机器人界面
  search.html             # 饰品搜索
  dashboard.html          # API 测试仪表盘
static/                   # CSS、JS、图片
data/                     # SQLite 数据库（自动创建）
```

## CS2 市场情报

机器人理解 CS2 特有的市场机制：

### 箱子投资逻辑
- **常见掉落箱子**（< 1 CNY）：每年 20-40% 增值，退出活跃掉落池后升值
- **活跃掉落箱子**（1-5 CNY）：大型更新期间 10-20% 涨幅
- **稀有箱子**（> 20 CNY）：保值稳定，适合长期持有

### 贴纸胶囊策略
- Major 期间**买入**胶囊（还在掉落时）
- Major 结束**3-6 个月后卖出**
- 历史回报率：近期 Major 50-200%

### 磨损/外观套利
- 低磨损战痕皮肤交易价格接近略磨
- 在 Buff163 检查具体磨损值寻找真正套利机会
- 图案编号对多普勒、渐变、表面淬火很重要

### 认证（可选）
API 默认开放。Skinport 无需认证即可使用。要解锁 Buff/Youpin 搜索：
1. 通过浏览器登录对应平台
2. 提取 cookies/session tokens
3. 添加到 `app/services/buff.py` 或 `app/services/youpin.py`

## 配置

复制 `.env.example` 为 `.env`：

```env
HOST=0.0.0.0
PORT=8000
DATABASE_URL=sqlite:///./data/cs2_scraper.db
ENABLE_YOUPIN=true
ENABLE_BUFF=true
ENABLE_SKINPORT=true
SCRAPE_INTERVAL_MINUTES=30
```

## 技术栈

- **后端**: FastAPI, SQLAlchemy, Pydantic, APScheduler
- **机器人引擎**: 异步市场扫描器，含 CS2 特定启发式算法
- **前端**: 简洁专业 UI, Chart.js, Jinja2
- **数据库**: SQLite（服务器 + 机器人共享数据）
- **抓取**: httpx 异步 HTTP 客户端

## 开源协议

MIT - 可自由用于你的交易机器人。

## 免责声明

本工具仅供教育和个人交易研究使用。请尊重所有交易平台的用户协议。使用风险自负。
