from .rss_base import RSSFeedScraper


class TechCrunchScraper(RSSFeedScraper):
    """Scraper for TechCrunch RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="TechCrunch", 
            feed_url="https://techcrunch.com/feed/"
        )