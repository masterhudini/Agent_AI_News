from .rss_base import RSSFeedScraper


class TechCrunchAIScraper(RSSFeedScraper):
    """Scraper for TechCrunch AI tag RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="TechCrunch AI", 
            feed_url="https://techcrunch.com/tag/artificial-intelligence/feed/"
        )