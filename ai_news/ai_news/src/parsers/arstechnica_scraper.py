from .rss_base import RSSFeedScraper


class ArsTechnicaScraper(RSSFeedScraper):
    """Scraper for Ars Technica RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="Ars Technica", 
            feed_url="https://feeds.arstechnica.com/arstechnica/index"
        )