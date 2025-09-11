from .rss_base import RSSFeedScraper


class AnalyticsVidhyaScraper(RSSFeedScraper):
    """Scraper for Analytics Vidhya RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="Analytics Vidhya", 
            feed_url="https://www.analyticsvidhya.com/blog/feed/"
        )