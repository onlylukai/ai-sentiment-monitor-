"""AI 舆情监控系统 - 爬虫模块"""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
from config import CRAWLER_TIMEOUT, CRAWLER_RETRY, CRAWLER_USER_AGENT


class Crawler:
    """舆情爬虫"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CRAWLER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })

    def fetch_news(self, topic: str, limit: int = 20) -> List[Dict]:
        """抓取新闻"""
        articles = []

        # Bing 搜索（主力源，稳定可抓）
        try:
            news = self._fetch_bing(topic, limit)
            articles.extend(news)
        except Exception as e:
            print(f"Bing 搜索抓取失败：{e}")

        # 新华网（JS 渲染页面，多数情况抓不到，保留兼底）
        try:
            news = self._fetch_xinhua(topic, limit)
            articles.extend(news)
        except Exception as e:
            print(f"新华网抓取失败：{e}")

        # 人民网（SPA 页面，多数情况抓不到，保留兼底）
        try:
            news = self._fetch_people(topic, limit)
            articles.extend(news)
        except Exception as e:
            print(f"人民网抓取失败：{e}")

        return articles[:limit]

    # 百科/文档/答问类站点：对舆情监控无意义，过滤掉
    # 词典 / 问答 / 文档搬运站：对舆情监控没有价值，全部过滤
    EXCLUDE_DOMAINS = (
        "baike.baidu.com", "zhidao.baidu.com", "baijiahao.baidu.com",
        "www.zhihu.com", "m.zhihu.com", "zhuanlan.zhihu.com",
        "hanyuguoxue.com", "hgcha.com", "chazidian.com", "gushici.net",
        "guoxuemao.com", "cidianwang.com", "cidian.55088.com", "hanwu.cn",
        "xuehu.cn", "docin.com", "book118.com", "taodocs.com", "doc88.com",
        "360doc.com", "renrendoc.com", "haokan.baidu.com", "ishare.cn",
        "max.book118.com", "www.docin.com", "m.book118.com",
        "www.toutiao.com/article", "www.toutiao.com/zixun",
    )

    def _split_topics(self, topic: str) -> List[str]:
        """把 "人工智能 教育 政策" 拆成独立子话题，逐个查询。

        单个连贯词在 Bing 上召回质量远高于多词 AND 查询
        （多词 AND 会被词典/问答站刷版）。
        """
        return [w.strip() for w in re.split(r'[\s,，、/]+', topic) if w.strip()]

    def _query(self, topic: str) -> str:
        """规整单个查询词，去掉多余空白"""
        return re.sub(r'\s+', ' ', topic.strip())

    def _fetch_bing(self, topic: str, limit: int) -> List[Dict]:
        """抓取 Bing 搜索结果（主数据源）"""
        import urllib.parse
        subs = self._split_topics(topic)
        # 多个子话题时均分额度，逐个查询后合并
        per = max(1, limit // max(len(subs), 1))
        all_items = []
        for sub in subs[:6]:  # 最多 6 个子话题
            sub_url = (
                f"https://www.bing.com/search?q={urllib.parse.quote(self._query(sub))}"
                "&setlang=zh-Hans&cc=CN"
            )
            try:
                resp = self._request(sub_url)
                if resp:
                    all_items.append(BeautifulSoup(resp.text, 'lxml'))
            except Exception as e:
                print(f"  子话题「{sub}」抓取失败：{e}")

        if not all_items:
            return []

        articles = []
        seen = set()

        for soup in all_items:
            for item in soup.select('li.b_algo'):
                # Bing 的 b_algo 里第一个 <a> 是域名徽章，真正的标题在 <h2> 内
                h2 = item.find('h2')
                a = h2.find('a') if h2 else item.select_one('h2 a')
                if not a:
                    continue
                title = a.get_text(strip=True)
                link = a.get('href')

                # 清理标题里的面包屑分隔符与省略号
                for sep in ("\u203a", "›"):
                    if sep in title:
                        title = title.split(sep)[-1].strip()
                title = title.replace("\u2026", "").replace(" ...", "").strip()
                if len(title) < 6 or not link:
                    continue

                # 去重 + 过滤百科/文档站点
                if link in seen or any(d in link for d in self.EXCLUDE_DOMAINS):
                    continue

                p = item.find('p')
                snippet = p.get_text(strip=True) if p else ""
                snippet = re.sub(r'\s*阅读更多\s*$', '', snippet)

                seen.add(link)
                articles.append({
                    "title": title,
                    "content": snippet,
                    "source": "Bing",
                    "url": link,
                    "collected_at": datetime.now().isoformat(),
                    "topic": topic,
                })

                if len(articles) >= limit:
                    break

        return articles

    def _fetch_xinhua(self, topic: str, limit: int) -> List[Dict]:
        """抓取新华网"""
        url = f"http://www.news.cn/search?keyword={topic}"
        response = self._request(url)

        if not response:
            return []

        soup = BeautifulSoup(response.text, 'lxml')
        articles = []

        for item in soup.select('.content li a'):
            title = item.get_text(strip=True)
            link = item.get('href')

            if title and link:
                if link.startswith('/'):
                    link = f"http://www.news.cn{link}"

                articles.append({
                    "title": title,
                    "content": "",
                    "source": "新华网",
                    "url": link,
                    "collected_at": datetime.now().isoformat(),
                    "topic": topic,
                })

                if len(articles) >= limit:
                    break

        return articles

    def _fetch_people(self, topic: str, limit: int) -> List[Dict]:
        """抓取人民网"""
        url = f"http://search.people.cn/s/?keyword={topic}"
        response = self._request(url)

        if not response:
            return []

        soup = BeautifulSoup(response.text, 'lxml')
        articles = []

        for item in soup.select('.result-list li a'):
            title = item.get_text(strip=True)
            link = item.get('href')

            if title and link:
                if link.startswith('/'):
                    link = f"http://www.people.com.cn{link}"

                articles.append({
                    "title": title,
                    "content": "",
                    "source": "人民网",
                    "url": link,
                    "collected_at": datetime.now().isoformat(),
                    "topic": topic,
                })

                if len(articles) >= limit:
                    break

        return articles

    def fetch_content(self, url: str) -> str:
        """抓取文章内容"""
        response = self._request(url)
        if not response:
            return ""

        soup = BeautifulSoup(response.text, 'lxml')

        # 移除不需要的标签
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        # 提取正文
        content = soup.get_text(separator='\n', strip=True)

        # 清理空白
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        return '\n'.join(lines[:100])  # 限制长度

    def _request(self, url: str, retries: int = None) -> requests.Response:
        """发送请求"""
        if retries is None:
            retries = CRAWLER_RETRY

        for i in range(retries):
            try:
                response = self.session.get(url, timeout=CRAWLER_TIMEOUT)
                response.encoding = response.apparent_encoding
                return response
            except Exception as e:
                if i == retries - 1:
                    print(f"请求失败：{url} - {e}")
                    return None

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """通用搜索"""
        # 使用百度热搜
        url = f"http://www.baidu.com/s?wd={query}"
        response = self._request(url)

        if not response:
            return []

        soup = BeautifulSoup(response.text, 'lxml')
        results = []

        for item in soup.select('.result h3 a')[:limit]:
            title = item.get_text(strip=True)
            link = item.get('href')

            if title and link:
                results.append({
                    "title": title,
                    "content": "",
                    "source": "百度搜索",
                    "url": link,
                    "collected_at": datetime.now().isoformat(),
                    "topic": query,
                })

        return results


if __name__ == "__main__":
    crawler = Crawler()

    # 测试抓取
    topic = "AI 教育"
    print(f"正在抓取「{topic}」相关舆情...")

    articles = crawler.fetch_news(topic, limit=10)
    print(f"抓取到 {len(articles)} 篇文章")

    for i, article in enumerate(articles, 1):
        print(f"{i}. [{article['source']}] {article['title']}")
        print(f"   链接：{article['url']}")