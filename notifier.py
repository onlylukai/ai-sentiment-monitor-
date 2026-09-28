"""AI 舆情监控系统 - 通知模块"""

import requests
from datetime import datetime
from typing import Dict
from config import WECHAT_BOT_WEBHOOK, ALERT_THRESHOLD


class Notifier:
    """通知发送器"""

    def __init__(self):
        self.webhook = WECHAT_BOT_WEBHOOK

    def send_alert(self, topic: str, stats: Dict, articles: list) -> bool:
        """发送预警通知"""
        if not self.webhook:
            print("⚠️ 未配置微信通知")
            return False

        # 检查是否需要预警
        if not self._should_alert(stats):
            return False

        # 构建消息
        message = self._build_alert_message(topic, stats, articles)

        # 发送到企业微信
        return self._send_wechat(message)

    def _should_alert(self, stats: Dict) -> bool:
        """判断是否需要预警"""
        total = stats.get("total", 0)
        if total == 0:
            return False

        # 负面占比超过 30%
        negative_ratio = stats.get("negative", 0) / total
        if negative_ratio > 0.3:
            return True

        # 平均情感分数低于阈值
        if stats.get("avg_sentiment", 0.5) < ALERT_THRESHOLD:
            return True

        # 情感波动大（标准差大）
        # 这里简化处理

        return False

    def _build_alert_message(self, topic: str, stats: Dict, articles: list) -> str:
        """构建预警消息"""
        total = stats.get("total", 0)
        negative = stats.get("negative", 0)
        positive = stats.get("positive", 0)
        avg = stats.get("avg_sentiment", 0)

        message = f"""🚨 舆情预警通知

主题：{topic}
时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

📊 数据统计：
• 文章总数：{total}
• 正面：{positive} ({positive / max(total, 1) * 100:.1f}%)
• 负面：{negative} ({negative / max(total, 1) * 100:.1f}%)
• 平均情感分：{avg:.2f}

⚠️ 预警原因："""

        # 判断预警原因
        reasons = []
        if negative / max(total, 1) > 0.3:
            reasons.append(f"负面占比 {negative / max(total, 1) * 100:.1f}% 超过 30%")
        if avg < ALERT_THRESHOLD:
            reasons.append(f"平均情感分 {avg:.2f} 低于阈值 {ALERT_THRESHOLD}")

        message += "\n".join([f"• {r}" for r in reasons]) if reasons else "• 综合判断"

        # 添加最新文章
        if articles:
            message += "\n\n📰 最新文章：\n"
            for i, article in enumerate(articles[:5], 1):
                sentiment = article.get("sentiment_label", "neutral")
                emoji = {"positive": "✅", "negative": "❌", "neutral": "➡️"}.get(sentiment, "➡️")
                message += f"{i}. {emoji} {article.get('title', '无标题')}\n"

        message += "\n---\n来自 AI 舆情监控系统"

        return message

    def _send_wechat(self, message: str) -> bool:
        """发送到企业微信"""
        try:
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": message
                }
            }

            response = requests.post(
                self.webhook,
                json=payload,
                timeout=10
            )

            result = response.json()
            if result.get("errcode") == 0:
                print("✅ 预警通知已发送")
                return True
            else:
                print(f"❌ 发送失败：{result}")
                return False

        except Exception as e:
            print(f"❌ 发送异常：{e}")
            return False

    def send_report(self, topic: str, report: str) -> bool:
        """发送报告"""
        if not self.webhook:
            return False

        message = f"📄 舆情分析报告\n\n{report[:2000]}"

        if len(report) > 2000:
            message += "\n\n... (内容过长，请查看完整报告)"

        return self._send_wechat(message)


if __name__ == "__main__":
    notifier = Notifier()

    # 测试发送
    test_stats = {
        "total": 100,
        "positive": 60,
        "negative": 25,
        "neutral": 15,
        "avg_sentiment": 0.65,
    }

    test_articles = [
        {"title": "AI 教育迎来重大突破", "sentiment_label": "positive"},
        {"title": "某教育公司暴雷", "sentiment_label": "negative"},
    ]

    if notifier._should_alert(test_stats):
        print("需要发送预警")
        notifier.send_alert("AI 教育", test_stats, test_articles)
    else:
        print("不需要预警")