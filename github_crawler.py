"""GitHub 舆情爬虫模块

以 GitHub 平台本身作为舆情来源：
- 仓库热度（star/fork/issue 数）→ 关注度
- Issue 标题与正文 → 需求与吐槽
- Issue 评论 → 真实讨论舆情（最有价值的部分）

数据源：GitHub REST API（无需登录，无 token 限额 60 core / 10 search 每小时）
填了 GITHUB_TOKEN 后提升到 5000 次/小时。

用法:
    from github_crawler import GitHubCrawler
    c = GitHubCrawler()
    repos = c.search_repos("AI 教育", limit=5)
    articles = c.fetch_articles("人工智能", limit=10)
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Optional

import requests
from config import CRAWLER_TIMEOUT, CRAWLER_USER_AGENT

API_BASE = "https://api.github.com"


class GitHubCrawler:
    """GitHub 平台舆情爬虫"""

    # issue 正文里的 GitHub 界面噪声（相对时间、机器人通知等），分析前剔除
    NOISE_PATTERNS = (
        r'\d+\s*(天|天前|周|月|年|小时|分钟)\s*前?\s*[·.]*',
        r'\d+\s*day\w*\s+ago',
        r'\d+\s*week\w*\s+ago',
        r'\d+\s*month\w*\s+ago',
        r'\d+\s*year\w*\s+ago',
        r'On\s+\d+\s+day\w*\s+ago',
        r'\bago\b',
        r'已编辑\s*[·.]*',
        r'\[skip to: \w+\]',
        r'Copy link\s*[·.]*',
        r'Copy Markdown\s*[·.]*',
        r'https://url\.ibm\.com/[\w/?=&%.-]*',   # 邮件跟踪链接
        r'http[s]?://[\w./?=&%:-]*\?[a-z]+url=[\w./?=%-]*',
    )

    @classmethod
    def clean_text(cls, text: str) -> str:
        """去掉 GitHub 界面噪声与相对时间，只留真实讨论内容"""
        for pat in cls.NOISE_PATTERNS:
            text = re.sub(pat, ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'\s{2,}', ' ', text).strip()
        return text

    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN", "").strip()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CRAWLER_USER_AGENT,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        self._last_remaining = None
        self._last_url_bucket = "core"

    # ------------------------------------------------------------------
    # 基础请求
    # ------------------------------------------------------------------
    def _get(self, url: str, params: dict = None):
        """带限额感知的 GET。失败返回 (None, 错误信息)"""
        try:
            r = self.session.get(url, params=params, timeout=CRAWLER_TIMEOUT)
            remaining = r.headers.get("x-ratelimit-remaining")
            if remaining is not None:
                self._last_remaining = int(remaining)
            self._last_url_bucket = "search" if "search/" in url else "core"
            if r.status_code == 200:
                return r.json(), None
            if r.status_code == 403 and "rate limit" in (r.text or "").lower():
                reset = r.headers.get("x-ratelimit-reset", "?")
                return None, f"GitHub API 限额已用尽（剩 {remaining}），重置时间戳 {reset}"
            if r.status_code == 404:
                return None, f"404 未找到：{url}"
            return None, f"HTTP {r.status_code}"
        except Exception as e:
            return None, f"请求异常：{e}"

    def check_quota(self, needed: int = 10) -> bool:
        """额度检查。未登录仅 60 次/小时且与本机其他程序共享，很容易不够用。"""
        left = self.rate_left()
        core = left.get("core", -1)
        if core is None or core < needed:
            print(
                f"\n⚠️  GitHub API 额度不足（剩 {core}，需 {needed}）。\n"
                f"      未登录限制为 60 次/小时，且与本机其他调用共享。\n"
                f"      解决办法：在 .env 里配置 GITHUB_TOKEN 可提升到 5000 次/小时。\n"
                f"      申请地址：https://github.com/settings/tokens/new （无需勾选任何权限）"
            )
            return False
        return True

    def rate_left(self) -> Dict[str, int]:
        """查询剩余额度。

        注意：/rate_limit 端点本身消耗 core 额度，额度耗尽时它也返回 403，
        所以结果可能为空 —— 此时退回上一次真实请求响应头里的 remaining。
        """
        data, err = self._get(f"{API_BASE}/rate_limit")
        if not data:
            if err and "rate limit" in err.lower():
                return {"core": 0, "search": 10, "source": "exhausted"}
            return {"core": self._last_remaining if self._last_remaining is not None else -1}
        core = data.get("resources", {}).get("core", {})
        search = data.get("resources", {}).get("search", {})
        return {"core": core.get("remaining", -1), "search": search.get("remaining", -1)}

    # ------------------------------------------------------------------
    # 仓库
    # ------------------------------------------------------------------
    def search_repos(self, topic: str, limit: int = 10) -> List[Dict]:
        """按关键词搜仓库，按 star 排序"""
        words = [w.strip() for w in re.split(r'[\s,，、/]+', topic) if w.strip()]
        query = " ".join(words) if words else topic

        data, err = self._get(
            f"{API_BASE}/search/repositories",
            params={"q": query, "sort": "stars", "order": "desc", "per_page": min(limit, 30)},
        )
        if err:
            print(f"  搜索仓库失败：{err}")
            return []
        return data.get("items", [])[:limit]

    def repo_overview(self, full_name: str) -> Optional[Dict]:
        """仓库元数据"""
        data, err = self._get(f"{API_BASE}/repos/{full_name}")
        if err:
            print(f"  {full_name} 详情失败：{err}")
        return data

    # ------------------------------------------------------------------
    # Issue / 讨论
    # ------------------------------------------------------------------
    def repo_issues(self, full_name: str, limit: int = 10, state: str = "open") -> List[Dict]:
        """获取 issue 列表。默认按评论数排序 → 讨论最热烈的就是舆情热点。

        state: open / closed / all
        """
        out: List[Dict] = []
        for sort in ("comments", "updated"):
            data, err = self._get(
                f"{API_BASE}/repos/{full_name}/issues",
                params={"state": state, "sort": sort, "direction": "desc", "per_page": min(limit, 100)},
            )
            if err:
                print(f"  {full_name} issues 失败：{err}")
                continue
            for it in data or []:
                if "pull_request" in it:      # 排除 PR，只看 issue
                    continue
                out.append(it)
            break                             # 成功一次即可
        return out[:limit]

    def issue_comments(self, full_name: str, number: int, limit: int = 20) -> List[Dict]:
        """获取单个 issue 的评论（含正文，是舆情分析的核心素材）"""
        data, err = self._get(
            f"{API_BASE}/repos/{full_name}/issues/{number}/comments",
            params={"per_page": min(limit, 100), "sort": "created", "direction": "desc"},
        )
        if err:
            print(f"  {full_name}#{number} 评论失败：{err}")
            return []
        return (data or [])[:limit]

    # ------------------------------------------------------------------
    # 组装成统一的 article 结构（可直接喂给 SentimentAnalyzer）
    # ------------------------------------------------------------------
    def fetch_articles(
        self,
        topic: str,
        limit: int = 12,
        repos: Optional[List[str]] = None,
        issues_per_repo: int = 2,
        comments_per_issue: int = 2,
        check_quota: bool = True,
    ) -> List[Dict]:
        """主入口：搜仓库 → 取 issue → 取评论 → 输出统一结构的文章列表。

        repos 为 None 时自动按 topic 搜索；也可直接指定仓库名列表。
        """
        articles: List[Dict] = []

        if check_quota and not self.check_quota(needed=10):
            print("  已跳过 GitHub 采集（额度不足）")
            return articles

        meta_by_repo = {}
        if repos is None:
            # 搜索一次就够：返回里已含 star/fork/issue 数，不用逐个仓库再请求（省额度）
            found = self.search_repos(topic, limit=5)
            for r in found:
                meta_by_repo[r.get("full_name")] = r
            repos = [r["full_name"] for r in found if r.get("full_name")]
            print(f"  匹配仓库：{', '.join(repos)}")

        for repo in repos[:5]:
            if len(articles) >= limit:
                break

            # 1) 仓库热度本身也是一条舆情信号
            ov = meta_by_repo.get(repo)
            if ov and ov.get("stargazers_count") is not None:
                stars = ov["stargazers_count"]
                forks = ov.get("forks_count", 0)
                opens = ov.get("open_issues_count", 0)
                desc = (ov.get("description") or "").strip()
                articles.append({
                    "title": f"[仓库热度] {repo} ★{stars} forks={forks} 待解决 issues={opens}",
                    "content": desc or f"stars={stars} forks={forks} open_issues={opens}",
                    "source": "GitHub-仓库",
                    "url": ov.get("html_url", f"https://github.com/{repo}"),
                    "collected_at": datetime.now().isoformat(),
                    "topic": topic,
                    "_skip_sentiment": True,
                    "meta": {
                        "repo": repo,
                        "stars": stars,
                        "forks": forks,
                        "open_issues": opens,
                    },
                })

            # 2) 讨论最热烈的 issues
            for issue in self.repo_issues(repo, limit=issues_per_repo):
                if len(articles) >= limit:
                    break
                title = issue.get("title") or ""
                body = self.clean_text(issue.get("body") or "")
                if len(title) < 4:
                    continue

                num = issue.get("number")
                comments = self.issue_comments(repo, num, limit=comments_per_issue) if num else []
                comment_text = "\n".join(
                    self.clean_text(c.get("body") or "")[:500] for c in comments
                )
                content = "\n".join(x for x in [body[:800], comment_text] if x).strip()

                labels = ",".join(l.get("name", "") for l in issue.get("labels", []) if l.get("name"))
                articles.append({
                    "title": f"[{repo}] #{num} {title[:80]}",
                    "content": content or title,
                    "source": "GitHub-Issue",
                    "url": issue.get("html_url", f"https://github.com/{repo}/issues/{num}"),
                    "collected_at": datetime.now().isoformat(),
                    "topic": topic,
                    "meta": {
                        "repo": repo,
                        "number": num,
                        "state": issue.get("state"),
                        "comments": issue.get("comments"),
                        "labels": labels,
                    },
                })

        return articles[:limit]

    # ------------------------------------------------------------------
    # 单独取话题趋势（star 增速代理指标）
    # ------------------------------------------------------------------
    def trending(self, topic: str, limit: int = 10) -> List[Dict]:
        """近 3 个月新建的高星仓库 → 热度趋势"""
        words = [w.strip() for w in re.split(r'[\s,，、/]+', topic) if w.strip()]
        query = f"{' '.join(words)} created:>={datetime.now().strftime('%Y-%m-%d')} pushed:>{datetime.now().strftime('%Y-%m-01')}"
        data, err = self._get(
            f"{API_BASE}/search/repositories",
            params={"q": query, "sort": "stars", "order": "desc", "per_page": min(limit, 30)},
        )
        if err:
            print(f"  趋势查询失败：{err}")
            return []
        return data.get("items", [])[:limit]


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="GitHub 舆情爬虫")
    p.add_argument("--topic", "-t", default="人工智能")
    p.add_argument("--limit", "-l", type=int, default=8)
    p.add_argument("--repo", "-r", action="append", help="直接指定仓库（可多次）")
    a = p.parse_args()

    print(f"正在抓取 GitHub 舆情：{a.topic}")
    print(f"剩余额度：{GitHubCrawler().rate_left()}")
    arts = GitHubCrawler().fetch_articles(a.topic, limit=a.limit, repos=a.repo)
    print(f"\n抓取到 {len(arts)} 条")
    for i, x in enumerate(arts, 1):
        print(f"{i}. [{x['source']}] {x['title'][:70]}")
        print(f"   {x['url']}")
