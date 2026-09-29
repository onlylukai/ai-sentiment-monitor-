#!/usr/bin/env python3
"""AI 舆情监控系统 - 主程序"""

import argparse
import sys
from datetime import datetime
from typing import List, Dict

from config import DEFAULT_INTERVAL, ALERT_THRESHOLD, TOP_KEYWORDS_COUNT, MAX_ARTICLES
from database import init_db, save_article, save_monitor_log, get_recent_articles, get_stats, save_keyword, get_top_keywords
from crawler import Crawler
from analyzer import SentimentAnalyzer
from notifier import Notifier


def monitor_topic(topic: str, interval: int = None, platforms: list = None, limit: int = None):
    """监控指定话题"""

    init_db()
    crawler = Crawler()
    analyzer = SentimentAnalyzer()
    notifier = Notifier()

    print(f"🚀 开始监控话题：{topic}")
    print(f"⏰ 监控间隔：{interval or DEFAULT_INTERVAL} 分钟")
    print("-" * 50)

    while True:
        try:
            # 1. 采集数据
            print(f"\n📡 {datetime.now().strftime('%H:%M:%S')} - 采集数据...")
            articles = crawler.fetch_news(topic, limit=limit or MAX_ARTICLES)
            print(f"   采集到 {len(articles)} 篇文章")

            # 2. 分析情感
            print("🤖 分析情感...")
            articles = analyzer.analyze_articles(articles)

            # 3. 保存数据
            print("💾 保存数据...")
            for article in articles:
                save_article(article)

                # 保存关键词
                if article.get("keywords"):
                    for kw in article["keywords"].split(","):
                        if kw.strip():
                            save_keyword(kw.strip(), 1, topic)

            # 4. 获取统计
            stats = get_stats(topic)
            print(f"📊 统计：总计 {stats['total']} 篇，平均情感 {stats.get('avg_sentiment', 0):.2f}")

            # 5. 检查预警
            if notifier._should_alert(stats):
                print("⚠️ 触发预警！")
                notifier.send_alert(topic, stats, articles[:5])

            # 6. 保存监控日志
            save_monitor_log({
                "topic": topic,
                "timestamp": datetime.now().isoformat(),
                "article_count": len(articles),
                "avg_sentiment": stats.get("avg_sentiment", 0),
                "alert_triggered": 1 if notifier._should_alert(stats) else 0,
                "details": f"采集 {len(articles)} 篇",
            })

            # 7. 显示热词
            keywords = get_top_keywords(topic, TOP_KEYWORDS_COUNT)
            if keywords:
                print("\n🔥 热词排行：")
                for i, kw in enumerate(keywords[:10], 1):
                    print(f"   {i}. {kw['keyword']} ({kw['count']} 次)")

            print("\n" + "=" * 50)

            # 等待下一次监控
            import time
            wait_minutes = interval or DEFAULT_INTERVAL
            print(f"⏳ 等待 {wait_minutes} 分钟后继续监控...")
            time.sleep(wait_minutes * 60)

        except KeyboardInterrupt:
            print("\n\n👋 监控已停止")
            break
        except Exception as e:
            print(f"❌ 监控异常：{e}")
            import time
            time.sleep(60)


def run_once(topic: str, limit: int = None):
    """单次运行"""
    init_db()
    crawler = Crawler()
    analyzer = SentimentAnalyzer()
    notifier = Notifier()

    print(f"🚀 单次监控话题：{topic}")
    print("-" * 50)

    # 1. 采集数据
    print("📡 采集数据...")
    articles = crawler.fetch_news(topic, limit=limit or MAX_ARTICLES)
    print(f"   采集到 {len(articles)} 篇文章")

    # 2. 分析情感
    print("🤖 分析情感...")
    articles = analyzer.analyze_articles(articles)

    # 3. 保存数据
    print("💾 保存数据...")
    for article in articles:
        save_article(article)
        if article.get("keywords"):
            for kw in article["keywords"].split(","):
                if kw.strip():
                    save_keyword(kw.strip(), 1, topic)

    # 4. 统计
    stats = get_stats(topic)
    print(f"\n📊 统计结果：")
    print(f"   总计：{stats['total']} 篇")
    avg = stats.get('avg_sentiment') or 0
    print(f"   平均情感：{float(avg):.2f}")
    print(f"   正面：{stats.get('positive', 0)} 篇")
    print(f"   负面：{stats.get('negative', 0)} 篇")
    print(f"   中性：{stats.get('neutral', 0)} 篇")

    # 5. 热词
    keywords = get_top_keywords(topic, TOP_KEYWORDS_COUNT)
    if keywords:
        print(f"\n🔥 热词排行：")
        for i, kw in enumerate(keywords[:10], 1):
            print(f"   {i}. {kw['keyword']} ({kw['count']} 次)")

    # 6. 检查预警
    if notifier._should_alert(stats):
        print(f"\n⚠️ 预警！")
        notifier.send_alert(topic, stats, articles[:5])

    print("\n✅ 单次监控完成")


def main():
    parser = argparse.ArgumentParser(description="AI 舆情监控系统")
    parser.add_argument("--topic", "-t", type=str, required=True, help="监控话题")
    parser.add_argument("--interval", "-i", type=int, default=DEFAULT_INTERVAL, help="监控间隔（分钟）")
    parser.add_argument("--once", action="store_true", help="单次运行")
    parser.add_argument("--limit", "-l", type=int, default=MAX_ARTICLES, help="最大文章数")

    args = parser.parse_args()

    if args.once:
        run_once(args.topic, args.limit)
    else:
        monitor_topic(args.topic, args.interval, limit=args.limit)


if __name__ == "__main__":
    main()