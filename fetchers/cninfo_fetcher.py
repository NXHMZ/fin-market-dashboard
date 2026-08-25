from .base import BaseFetcher
from config import DATA_SOURCES
from datetime import datetime
from bs4 import BeautifulSoup
import requests


class CninfoFetcher(BaseFetcher):
    def __init__(self):
        super().__init__("cninfo", DATA_SOURCES["cninfo"])

    def fetch(self):
        url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
        data = {
            "stock": "",
            "tabName": "fulltext",
            "pageSize": "30",
            "pageNum": "1",
            "column": "szse",
            "category": "",
            "plate": "sz",
            "searchkey": "",
            "secid": "",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        headers = {
            **self.headers,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "http://www.cninfo.com.cn/new/disclosure",
        }
        try:
            import urllib3
            urllib3.disable_warnings()
            resp = requests.post(url, data=data, headers=headers,
                                 timeout=self.timeout, verify=False)
            if resp.status_code != 200:
                return [self._error_item("巨潮资讯网接口请求失败")]
            result = resp.json()
        except Exception:
            return [self._error_item("无法连接巨潮资讯网接口")]

        items = []
        announcements = result.get("announcements", [])
        if not announcements:
            return [self._error_item("巨潮资讯网未获取到公告")]

        for entry in announcements[:30]:
            title = entry.get("announcementTitle", "")
            if not title:
                continue
            sec_name = entry.get("secName", "")
            sec_code = entry.get("secCode", "")
            prefix = f"[{sec_name}{sec_code}] " if sec_name else ""

            ann_id = entry.get("announcementId", "")
            if ann_id and sec_code:
                href = f"http://www.cninfo.com.cn/new/disclosure/detail?stockCode={sec_code}&announcementId={ann_id}"
            elif entry.get("adjunctUrl", ""):
                href = f"http://www.cninfo.com.cn/{entry['adjunctUrl']}"
            else:
                href = ""

            ann_time = entry.get("announcementTime", "")
            dt_str = ""
            if ann_time:
                try:
                    dt = datetime.fromtimestamp(int(ann_time) / 1000)
                    dt_str = dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError):
                    pass

            item = self._make_item(prefix + title, "", href, dt_str)
            items.append(item)

        if not items:
            return [self._error_item("巨潮资讯网未解析到公告")]
        return items
