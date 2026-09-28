#!/usr/bin/env python3
"""AI 舆情监控系统 - 状态查看"""

import argparse
from datetime import datetime
from database import init_db, get_stats, get_top_keywords, get_recent_articles


def show_status(topic: str):
    """显示监控状态"""

    init_db()
    stats = get_stats(topic)
    keywords = get_top_keywords(topic, 20)
    articles = get_recent_articles(topic, 10)

    print(f"\n{'=' * 50}")
    print(f"📊 舆情监控状态")
    print(f"{'=' * 50}")
    print(f"主题：{topic}")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    print(f"{'─' * 50}")
    print(f"📈 统计概览")
    print(f"{'─' * 50}")
    print(f"  文章总数：{stats.get('total', 0)}")
    print(f"  平均情感：{stats.get('avg_sentiment', 0):.2f}")
    print(f"  正面：{stats.get('positive', 0)} 篇")
    print(f"  负面：{stats.get('negative', 0)} 篇")
    print(f"  中性：{stats.get('neutral', 0)} 篇")
    print()

    if articles:
        print(f"{'─' * 50}")
        print(f"📰 最新文章")
        print(f"{'─' * 50}")
        for i, article in enumerate(articles, 1):
            sentiment = article.get('sentiment_label', 'neutral')
            emoji = {"positive": "✅", "negative": "❌", "neutral": "➡️"}.get(sentiment, "➡️")
            print(f"  {i}. {emoji} {article.get('title', '无标题')[:40]}")
            print(f"     来源：{article.get('source', '未知')} | {article.get('collected_at', '')[:10]}")
        print()

    if keywords:
        print(f"{'─' * 50}")
        print(f"🔥 热词排行")
        print(f"{'─' * 50}")
        for i, kw in enumerate(keywords, 1):
            bar = "█" * min(kw['count'], 20)
            print(f"  {i:2d}. {kw['keyword']:<10} {bar} {kw['count']}")
        print()

    print(f"{'=' * 50}")


def show_all_topics():
    """显示所有话题状态"""

    import sqlite3
    from config import DATABASE_PATH

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT DISTINCT topic FROM articles')
    topics = cursor.fetchall()

    print(f"\n{'=' * 50}")
    print(f"📊 所有监控话题")
    print(f"{'=' * 50}")

    for topic in topics:
        show_status(topic[0])

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="查看监控状态")
    parser.add_argument("--topic", "-t", type=str, help="指定话题")
    parser.add_argument("--all", action="store_true", help="显示所有话题")

    args = parser.parse_args()

    if args.all:
        show_all_topics()
    elif args.topic:
        show_status(args.topic)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()