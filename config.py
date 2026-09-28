"""AI 舆情监控系统 - 主配置文件"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# LLM 配置
LLM_API_KEY = ***"LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "qwen-plus")

# 微信通知配置
WECHAT_BOT_WEBHOOK = os.getenv("WECHAT_BOT_WEBHOOK", "")

# 监控配置
DEFAULT_INTERVAL = int(os.getenv("DEFAULT_INTERVAL", "30"))
ALERT_THRESHOLD = float(os.getenv("ALERT_THRESHOLD", "0.7"))
TOP_KEYWORDS_COUNT = int(os.getenv("TOP_KEYWORDS_COUNT", "20"))
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", "100"))

# 数据库配置
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/sentiment.db")

# 爬虫配置
CRAWLER_TIMEOUT = int(os.getenv("CRAWLER_TIMEOUT", "15"))
CRAWLER_RETRY = int(os.getenv("CRAWLER_RETRY", "3"))
CRAWLER_USER_AGENT = os.getenv(
    "CRAWLER_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)

# 报告配置
REPORT_TEMPLATE = os.getenv("REPORT_TEMPLATE", "templates/report.html")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output/reports")

# 支持的平台
PLATFORMS = {
    "news": ["新华网", "人民网", "新浪新闻"],
    "weibo": ["微博热搜"],
    "zhihu": ["知乎热榜"],
    "baidu": ["百度热搜"],
}