"""AI 舆情监控系统 - 数据库模块"""

import json
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional
from config import DATABASE_PATH


def get_db_path() -> str:
    """获取数据库路径并确保目录存在"""
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    return DATABASE_PATH


def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    # 创建文章表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            source TEXT,
            url TEXT UNIQUE,
            sentiment_score REAL,
            sentiment_label TEXT,
            keywords TEXT,
            collected_at TEXT NOT NULL,
            topic TEXT
        )
    ''')

    # 创建监控记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitor_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            article_count INTEGER,
            avg_sentiment REAL,
            alert_triggered INTEGER DEFAULT 0,
            details TEXT
        )
    ''')

    # 创建热词表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            count INTEGER NOT NULL,
            first_seen TEXT,
            last_seen TEXT,
            topic TEXT
        )
    ''')

    # 旧版本数据库补齐 meta 列
    try:
        cols = [r[1] for r in cursor.execute("PRAGMA table_info(articles)").fetchall()]
        if "meta" not in cols:
            cursor.execute("ALTER TABLE articles ADD COLUMN meta TEXT")
    except Exception:
        pass

    conn.commit()
    conn.close()


def save_article(article: Dict) -> int:
    """保存文章"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT OR REPLACE INTO articles
            (title, content, source, url, sentiment_score, sentiment_label, keywords, meta, collected_at, topic)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            article.get("title", ""),
            article.get("content", ""),
            article.get("source", ""),
            article.get("url", ""),
            article.get("sentiment_score", 0),
            article.get("sentiment_label", "neutral"),
            article.get("keywords", ""),
            json.dumps(article.get("meta") or {}, ensure_ascii=False) if article.get("meta") else None,
            article.get("collected_at", datetime.now().isoformat()),
            article.get("topic", "")
        ))

        # 同一 url 只保留最新一条（articles 表无唯一约束，OR REPLACE 不会去重）
        url, topic = article.get("url"), article.get("topic", "")
        if url:
            cursor.execute(
                "DELETE FROM articles WHERE url = ? AND topic = ? AND id != ?",
                (url, topic, cursor.lastrowid),
            )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def save_monitor_log(log: Dict) -> int:
    """保存监控日志"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO monitor_logs
            (topic, timestamp, article_count, avg_sentiment, alert_triggered, details)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            log.get("topic", ""),
            log.get("timestamp", datetime.now().isoformat()),
            log.get("article_count", 0),
            log.get("avg_sentiment", 0),
            log.get("alert_triggered", 0),
            log.get("details", "")
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_recent_articles(topic: str, limit: int = 50) -> List[Dict]:
    """获取最近的文章"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT * FROM articles
            WHERE topic = ?
            ORDER BY collected_at DESC
            LIMIT ?
        ''', (topic, limit))

        out = []
        for row in cursor.fetchall():
            d = dict(row)
            if d.get("meta"):
                try:
                    d["meta"] = json.loads(d["meta"])
                except Exception:
                    d["meta"] = {}
            out.append(d)
        return out
    finally:
        conn.close()


def get_article_count(topic: str) -> int:
    """获取文章总数"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT COUNT(*) FROM articles WHERE topic = ?', (topic,))
        return cursor.fetchone()[0]
    finally:
        conn.close()


def save_keyword(keyword: str, count: int, topic: str):
    """保存热词"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    try:
        # 按 (keyword, topic) 累加；keywords 表无唯一约束，用 SELECT 判重
        cursor.execute(
            'SELECT id FROM keywords WHERE keyword = ? AND topic = ?',
            (keyword, topic),
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                'UPDATE keywords SET count = count + ?, last_seen = ? WHERE id = ?',
                (count, now, row[0]),
            )
        else:
            cursor.execute(
                'INSERT INTO keywords (keyword, count, first_seen, last_seen, topic) '
                'VALUES (?, ?, ?, ?, ?)',
                (keyword, count, now, now, topic),
            )
        conn.commit()
    finally:
        conn.close()


def get_top_keywords(topic: str, limit: int = 20) -> List[Dict]:
    """获取热词排行"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT keyword, count FROM keywords
            WHERE topic = ?
            ORDER BY count DESC
            LIMIT ?
        ''', (topic, limit))

        out = []
        for row in cursor.fetchall():
            d = dict(row)
            if d.get("meta"):
                try:
                    d["meta"] = json.loads(d["meta"])
                except Exception:
                    d["meta"] = {}
            out.append(d)
        return out
    finally:
        conn.close()


def get_stats(topic: str) -> Dict:
    """获取统计信息"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT
                COUNT(*) as total,
                AVG(sentiment_score) as avg_sentiment,
                SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative,
                SUM(CASE WHEN sentiment_label = 'neutral' THEN 1 ELSE 0 END) as neutral
            FROM articles
            WHERE topic = ?
        ''', (topic,))

        row = cursor.fetchone()
        stats = dict(row)
        # SQLite 的 SUM/AVG 在空表时返回 NULL，统一转 0 避免下游格式化崩溃
        for k in ("total", "positive", "negative", "neutral", "avg_sentiment"):
            stats[k] = stats.get(k) or 0
        return stats
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"数据库初始化完成：{get_db_path()}")