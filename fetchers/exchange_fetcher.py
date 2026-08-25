from .base import BaseFetcher
from config import DATA_SOURCES
from datetime import datetime
import requests
import re
import json
import urllib3
from bs4 import BeautifulSoup
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ExchangeFetcher(BaseFetcher):
    def __init__(self, source_id=None):
        if source_id is None:
            source_id = "sse"
        super().__init__(source_id, DATA_SOURCES[source_id])

    def fetch(self):
        if self.source_id == "sse":
            return self._fetch_sse()
        elif self.source_id == "szse":
            return self._fetch_szse()
        return [self._error_item("未知交易所")]

    def _fetch_sse(self):
        for url in [
            "http://www.sse.com.cn/disclosure/listinfo/announcement/",
            "https://www.sse.com.cn/disclosure/announcement/",
            "http://www.sse.com.cn/",
        ]:
            soup = self._request_html(url, headers={"Referer": "http://www.sse.com.cn/"})
            if not soup:
                continue
            items = []
            seen = set()
            for a_tag in soup.select("a[href]"):
                href = a_tag.get("href", "")
                title = a_tag.get_text(strip=True)
                if not title or len(title) < 6 or title in seen:
                    continue
                if any(kw in href for kw in ["/disclosure/", "/announcement/", "notice"]):
                    seen.add(title)
                    if not href.startswith("http"):
                        href = f"http://www.sse.com.cn{href}" if href.startswith("/") else f"http://www.sse.com.cn/{href}"
                    pub = self._extract_date_from_url(href) or f"{self._today_str()} 00:00"
                    item = self._make_item(title, "", href, pub)
                    items.append(item)
                    if len(items) >= 30:
                        break
            if items:
                return items

        try:
            import urllib3
            urllib3.disable_warnings()
            params = {
                "jsonCallBack": "jsonpCallback",
                "pageNo": "1",
                "pageSize": "30",
            }
            r = requests.get(
                "http://query.sse.com.cn/security/stock/queryCompanyBulletinNew.do",
                params=params,
                headers={**self.headers, "Referer": "http://www.sse.com.cn/"},
                timeout=self.timeout, verify=False
            )
            if r.status_code == 200:
                text = r.text
                jsonp_match = re.search(r'jsonpCallback\((.*)\)', text)
                if jsonp_match:
                    data = json.loads(jsonp_match.group(1))
                    page_help = data.get("pageHelp", {})
                    results = page_help.get("data", [])
                    items = []
                    for entry in results[:30]:
                        title = entry.get("BULLETINTITLE", "") or entry.get("title", "")
                        if not title:
                            continue
                        href = entry.get("URL", "") or ""
                        dt_str = entry.get("BULLETINDATE", "") or entry.get("date", "")
                        item = self._make_item(title, "", href, str(dt_str)[:19] if dt_str else "")
                        items.append(item)
                    if items:
                        return items
        except Exception:
            pass

        return [self._error_item("上交所数据获取失败")]

    def _fetch_szse(self):
        try:
            import urllib3
            urllib3.disable_warnings()
            params = {
                "random": 0.123,
                "pageNum": 1,
                "pageSize": 30,
                "channelCode": "fixed_disc",
            }
            r = requests.get(
                "https://www.szse.cn/api/disc/announcement/annList",
                params=params,
                headers={**self.headers, "Referer": "https://www.szse.cn/disclosure/"},
                timeout=self.timeout, verify=False
            )
            if r.status_code == 200:
                data = r.json()
                ann_list = data.get("data") or data.get("announceList") or data.get("result") or []
                if isinstance(ann_list, list) and ann_list:
                    items = []
                    for entry in ann_list[:30]:
                        title = entry.get("title", "") or entry.get("announcementTitle", "")
                        if not title:
                            continue
                        href = entry.get("announcementPath", "") or entry.get("url", "")
                        if href and not href.startswith("http"):
                            href = f"https://www.szse.cn{href}"
                        dt_val = (entry.get("announcementTime") or entry.get("noticeDate")
                                  or entry.get("publishTime") or entry.get("securitiesTime") or "")
                        dt_str = ""
                        if dt_val:
                            try:
                                if isinstance(dt_val, (int, float)):
                                    ts = float(dt_val)
                                    if ts > 1e12:
                                        ts = ts / 1000
                                    dt = datetime.fromtimestamp(ts)
                                    dt_str = dt.strftime("%Y-%m-%d %H:%M")
                                elif isinstance(dt_val, str):
                                    dt_str = dt_val[:16] if len(dt_val) >= 16 else dt_val
                            except (ValueError, TypeError):
                                dt_str = str(dt_val)[:16]
                        if not dt_str:
                            dt_str = self._extract_date_from_url(href or "") or f"{self._today_str()} 00:00"
                        item = self._make_item(title, "", href, dt_str)
                        items.append(item)
                    if items:
                        return items
        except Exception:
            pass

        soup = self._request_html(
            "https://www.szse.cn/disclosure/listed/notice/",
            headers={"Referer": "https://www.szse.cn/"}
        )
        if soup:
            items = []
            seen = set()
            for a_tag in soup.select("a[href]"):
                href = a_tag.get("href", "")
                title = a_tag.get_text(strip=True)
                if not title or len(title) < 6 or title in seen:
                    continue
                if "/disclosure/" in href or "/announcement/" in href:
                    seen.add(title)
                    if not href.startswith("http"):
                        href = f"https://www.szse.cn{href}" if href.startswith("/") else f"https://www.szse.cn/{href}"
                    pub = self._extract_date_from_url(href) or f"{self._today_str()} 00:00"
                    item = self._make_item(title, "", href, pub)
                    items.append(item)
                    if len(items) >= 30:
                        break
            if items:
                return items

        return [self._error_item("深交所数据获取失败")]
