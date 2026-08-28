from datetime import datetime
from config import HEAT_KEYWORDS, BREAKING_KEYWORDS, BREAKING_NEWS_THRESHOLD, BREAKING_NEWS_MAX_AGE_SECONDS
import difflib


class HeatEngine:
    def __init__(self):
        self.major_keywords = set(HEAT_KEYWORDS["重大"])
        self.important_keywords = set(HEAT_KEYWORDS["重要"])
        self.breaking_keywords = set(BREAKING_KEYWORDS)
        self.keyword_frequency = {}
        self.last_update = None
        self._seen_titles = {}

    def calculate(self, item):
        score = 0.0
        text = f"{item.get('title', '')} {item.get('content', '')}"
        text_lower = text.lower()

        matched_keywords = []
        breaking_hits = []

        for kw in self.major_keywords:
            kw_lower = kw.lower()
            if kw_lower in text_lower:
                score += 15
                matched_keywords.append(kw)
                if kw in self.breaking_keywords:
                    breaking_hits.append(kw)

        for kw in self.important_keywords:
            kw_lower = kw.lower()
            if kw_lower in text_lower:
                score += 8
                if kw not in matched_keywords:
                    matched_keywords.append(kw)

        if item.get("important"):
            score += 25

        if item.get("error"):
            score = 0
            return self._build_result(item, 0, [], "error", False, [])

        published_dt = item.get("published_dt")
        age_seconds = None
        if published_dt:
            now = datetime.now()
            delta = (now - published_dt).total_seconds()
            age_seconds = delta
            if delta < 60:
                score += 50
            elif delta < 180:
                score += 45
            elif delta < 300:
                score += 40
            elif delta < 900:
                score += 25
            elif delta < 1800:
                score += 15
            elif delta < 3600:
                score += 10
            elif delta < 7200:
                score += 5
            elif delta < 14400:
                score += 2

        source_weights = {
            "cls": 1.3,
            "jin10": 1.3,
            "wallstreetcn": 1.2,
            "csrc": 1.3,
            "sse": 1.1,
            "szse": 1.1,
            "cninfo": 1.0,
            "cs": 1.0,
            "cnstock": 1.0,
            "stcn": 1.0,
        }
        source_id = item.get("source_id", "")
        score *= source_weights.get(source_id, 1.0)

        if len(item.get("title", "")) > 30:
            score += 3

        is_breaking = self._detect_breaking(score, breaking_hits, age_seconds, item)

        level = self._get_level(score)
        result = self._build_result(item, score, matched_keywords, level, is_breaking, breaking_hits)

        title_key = item.get("title", "")[:80].strip()
        if title_key:
            self._seen_titles[title_key] = datetime.now()

        return result

    def _detect_breaking(self, score, breaking_hits, age_seconds, item):
        if score < BREAKING_NEWS_THRESHOLD:
            return False
        if breaking_hits and (age_seconds is None or age_seconds < BREAKING_NEWS_MAX_AGE_SECONDS):
            return True
        if age_seconds is not None and age_seconds < 60 and score >= BREAKING_NEWS_THRESHOLD:
            return True
        if item.get("important") and breaking_hits:
            return True
        return False

    def is_duplicate(self, title, existing_items, threshold=0.75):
        if not title or len(title) < 6:
            return False
        title_lower = title.lower().strip()
        for existing in existing_items:
            ex_title = existing.get("title", "").lower().strip()
            if not ex_title:
                continue
            if title_lower == ex_title:
                return True
            if len(title_lower) > 10 and len(ex_title) > 10:
                ratio = difflib.SequenceMatcher(None, title_lower, ex_title).ratio()
                if ratio >= threshold:
                    return True
        return False

    def _build_result(self, item, score, keywords, level, is_breaking=False, breaking_hits=None):
        return {
            **item,
            "heat_score": round(score, 1),
            "heat_keywords": keywords[:8],
            "heat_level": level,
            "is_breaking": is_breaking,
            "breaking_hits": breaking_hits or [],
        }

    def _get_level(self, score):
        if score >= 80:
            return "scorching"
        elif score >= 50:
            return "hot"
        elif score >= 30:
            return "warm"
        elif score >= 15:
            return "cool"
        else:
            return "cold"

    def compute_keyword_stats(self, all_items):
        freq = {}
        for item in all_items:
            for kw in item.get("heat_keywords", []):
                freq[kw] = freq.get(kw, 0) + 1

        sorted_kw = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        self.keyword_frequency = dict(sorted_kw[:30])
        self.last_update = datetime.now()
        return self.keyword_frequency

    @property
    def heat_level_meta(self):
        return {
            "scorching": {"label": "爆", "color": "#ff1744", "bg": "rgba(255,23,68,0.12)"},
            "hot":       {"label": "热", "color": "#ff5722", "bg": "rgba(255,87,34,0.10)"},
            "warm":      {"label": "温", "color": "#ff9800", "bg": "rgba(255,152,0,0.08)"},
            "cool":      {"label": "凉", "color": "#4caf50", "bg": "rgba(76,175,80,0.06)"},
            "cold":      {"label": "冷", "color": "#90a4ae", "bg": "rgba(144,164,174,0.05)"},
        }
