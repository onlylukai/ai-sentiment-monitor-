#!/usr/bin/env python3
"""AI 舆情监控系统 - 报告生成"""

import argparse
import os
from datetime import datetime
from typing import Dict, List

from config import OUTPUT_DIR, REPORT_TEMPLATE
from database import init_db, get_recent_articles, get_stats, get_top_keywords
from analyzer import SentimentAnalyzer


def generate_report(topic: str, date: str = None, output_format: str = "markdown") -> str:
    """生成报告"""

    init_db()
    analyzer = SentimentAnalyzer()

    # 获取数据
    stats = get_stats(topic)
    articles = get_recent_articles(topic, limit=50)
    keywords = get_top_keywords(topic, limit=20)

    # 生成报告
    report = analyzer.generate_report(topic, articles, stats)

    # 保存报告
    if output_format == "markdown":
        return save_markdown_report(topic, date, report, stats, articles, keywords)
    elif output_format == "html":
        return save_html_report(topic, date, report, stats, articles, keywords)
    else:
        return report


def save_markdown_report(topic: str, date: str, report: str, stats: Dict, articles: List, keywords: List) -> str:
    """保存 Markdown 报告"""

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"{OUTPUT_DIR}/{topic}_{date or datetime.now().strftime('%Y%m%d')}.md"

    content = f"""# 舆情分析报告

**主题**: {topic}  
**日期**: {date or datetime.now().strftime('%Y-%m-%d')}  
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 统计概览

| 指标 | 数值 |
|------|------|
| 文章总数 | {stats.get('total', 0)} |
| 平均情感分 | {stats.get('avg_sentiment', 0):.2f} |
| 正面文章 | {stats.get('positive', 0)} ({stats.get('positive', 0) / max(stats.get('total', 1), 1) * 100:.1f}%) |
| 负面文章 | {stats.get('negative', 0)} ({stats.get('negative', 0) / max(stats.get('total', 1), 1) * 100:.1f}%) |
| 中性文章 | {stats.get('neutral', 0)} ({stats.get('neutral', 0) / max(stats.get('total', 1), 1) * 100:.1f}%) |

---

## 📰 最新舆情

{chr(10).join([f"- [{a['title']}]({a.get('url', '')}) - {a.get('sentiment_label', 'neutral')}" for a in articles[:10]])}

---

## 🔥 热词排行

| 排名 | 关键词 | 次数 |
|------|--------|------|
{chr(10).join([f"| {i} | {kw['keyword']} | {kw['count']} |" for i, kw in enumerate(keywords, 1)])}

---

## 📝 AI 分析

{report}

---

*报告由 AI 舆情监控系统自动生成*
"""

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 报告已保存：{filename}")
    return filename


def save_html_report(topic: str, date: str, report: str, stats: Dict, articles: List, keywords: List) -> str:
    """保存 HTML 报告"""

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"{OUTPUT_DIR}/{topic}_{date or datetime.now().strftime('%Y%m%d')}.html"

    content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>舆情分析报告 - {topic}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #1890ff; color: white; padding: 20px; border-radius: 8px; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 20px 0; }}
        .stat-card {{ background: #f0f0f0; padding: 15px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #1890ff; }}
        .article {{ padding: 10px; border-bottom: 1px solid #eee; }}
        .sentiment-positive {{ color: #52c41a; }}
        .sentiment-negative {{ color: #ff4d4f; }}
        .sentiment-neutral {{ color: #999; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>舆情分析报告</h1>
        <p>主题：{topic} | 日期：{date or datetime.now().strftime('%Y-%m-%d')}</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{stats.get('total', 0)}</div>
            <div>文章总数</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats.get('avg_sentiment', 0):.2f}</div>
            <div>平均情感</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats.get('positive', 0)}</div>
            <div>正面</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{stats.get('negative', 0)}</div>
            <div>负面</div>
        </div>
    </div>

    <h2>📰 最新舆情</h2>
    {''.join([f'<div class="article"><a href="{a.get(\"url\", \"\")}">{a["title"]}</a> <span class="sentiment-{a.get(\"sentiment_label\", \"neutral\")}">{a.get("sentiment_label", "neutral")}</span></div>' for a in articles[:10]])}

    <h2>🔥 热词排行</h2>
    <ul>
        {''.join([f'<li>{kw["keyword"]} ({kw["count"]} 次)</li>' for kw in keywords])}
    </ul>

    <h2>📝 AI 分析</h2>
    <div>{report}</div>
</body>
</html>"""

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 报告已保存：{filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(description="生成舆情报告")
    parser.add_argument("--topic", "-t", type=str, required=True, help="话题")
    parser.add_argument("--date", "-d", type=str, help="日期")
    parser.add_argument("--format", "-f", type=str, choices=["markdown", "html"], default="markdown")

    args = parser.parse_args()
    generate_report(args.topic, args.date, args.format)


if __name__ == "__main__":
    main()