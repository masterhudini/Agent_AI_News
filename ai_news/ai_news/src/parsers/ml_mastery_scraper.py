from .rss_base import RSSFeedScraper


class MLMasteryScraper(RSSFeedScraper):
    """Scraper for Machine Learning Mastery RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="ML Mastery", 
            feed_url="https://machinelearningmastery.com/blog/feed/"
        )