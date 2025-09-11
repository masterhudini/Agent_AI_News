from .rss_base import RSSFeedScraper


class BAIRBlogScraper(RSSFeedScraper):
    """Scraper for BAIR Blog (UC Berkeley) RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="BAIR Blog", 
            feed_url="https://bair.berkeley.edu/blog/rss.xml"
        )