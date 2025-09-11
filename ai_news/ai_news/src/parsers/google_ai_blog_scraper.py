from .rss_base import RSSFeedScraper


class GoogleAIBlogScraper(RSSFeedScraper):
    """Scraper for Google AI Blog RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="Google AI Blog", 
            feed_url="https://ai.googleblog.com/feeds/posts/default"
        )