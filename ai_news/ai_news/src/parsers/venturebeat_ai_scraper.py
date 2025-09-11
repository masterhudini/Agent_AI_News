from .rss_base import RSSFeedScraper


class VentureBeatAIScraper(RSSFeedScraper):
    """Scraper for VentureBeat AI category RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="VentureBeat AI", 
            feed_url="https://venturebeat.com/category/ai/feed/"
        )