from .rss_base import RSSFeedScraper


class WiredAIScraper(RSSFeedScraper):
    """Scraper for Wired AI category RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="Wired AI", 
            feed_url="https://www.wired.com/category/science/artificial-intelligence/rss"
        )