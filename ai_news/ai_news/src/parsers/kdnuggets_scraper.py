from .rss_base import RSSFeedScraper


class KDnuggetsScraper(RSSFeedScraper):
    """Scraper for KDnuggets RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="KDnuggets", 
            feed_url="https://www.kdnuggets.com/feed"
        )