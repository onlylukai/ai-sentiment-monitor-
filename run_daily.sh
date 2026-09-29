#!/bin/bash
# ============================================
# AI 舆情监控系统 - 每日定时任务
# ============================================
# 用法:
#   1. 直接运行一次:  ./run_daily.sh
#   2. 加入 crontab 每天早上 8 点跑:
#      crontab -e
#      0 8 * * * cd /path/to/my-ai-monitor && ./run_daily.sh >> output/cron.log 2>&1
# ============================================

set -e
cd "$(dirname "$0")"

TOPICS="${TOPICS:-人工智能 人工智能+教育 职业教育}"
LIMIT="${LIMIT:-8}"
DATE=$(date +%Y%m%d)

echo "" >> output/cron.log
echo "===== $(date '+%Y-%m-%d %H:%M:%S') 开始每日舆情扫描 =====" >> output/cron.log

mkdir -p data output output/reports

for topic in $TOPICS; do
    echo "--- 话题: $topic ---"
    python3 monitor.py -t "$topic" --once --limit "$LIMIT" 2>&1 | grep -v "Building prefix\|Loading model\|Dumping model\|Prefix dict" >> output/cron.log
    python3 report.py -t "$topic" -f markdown >> output/cron.log 2>&1
done

# 生成最新状态快照，方便一眼看结果
python3 status.py --all >> output/cron.log 2>&1

echo "===== 完成: 报告在 output/reports/ =====" >> output/cron.log
