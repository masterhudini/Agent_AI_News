from .rss_base import RSSFeedScraper


class AINewsScraper(RSSFeedScraper):
    """Scraper for AI News RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="AI News", 
            feed_url="https://www.artificialintelligence-news.com/feed/"
        )