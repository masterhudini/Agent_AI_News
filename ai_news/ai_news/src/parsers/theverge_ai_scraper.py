from .rss_base import RSSFeedScraper


class TheVergeAIScraper(RSSFeedScraper):
    """Scraper for The Verge AI category RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="The Verge AI", 
            feed_url="https://www.theverge.com/ai/rss/index.xml"
        )