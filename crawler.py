"""AI 舆情监控系统 - 爬虫模块"""

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

        # 新华网
        try:
            news = self._fetch_xinhua(topic, limit)
            articles.extend(news)
        except Exception as e:
            print(f"新华网抓取失败：{e}")

        # 人民网
        try:
            news = self._fetch_people(topic, limit)
            articles.extend(news)
        except Exception as e:
            print(f"人民网抓取失败：{e}")

        return articles[:limit]

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