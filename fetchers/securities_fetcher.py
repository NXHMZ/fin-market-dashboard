from .base import BaseFetcher
from config import DATA_SOURCES
from bs4 import BeautifulSoup
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SecuritiesFetcher(BaseFetcher):
    def __init__(self, source_id=None):
        if source_id is None:
            source_id = "cs"
        super().__init__(source_id, DATA_SOURCES[source_id])

    def fetch(self):
        if self.source_id == "cs":
            return self._fetch_cs()
        elif self.source_id == "cnstock":
            return self._fetch_cnstock()
        elif self.source_id == "stcn":
            return self._fetch_stcn()
        return [self._error_item("未知证券报")]

    def _fetch_cs(self):
        soup = self._request_html("https://www.cs.com.cn/")
        if not soup:
            return [self._error_item("无法连接中国证券报网站")]

        items = []
        seen = set()
        for a_tag in soup.select("a[href]"):
            href = a_tag.get("href", "")
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 8 or title in seen:
                continue
            if "detail_" in href or "/ssgs/" in href or "/sylm/" in href:
                seen.add(title)
                if not href.startswith("http"):
                    href = f"https://www.cs.com.cn{href}" if href.startswith("/") else f"https://www.cs.com.cn/{href}"
                pub = self._extract_date_from_url(href) or f"{self._today_str()} 00:00"
                item = self._make_item(title, "", href, pub)
                items.append(item)
                if len(items) >= 30:
                    break

        if not items:
            return [self._error_item("中国证券报未提取到新闻")]
        return items

    def _fetch_cnstock(self):
        soup = self._request_html("https://www.cnstock.com/")
        if not soup:
            return [self._error_item("无法连接上海证券报网站")]

        items = []
        seen = set()
        for a_tag in soup.select("a[href]"):
            href = a_tag.get("href", "")
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 8 or title in seen:
                continue
            if "/commonDetail/" in href or "/topicDetail/" in href or "/liveDetail/" in href:
                seen.add(title)
                if not href.startswith("http"):
                    href = f"https://www.cnstock.com{href}" if href.startswith("/") else f"https://www.cnstock.com/{href}"
                pub = self._extract_date_from_url(href) or f"{self._today_str()} 00:00"
                item = self._make_item(title, "", href, pub)
                items.append(item)
                if len(items) >= 30:
                    break

        if not items:
            return [self._error_item("上海证券报未提取到新闻")]
        return items

    def _fetch_stcn(self):
        soup = self._request_html("https://www.stcn.com/")
        if not soup:
            return [self._error_item("无法连接证券时报网站")]

        items = []
        seen = set()
        for a_tag in soup.select("a[href]"):
            href = a_tag.get("href", "")
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 8 or title in seen:
                continue
            if "/article/" in href:
                seen.add(title)
                if not href.startswith("http"):
                    href = f"https://www.stcn.com{href}" if href.startswith("/") else f"https://www.stcn.com/{href}"
                pub = self._extract_date_from_url(href) or f"{self._today_str()} 00:00"
                item = self._make_item(title, "", href, pub)
                items.append(item)
                if len(items) >= 30:
                    break

        if not items:
            return [self._error_item("证券时报未提取到新闻")]
        return items
