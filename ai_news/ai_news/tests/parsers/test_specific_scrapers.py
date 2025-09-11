"""
Tests for specific scraper implementations
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from ai_news.src.parsers.openai_blog_scraper import OpenAIBlogScraper
from ai_news.src.parsers.hackernews_scraper import HackerNewsScraper
from ai_news.src.parsers.reddit_machinelearning_scraper import RedditMachineLeaningScraper
from ai_news.src.parsers.arxiv_ai_scraper import ArxivAIScraper
from ai_news.tests.base import BaseTestCase, MockRequestsResponse


class TestSpecificScrapers(BaseTestCase):
    """Test specific scraper implementations"""
    
    def test_openai_blog_scraper_initialization(self):
        """Test OpenAI Blog scraper initialization"""
        scraper = OpenAIBlogScraper()
        
        self.assertEqual(scraper.source_name, 'OpenAI Blog')
        self.assertEqual(scraper.feed_url, 'https://openai.com/blog/rss/')
    
    def test_hackernews_scraper_initialization(self):
        """Test Hacker News scraper initialization"""
        scraper = HackerNewsScraper()
        
        self.assertEqual(scraper.source_name, 'Hacker News')
        self.assertEqual(scraper.api_url, 'https://hacker-news.firebaseio.com/v0')
        self.assertEqual(scraper.max_stories, 30)
    
    @patch('ai_news.src.parsers.hackernews_scraper.requests.Session.get')
    def test_hackernews_scraper_successful_scraping(self, mock_get):
        """Test Hacker News scraper successful operation"""
        
        scraper = HackerNewsScraper()
        
        # Mock top stories response
        story_ids_response = MockRequestsResponse(json_data=[1, 2, 3])
        
        # Mock individual story responses
        story1_response = MockRequestsResponse(json_data={
            'type': 'story',
            'title': 'Test AI Story 1',
            'url': 'https://example.com/story1',
            'text': 'Story 1 content',
            'time': 1609459200,  # 2021-01-01
            'by': 'author1'
        })
        
        story2_response = MockRequestsResponse(json_data={
            'type': 'story',
            'title': 'Test AI Story 2',
            'url': 'https://example.com/story2',
            'text': 'Story 2 content',
            'time': 1609545600,  # 2021-01-02
            'by': 'author2'
        })
        
        story3_response = MockRequestsResponse(json_data={
            'type': 'ask',  # Not a story type, should be filtered
            'title': 'Ask HN: Something',
            'url': '',
            'time': 1609632000
        })
        
        mock_get.side_effect = [story_ids_response, story1_response, story2_response, story3_response]
        
        articles = scraper.scrape()
        
        # Should have 2 valid stories (story3 filtered out)
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0].title, 'Test AI Story 1')
        self.assertEqual(articles[0].source, 'Hacker News')
        self.assertEqual(articles[1].title, 'Test AI Story 2')
    
    @patch('ai_news.src.parsers.hackernews_scraper.requests.Session.get')
    def test_hackernews_scraper_network_error(self, mock_get):
        """Test Hacker News scraper with network error"""
        
        scraper = HackerNewsScraper()
        mock_get.side_effect = Exception('Network timeout')
        
        articles = scraper.scrape()
        
        # Should handle error gracefully
        self.assertEqual(articles, [])
    
    def test_reddit_scraper_initialization(self):
        """Test Reddit scraper initialization"""
        scraper = RedditMachineLeaningScraper()
        
        self.assertEqual(scraper.source_name, 'Reddit ML')
        self.assertEqual(scraper.feed_url, 'https://www.reddit.com/r/MachineLearning/.rss')
    
    def test_reddit_scraper_content_extraction(self):
        """Test Reddit scraper HTML content extraction"""
        scraper = RedditMachineLeaningScraper()
        
        # Test with HTML content
        entry_with_html = Mock()
        entry_with_html.get.side_effect = lambda key, default='': {
            'content': [{'value': '&lt;p&gt;Test HTML content&lt;/p&gt;'}],
            'summary': '',
            'description': ''
        }.get(key, default)
        
        content = scraper._extract_content(entry_with_html)
        
        # Should decode HTML entities and extract text
        self.assertIn('Test HTML content', content)
        self.assertNotIn('&lt;', content)
        self.assertNotIn('&gt;', content)
    
    def test_arxiv_scraper_initialization(self):
        """Test arXiv scraper initialization"""
        scraper = ArxivAIScraper()
        
        self.assertEqual(scraper.source_name, 'arXiv AI')
        self.assertEqual(scraper.feed_url, 'https://export.arxiv.org/rss/cs.AI')
    
    def test_arxiv_scraper_content_extraction(self):
        """Test arXiv scraper abstract extraction"""
        scraper = ArxivAIScraper()
        
        # Test with arXiv-style summary
        entry_with_arxiv_format = Mock()
        entry_with_arxiv_format.get.side_effect = lambda key, default='': {
            'summary': 'arXiv:2301.00123v1 [cs.AI] 1 Jan 2023\nThis is the actual abstract content for the paper.',
            'description': '',
            'content': ''
        }.get(key, default)
        
        content = scraper._extract_content(entry_with_arxiv_format)
        
        # Should extract abstract without arXiv prefix
        self.assertIn('This is the actual abstract', content)
        self.assertNotIn('arXiv:2301.00123v1', content)


class TestScraperErrorHandling(BaseTestCase):
    """Test error handling across different scrapers"""
    
    @patch('ai_news.src.parsers.rss_base.feedparser.parse')
    def test_rss_scraper_malformed_date_handling(self, mock_parse):
        """Test RSS scrapers handle malformed dates"""
        
        scraper = OpenAIBlogScraper()
        
        # Mock feed with malformed date
        mock_feed = Mock()
        mock_feed.entries = [
            Mock(
                title='Test Article',
                summary='Test summary',
                link='https://example.com/test',
                published='not-a-valid-date',  # Malformed date
                author='Test Author'
            )
        ]
        mock_parse.return_value = mock_feed
        
        articles = scraper.scrape()
        
        # Should handle malformed date gracefully
        self.assertEqual(len(articles), 1)
        self.assertIsInstance(articles[0].published_date, datetime)
    
    @patch('ai_news.src.parsers.hackernews_scraper.requests.Session.get')
    def test_hackernews_scraper_malformed_response(self, mock_get):
        """Test Hacker News scraper with malformed API response"""
        
        scraper = HackerNewsScraper()
        
        # Mock malformed responses
        malformed_response = MockRequestsResponse(json_data={'invalid': 'format'})
        mock_get.return_value = malformed_response
        
        articles = scraper.scrape()
        
        # Should handle malformed response gracefully
        self.assertEqual(articles, [])
    
    def test_scraper_session_configuration(self):
        """Test that all scrapers have proper session configuration"""
        
        scrapers_to_test = [
            OpenAIBlogScraper(),
            HackerNewsScraper(),
            RedditMachineLeaningScraper(),
            ArxivAIScraper()
        ]
        
        for scraper in scrapers_to_test:
            # Check session exists and has User-Agent
            self.assertIsNotNone(scraper.session)
            self.assertIn('User-Agent', scraper.session.headers)
            
            # Check User-Agent is reasonable (contains browser-like string)
            user_agent = scraper.session.headers['User-Agent']
            self.assertIn('Mozilla', user_agent)


class TestScraperIntegration(BaseTestCase):
    """Integration tests for scrapers"""
    
    @patch('ai_news.src.parsers.rss_base.feedparser.parse')
    def test_multiple_scrapers_same_feed_format(self, mock_parse):
        """Test multiple scrapers can handle same feed format"""
        
        # Mock the same feed for different scrapers
        mock_feed = self.create_mock_rss_feed(entry_count=2)
        mock_parse.return_value = mock_feed
        
        scrapers = [
            OpenAIBlogScraper(),
            ArxivAIScraper(),
            RedditMachineLeaningScraper()
        ]
        
        for scraper in scrapers:
            articles = scraper.scrape()
            
            # Each should produce same number of articles
            self.assertEqual(len(articles), 2)
            
            # But with their own source name
            self.assertEqual(articles[0].source, scraper.source_name)
            self.assertEqual(articles[1].source, scraper.source_name)
    
    def test_scraper_inheritance_hierarchy(self):
        """Test scraper inheritance relationships"""
        
        from ai_news.src.parsers.base import BaseScraper
        from ai_news.src.parsers.rss_base import RSSFeedScraper
        
        # RSS-based scrapers should inherit from RSSFeedScraper
        rss_scrapers = [OpenAIBlogScraper(), ArxivAIScraper(), RedditMachineLeaningScraper()]
        
        for scraper in rss_scrapers:
            self.assertIsInstance(scraper, RSSFeedScraper)
            self.assertIsInstance(scraper, BaseScraper)
        
        # API-based scrapers should inherit directly from BaseScraper
        api_scrapers = [HackerNewsScraper()]
        
        for scraper in api_scrapers:
            self.assertIsInstance(scraper, BaseScraper)
            self.assertNotIsInstance(scraper, RSSFeedScraper)