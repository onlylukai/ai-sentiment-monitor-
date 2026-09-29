"""AI 舆情监控系统 - 报告生成模块"""

import os
from datetime import datetime
from typing import Dict, List

from config import OUTPUT_DIR
from analyzer import SentimentAnalyzer
from database import init_db, get_stats, get_recent_articles, get_top_keywords


def generate_report(topic: str, date: str = None, output_format: str = "markdown") -> str:
    """生成报告"""
    init_db()
    analyzer = SentimentAnalyzer()

    stats = get_stats(topic)
    articles = get_recent_articles(topic, limit=50)
    keywords = get_top_keywords(topic, limit=20)

    # AI 分析（无 key 时走兜底）
    try:
        report = analyzer.generate_report(topic, articles, stats)
    except Exception as e:
        report = f"（AI 分析生成失败，已跳过）{e}"

    date = date or datetime.now().strftime("%Y%m%d")

    if output_format == "markdown":
        return save_markdown_report(topic, date, report, stats, articles, keywords)
    if output_format == "html":
        return save_html_report(topic, date, report, stats, articles, keywords)
    if output_format == "excel":
        return save_excel_report(topic, date, report, stats, articles, keywords)
    if output_format == "all":
        paths = [save_markdown_report(topic, date, report, stats, articles, keywords),
                 save_html_report(topic, date, report, stats, articles, keywords),
                 save_excel_report(topic, date, report, stats, articles, keywords)]
        return "\n".join(paths)
    return report


def _fmt_stats(stats: Dict) -> Dict:
    """把可能为 None 的统计值规整成可格式化类型"""
    total = stats.get("total") or 0
    avg = stats.get("avg_sentiment") or 0
    pos = stats.get("positive") or 0
    neg = stats.get("negative") or 0
    neu = stats.get("neutral") or 0
    denom = max(total, 1)
    return {
        "total": total,
        "avg": float(avg),
        "avg_str": f"{float(avg):.2f}",
        "pos": pos,
        "neg": neg,
        "neu": neu,
        "pos_pct": f"{pos / denom * 100:.1f}",
        "neg_pct": f"{neg / denom * 100:.1f}",
        "neu_pct": f"{neu / denom * 100:.1f}",
    }


def save_markdown_report(topic, date, report, stats, articles, keywords) -> str:
    """保存 Markdown 报告"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    s = _fmt_stats(stats)
    date_disp = datetime.now().strftime("%Y-%m-%d")

    # 列表先算好，避免 f-string 里嵌复杂表达式
    # 按数据源分组：GitHub 有专属版块，其余走通用列表
    gh = [a for a in articles if str(a.get("source", "")).startswith("GitHub")]
    others = [a for a in articles if not str(a.get("source", "")).startswith("GitHub")]

    art_lines = []
    for a in others[:10]:
        t = a.get("title") or ""
        u = a.get("url") or ""
        label = a.get("sentiment_label") or "neutral"
        art_lines.append(f"- [{t}]({u}) - {label}")

    repos_lines, issues_lines = [], []
    for a in gh:
        meta = a.get("meta") or {}
        if a.get("source") == "GitHub-仓库" and meta.get("stars") is not None:
            repos_lines.append(
                f"| [{meta.get('repo', '')}]({a.get('url', '')}) | "
                f"★{meta.get('stars', 0):,} | {meta.get('forks', 0):,} | {meta.get('open_issues', 0)} |"
            )
        elif a.get("source") == "GitHub-Issue":
            comments = (a.get("meta") or {}).get("comments")
            labels = (a.get("meta") or {}).get("labels") or "—"
            repos_lines.append("")
            issues_lines.append(
                f"- [{a.get('title', '')}]({a.get('url', '')}) "
                f"· 评论 {comments if comments is not None else '?'} 条 · 标签 {labels}"
            )
    # 仓库热度按 star 降序
    repos_lines = sorted([l for l in repos_lines if l],
                         key=lambda l: -int(l.split("|")[2].replace(",", "").replace("★", "").strip()))

    kw_lines = []
    for i, kw in enumerate(keywords, 1):
        kw_lines.append(f"| {i} | {kw.get('keyword', '')} | {kw.get('count', 0)} |")

    # GitHub 专属版块
    gh_block = ""
    if repos_lines or issues_lines:
        gh_block = "\n---\n\n## 🐙 GitHub 平台舆情\n\n"
        if repos_lines:
            gh_block += ("> 关注度与维持风险（open issues 越多越说明维护压力大）\n\n"
                         "| 仓库 | 星标 | Forks | 待解决 issues |\n|------|------|-------|--------------|\n"
                         + "\n".join(repos_lines) + "\n\n")
        if issues_lines:
            gh_block += ("### 讨论热点（按评论数排序）\n\n"
                         + "\n".join(issues_lines) + "\n\n")

    content = f"""# 舆情分析报告

**主题**: {topic}
**日期**: {date_disp}
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 统计概览

| 指标 | 数值 |
|------|------|
| 文章总数 | {s['total']} |
| 平均情感分 | {s['avg_str']} |
| 正面文章 | {s['pos']} ({s['pos_pct']}%) |
| 负面文章 | {s['neg']} ({s['neg_pct']}%) |
| 中性文章 | {s['neu']} ({s['neu_pct']}%) |

---

## 📰 最新舆情

{chr(10).join(art_lines) if art_lines else '_（暂无新闻/网页数据）_'}

{gh_block if (repos_lines or issues_lines) else ""}

---

## 🔥 热词排行

| 排名 | 关键词 | 次数 |
|------|--------|------|
{chr(10).join(kw_lines) if kw_lines else '| - | - | - |'}

---

## 📝 AI 分析

{report}

---

*报告由 AI 舆情监控系统自动生成*
"""

    filename = f"{OUTPUT_DIR}/{topic}_{date}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ 报告已保存：{filename}")
    return filename


def save_excel_report(topic, date, report, stats, articles, keywords) -> str:
    """导出 Excel 明细表（可直接用于工作台账/汇报附件）

    三个工作表：
    1. 统计概览 —— 一行汇总指标
    2. 文章明细 —— 逐篇标题/来源/链接/情感分/关键词
    3. 热词排行 —— 关键词频次
    """
    import pandas as pd
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    s = _fmt_stats(stats)
    date_disp = datetime.now().strftime("%Y-%m-%d %H:%M")

    df_stats = pd.DataFrame([{
        "主题": topic,
        "报告日期": datetime.now().strftime("%Y-%m-%d"),
        "生成时间": date_disp,
        "文章总数": s["total"],
        "平均情感分": float(s["avg"]),
        "正面文章": s["pos"],
        "正面占比": s["pos_pct"] + "%",
        "负面文章": s["neg"],
        "负面占比": s["neg_pct"] + "%",
        "中性文章": s["neu"],
        "中性占比": s["neu_pct"] + "%",
        "预警触发": "是（平均情感 < 0.3）" if float(s["avg"]) < 0.3 else "否",
    }])

    rows = []
    for a in articles:
        meta = a.get("meta") or {}
        if a.get("source") == "GitHub-仓库":
            content = (f"星标 {meta.get('stars', 0)} | Forks {meta.get('forks', 0)} "
                       f"| 待解决 issues {meta.get('open_issues', 0)}")
        elif a.get("source") == "GitHub-Issue":
            content = (f"评论 {meta.get('comments')} 条 | 标签 {meta.get('labels', '—')}\n"
                       f"{a.get('content') or ''}").strip()
        else:
            content = a.get("content") or ""
        rows.append({
            "来源平台": a.get("source") or "",
            "标题": a.get("title") or "",
            "链接": a.get("url") or "",
            "情感分": a.get("sentiment_score") if a.get("sentiment_score") is not None else "",
            "情感标签": a.get("sentiment_label") or "",
            "关键词": ", ".join(a.get("keywords") or []),
            "采集时间": (a.get("collected_at") or "")[:19],
            "正文摘要": content[:500],
        })
    df_articles = pd.DataFrame(rows)
    if df_articles.empty:
        df_articles = pd.DataFrame(columns=["来源平台", "标题", "链接", "情感分", "情感标签", "关键词", "采集时间", "正文摘要"])

    df_kw = pd.DataFrame([
        {"排名": i, "关键词": kw.get("keyword", ""), "出现次数": kw.get("count", 0)}
        for i, kw in enumerate(keywords, 1)
    ])
    if df_kw.empty:
        df_kw = pd.DataFrame(columns=["排名", "关键词", "出现次数"])

    df_report = pd.DataFrame({"AI 综合分析": [report]})

    filename = f"{OUTPUT_DIR}/{topic}_{date}.xlsx"
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        df_stats.to_excel(writer, sheet_name="统计概览", index=False)
        df_articles.to_excel(writer, sheet_name="文章明细", index=False)
        df_kw.to_excel(writer, sheet_name="热词排行", index=False)
        df_report.to_excel(writer, sheet_name="AI综合分析", index=False)

        # 列宽微调，避免交付时列被压成 ###
        for name, widths in {
            "统计概览": [16] * 12,
            "文章明细": [18, 40, 45, 8, 10, 28, 20, 60],
            "热词排行": [6, 24, 10],
            "AI综合分析": [110],
        }.items():
            ws = writer.sheets[name]
            from openpyxl.utils import get_column_letter
            from openpyxl.styles import Alignment
            for idx, w in enumerate(widths, 1):
                ws.column_dimensions[get_column_letter(idx)].width = w
            for row in ws.iter_rows():
                for cell in row:
                    cell.alignment = Alignment(wrap_text=True, vertical="top")

    print(f"✅ Excel 已保存：{filename}（{len(df_articles)} 篇文章，{len(df_kw)} 个热词）")
    return filename


def save_html_report(topic, date, report, stats, articles, keywords) -> str:
    """保存 HTML 报告"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    s = _fmt_stats(stats)
    date_disp = datetime.now().strftime("%Y-%m-%d")

    art_items = []
    for a in articles[:10]:
        u = a.get("url") or "#"
        t = a.get("title") or ""
        label = a.get("sentiment_label") or "neutral"
        art_items.append(
            f'<div class="article"><a href="{u}">{t}</a> '
            f'<span class="sentiment-{label}">{label}</span></div>'
        )

    kw_items = [
        f'<li>{kw.get("keyword", "")} ({kw.get("count", 0)} 次)</li>'
        for kw in keywords
    ]

    content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>舆情分析报告 - {topic}</title>
    <style>
        body {{ font-family: "PingFang SC", "Microsoft YaHei", Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f6fa; color: #333; }}
        .header {{ background: #1890ff; color: white; padding: 24px; border-radius: 8px; }}
        .header h1 {{ margin: 0 0 8px; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 20px 0; }}
        .stat-card {{ background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #1890ff; }}
        .article {{ padding: 10px; background: white; border-bottom: 1px solid #eee; }}
        .article a {{ color: #1890ff; text-decoration: none; }}
        .sentiment-positive {{ color: #52c41a; font-weight: bold; }}
        .sentiment-negative {{ color: #ff4d4f; font-weight: bold; }}
        .sentiment-neutral {{ color: #999; }}
        .ai-box {{ background: white; padding: 16px; border-radius: 8px; white-space: pre-wrap; line-height: 1.7; }}
        h2 {{ color: #333; border-left: 4px solid #1890ff; padding-left: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>舆情分析报告</h1>
        <p>主题：{topic} | 日期：{date_disp}</p>
    </div>

    <div class="stats">
        <div class="stat-card"><div class="stat-value">{s['total']}</div><div>文章总数</div></div>
        <div class="stat-card"><div class="stat-value">{s['avg_str']}</div><div>平均情感</div></div>
        <div class="stat-card"><div class="stat-value">{s['pos']}</div><div>正面</div></div>
        <div class="stat-card"><div class="stat-value">{s['neg']}</div><div>负面</div></div>
    </div>

    <h2>📰 最新舆情</h2>
    {''.join(art_items) if art_items else '<div class="article">（暂无数据）</div>'}

    <h2>🔥 热词排行</h2>
    <ul>{''.join(kw_items) if kw_items else '<li>（暂无数据）</li>'}</ul>

    <h2>📝 AI 分析</h2>
    <div class="ai-box">{report}</div>
</body>
</html>"""

    filename = f"{OUTPUT_DIR}/{topic}_{date}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ 报告已保存：{filename}")
    return filename


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AI 舆情监控系统 - 报告生成")
    parser.add_argument("--topic", "-t", type=str, required=True, help="监控话题")
    parser.add_argument("--date", "-d", type=str, default=None, help="报告日期 YYYY-MM-DD")
    parser.add_argument("--format", "-f", type=str, default="markdown",
                        choices=["markdown", "html", "excel", "all"],
                        help="markdown / html / excel / all（三种全出）")
    args = parser.parse_args()

    try:
        generate_report(args.topic, args.date, args.format)
    except Exception as e:
        print(f"报告生成失败：{e}")
        raise
