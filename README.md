# AI 舆情监控系统 🔥

> 基于 AI 的多平台舆情监控与分析报告工具

[![GitHub stars](https://img.shields.io/github/stars/onlylukai/ai-sentiment-monitor.svg)](https://github.com/onlylukai/ai-sentiment-monitor/stargazers)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/onlylukai/ai-sentiment-monitor/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/downloads/)

---

## 🎯 项目简介

本项目是一个基于 AI 的舆情监控工具，可以：

1. **多平台采集** - 自动抓取微博、知乎、新闻等平台的舆情数据
2. **AI 情感分析** - 使用大模型分析文本情感倾向
3. **热词监控** - 实时追踪热点话题变化
4. **预警推送** - 异常波动微信通知
5. **报告生成** - 自动生成舆情分析报告

---

## 📦 功能特性

| 功能 | 说明 |
|------|------|
| 📰 新闻采集 | 自动抓取主流新闻平台 |
| 🐦 社交媒体 | 支持微博、知乎等平台 |
| 🤖 AI 分析 | 情感分析、关键词提取 |
| 📊 趋势监控 | 实时追踪舆情变化 |
| 🔔 智能预警 | 异常波动即时通知 |
| 📄 报告生成 | 自动生成分析报告 |

---

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────┐
│                   AI 舆情监控系统                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  数据采集    │ →  │  AI 分析    │ →  │  报告生成    │  │
│  │  (爬虫)      │    │  (大模型)   │    │  (Markdown)  │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                │                │              │
│         ↓                ↓                ↓              │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                  数据存储 (SQLite)                    │ │
│  └─────────────────────────────────────────────────────┘ │
│                          │                                │
│                          ↓                                │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                  微信通知推送                         │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/onlylukai/ai-sentiment-monitor.git
cd ai-sentiment-monitor
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

```bash
cp .env.example .env
# 编辑 .env 文件，填入 API Key
```

### 4. 运行

```bash
# 启动监控
python monitor.py --topic "AI 教育"

# 生成报告
python report.py --date 2026-09-28

# 查看状态
python status.py
```

---

## 📁 项目结构

```
ai-sentiment-monitor/
├── monitor.py          # 主监控程序
├── report.py           # 报告生成
├── status.py           # 状态查看
├── config.py           # 配置文件
├── crawler.py          # 爬虫模块
├── analyzer.py         # AI 分析模块
├── notifier.py         # 通知模块
├── database.py         # 数据库模块
├── requirements.txt    # Python 依赖
├── .env.example        # 环境变量模板
└── README.md           # 项目说明
```

---

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| 爬虫 | requests, beautifulsoup4 |
| AI | OpenAI API / 阿里百炼 |
| 存储 | SQLite3 |
| 通知 | WeChat Bot API |
| 报告 | Jinja2 模板 |

---

## 📊 使用示例

### 监控 AI 教育话题

```bash
python monitor.py --topic "AI 教育" --platforms news,weibo --interval 30
```

### 生成日报

```bash
python report.py --date 2026-09-28 --format markdown
```

### 设置预警

```bash
python monitor.py --alert-threshold 0.7 --topic "教育政策"
```

---

## 💰 商业应用

| 场景 | 客户 | 价格 |
|------|------|------|
| 品牌舆情监控 | 企业品牌方 | 2000-5000/月 |
| 政策影响分析 | 政府部门 | 5000-20000/月 |
| 竞品追踪 | 投资机构 | 1000-3000/月 |
| 教育舆情 | 学校/教育局 | 1000-5000/月 |

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 License

MIT License

---

**作者**: 老师  
**GitHub**: onlylukai  
**邮箱**: onlylukai@users.noreply.github.com