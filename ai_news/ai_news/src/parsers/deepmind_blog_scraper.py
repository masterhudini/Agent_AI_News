from .rss_base import RSSFeedScraper


class DeepMindBlogScraper(RSSFeedScraper):
    """Scraper for DeepMind Blog RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="DeepMind Blog", 
            feed_url="https://deepmind.com/blog/feed.xml"
        )