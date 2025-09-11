from .rss_base import RSSFeedScraper


class AWSMLBlogScraper(RSSFeedScraper):
    """Scraper for AWS Machine Learning Blog RSS feed"""
    
    def __init__(self):
        super().__init__(
            source_name="AWS ML Blog", 
            feed_url="https://aws.amazon.com/blogs/machine-learning/feed/"
        )