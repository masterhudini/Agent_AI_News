from .rss_base import RSSFeedScraper


class TheVergeScraper(RSSFeedScraper):
    """Scraper for The Verge RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="The Verge", 
            feed_url="https://www.theverge.com/rss/index.xml"
        )