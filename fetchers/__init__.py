from .cls_fetcher import CLSFetcher
from .jin10_fetcher import Jin10Fetcher
from .wallstreetcn_fetcher import WallstreetcnFetcher
from .cninfo_fetcher import CninfoFetcher
from .exchange_fetcher import ExchangeFetcher
from .csrc_fetcher import CSRCFetcher
from .securities_fetcher import SecuritiesFetcher

ALL_FETCHERS = {
    "cls":          CLSFetcher,
    "jin10":        Jin10Fetcher,
    "wallstreetcn": WallstreetcnFetcher,
    "cninfo":       CninfoFetcher,
    "sse":          ExchangeFetcher,
    "szse":         ExchangeFetcher,
    "csrc":         CSRCFetcher,
    "cs":           SecuritiesFetcher,
    "cnstock":      SecuritiesFetcher,
    "stcn":         SecuritiesFetcher,
}
