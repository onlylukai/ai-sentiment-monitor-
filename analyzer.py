"""AI 舆情监控系统 - AI 分析模块"""

import os
from typing import Dict, List
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class SentimentAnalyzer:
    """情感分析器"""

    def __init__(self):
        self.api_key = LLM_API_KEY
        self.base_url = LLM_BASE_URL
        self.model = LLM_MODEL_NAME

        if HAS_OPENAI and self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        else:
            self.client = None
            print("⚠️ 警告：未配置 LLM API Key，使用基础分析模式")

    def analyze_sentiment(self, text: str) -> Dict:
        """分析文本情感"""
        if not self.client:
            return self._simple_analyze(text)

        try:
            prompt = f"""请分析以下文本的情感倾向，返回 JSON 格式：
            {{"sentiment": "positive/negative/neutral", "score": 0.0-1.0, "keywords": ["关键词 1","关键词 2"]}}

            文本：
            {text[:500]}"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是专业的情感分析助手"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=200,
            )

            result = response.choices[0].message.content

            # 解析 JSON
            import json
            import re
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return {
                    "score": float(data.get("score", 0.5)),
                    "label": data.get("sentiment", "neutral"),
                    "keywords": data.get("keywords", []),
                    "analysis": result,
                }

            return {
                "score": 0.5,
                "label": "neutral",
                "keywords": [],
                "analysis": result,
            }

        except Exception as e:
            print(f"AI 分析失败（已回退基础分析）：{e}")
            return self._simple_analyze(text)

    def _simple_analyze(self, text: str) -> Dict:
        """基础情感分析（无 AI 或 AI 失败时的兜底）"""
        positive_words = [
            "好", "优秀", "成功", "进步", "发展", "创新", "支持", "积极",
            "增长", "突破", "提升", "高质量", "赋能", "引领", "繁荣", "机遇",
            "促进", "推动", "深化", "升级", "领先", "红利", "成效",
        ]
        negative_words = [
            "失败", "风险", "危机", "下降", "亏损", "负面", "警告", "担忧",
            "挑战", "制约", "不足", "困难", "落后", "瓶颈", "乱象",
            "滥用", "造假", "泄密", "失控", "争议", "投诉", "乱象", "隐患",
        ]

        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)

        if pos_count > neg_count:
            score = min(1.0, 0.5 + (pos_count - neg_count) * 0.1)
            label = "positive"
        elif neg_count > pos_count:
            score = max(0.0, 0.5 - (neg_count - pos_count) * 0.1)
            label = "negative"
        else:
            score = 0.5
            label = "neutral"

        keywords = self._extract_keywords(text)

        return {
            "score": score,
            "label": label,
            "keywords": keywords,
            "analysis": f"基础分析：正面 {pos_count}，负面 {neg_count}",
        }

    # 中文停用词（最小集，避免把内容词过滤掉）
    _STOPWORDS = set("""
    的 了 在 是 和 与 及 等 也 都 就 而 于 为 以 从 向 对 被 把 这 那 有 无 个
    一 不 很 更 最 会 能 要 将 已 并 或 但 却 其 之 所 者 上 下 中 前 后 里 内 外
    什么 怎么 如何 我们 你们 他们 可以 因为 所以 如果 虽然 但是 以及 进行 通过
    对于 关于 其中 目前 已经 一个 一直 不是 成为 作为 表示 说明 相关 方面 工作
    内容 时间 地区 方式 系统 中国 全球 世界 国家 企业 行业 重要 大量 部分
    主要 全面 积极 大力 不断 持续 深入 广泛 进一步 实现 构建 加强 提升 建设
    服务 提供 支持 促进 推动 深化 完善 优化 开展 报告 文件 页面 搜索 阅读 更多
    缩写 编者按 引言 一门 一个 两个 三者 之一 之中 以上 以下 之间 之内 之后
    指出 强调 提出 强调 认为 表示 强调 强调 强调 强调 强调 强调 强调 强调
    """.split())

    @classmethod
    def _extract_keywords(cls, text: str, top_n: int = 8) -> List[str]:
        """jieba 分词 + 停用词过滤 + 词频排序，输出真实关键词"""
        import re
        from collections import Counter

        text = re.sub(r'[\d\s]+', ' ', text)

        try:
            import jieba
            tokens = [t.strip() for t in jieba.lcut(text) if t.strip()]
        except Exception:
            tokens = re.findall(r'[\u4e00-\u9fff]{2,4}', text)

        counter = Counter(
            t for t in tokens
            if len(t) >= 2
            and t not in cls._STOPWORDS
            and re.fullmatch(r'[\u4e00-\u9fff]{2,6}', t)
        )

        return [w for w, _ in counter.most_common(top_n)]

    def analyze_articles(self, articles: List[Dict]) -> List[Dict]:
        """批量分析文章"""
        results = []

        for article in articles:
            text = article.get("content", article.get("title", ""))
            sentiment = self.analyze_sentiment(text)

            article["sentiment_score"] = sentiment["score"]
            article["sentiment_label"] = sentiment["label"]
            article["keywords"] = ",".join(sentiment.get("keywords", []))

            results.append(article)

        return results

    def generate_report(self, topic: str, articles: List[Dict], stats: Dict) -> str:
        """生成分析报告"""
        if not self.client:
            return self._simple_report(topic, articles, stats)

        try:
            prompt = f"""请根据以下舆情数据生成分析报告，包含：
            1. 总体概述
            2. 情感分布
            3. 热点话题
            4. 风险提示
            5. 建议

            主题：{topic}
            文章数量：{stats.get('total', 0)}
            平均情感分数：{stats.get('avg_sentiment', 0):.2f}
            正面：{stats.get('positive', 0)}
            负面：{stats.get('negative', 0)}
            中性：{stats.get('neutral', 0)}

            最新文章：
            {chr(10).join([f"- {a['title']} ({a.get('sentiment_label', 'neutral')})" for a in articles[:10]])}
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是专业的舆情分析助手"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"AI 报告生成失败，已回退基础报告：{e}")
            return self._simple_report(topic, articles, stats)

    def _simple_report(self, topic: str, articles: List[Dict], stats: Dict) -> str:
        """简单报告"""
        report = f"""# 舆情分析报告

## 主题：{topic}

## 统计概览
- 文章总数：{stats.get('total', 0)}
- 平均情感分数：{stats.get('avg_sentiment', 0):.2f}
- 正面：{stats.get('positive', 0)} 篇 ({stats.get('positive', 0) / max(stats.get('total', 1), 1) * 100:.1f}%)
- 负面：{stats.get('negative', 0)} 篇 ({stats.get('negative', 0) / max(stats.get('total', 1), 1) * 100:.1f}%)
- 中性：{stats.get('neutral', 0)} 篇 ({stats.get('neutral', 0) / max(stats.get('total', 1), 1) * 100:.1f}%)

## 最新文章
{chr(10).join([f"- {a['title']} [{a.get('sentiment_label', 'neutral')}]" for a in articles[:10]])}

## 风险提示
- 情感分数低于 0.3 时触发预警
- 负面文章占比超过 30% 时重点关注
"""
        return report


if __name__ == "__main__":
    analyzer = SentimentAnalyzer()

    # 测试分析
    test_text = "AI 教育迎来重大突破，多家企业宣布加大投入，投资者看好市场前景。"
    result = analyzer.analyze_sentiment(test_text)

    print(f"情感分数：{result['score']:.2f}")
    print(f"情感标签：{result['label']}")
    print(f"关键词：{result['keywords']}")
    print(f"分析：{result['analysis']}")