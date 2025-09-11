from .rss_base import RSSFeedScraper


class AIMagazineScraper(RSSFeedScraper):
    """Scraper for AI Magazine RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="AI Magazine", 
            feed_url="https://aimagazine.com/feed/"
        )