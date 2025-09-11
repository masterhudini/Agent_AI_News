"""
Tests for RSS base scraper functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock

from ai_news.src.parsers.rss_base import RSSFeedScraper
from ai_news.src.parsers.base import NewsArticleData
from ai_news.tests.base import BaseTestCase, mock_feedparser_parse


class TestRSSFeedScraper(BaseTestCase):
    """Test RSSFeedScraper functionality"""
    
    def setUp(self):
        super().setUp()
        self.scraper = RSSFeedScraper('Test RSS Source', 'https://example.com/rss')
    
    def test_rss_scraper_initialization(self):
        """Test RSS scraper initialization"""
        self.assertEqual(self.scraper.source_name, 'Test RSS Source')
        self.assertEqual(self.scraper.feed_url, 'https://example.com/rss')
    
    @patch('ai_news.src.parsers.rss_base.feedparser.parse')
    def test_successful_rss_scraping(self, mock_parse):
        """Test successful RSS feed scraping"""
        
        # Mock feedparser response
        mock_feed = self.create_mock_rss_feed(entry_count=2)
        mock_parse.return_value = mock_feed
        
        # Scrape articles
        articles = self.scraper.scrape()
        
        # Verify results
        self.assertEqual(len(articles), 2)
        self.assertIsInstance(articles[0], NewsArticleData)
        self.assertEqual(articles[0].source, 'Test RSS Source')
        
        # Verify feedparser was called correctly
        mock_parse.assert_called_once_with('https://example.com/rss')
    
    @patch('ai_news.src.parsers.rss_base.feedparser.parse')
    def test_rss_scraping_with_invalid_feed(self, mock_parse):
        """Test RSS scraping with invalid feed format"""
        
        # Mock invalid feed (no entries attribute)
        mock_feed = Mock()
        del mock_feed.entries  # Remove entries attribute
        mock_parse.return_value = mock_feed
        
        articles = self.scraper.scrape()
        
        # Should return empty list
        self.assertEqual(articles, [])
    
    @patch('ai_news.src.parsers.rss_base.feedparser.parse')
    def test_rss_scraping_with_exception(self, mock_parse):
        """Test RSS scraping with network exception"""
        
        # Mock exception during parsing
        mock_parse.side_effect = Exception('Network error')
        
        articles = self.scraper.scrape()
        
        # Should handle exception and return empty list
        self.assertEqual(articles, [])
    
    def test_extract_content_from_entry(self):
        """Test content extraction from RSS entries"""
        
        # Test with summary field
        entry_with_summary = Mock(
            summary='Test summary content',
            content='',
            description=''
        )
        content = self.scraper._extract_content(entry_with_summary)
        self.assertEqual(content, 'Test summary content')
        
        # Test with content field (list format)
        entry_with_content = Mock(
            summary='',
            content=[{'value': 'Test content value'}],
            description=''
        )
        content = self.scraper._extract_content(entry_with_content)
        self.assertEqual(content, 'Test content value')
        
        # Test with description field
        entry_with_description = Mock(
            summary='',
            content='',
            description='Test description'
        )
        content = self.scraper._extract_content(entry_with_description)
        self.assertEqual(content, 'Test description')
    
    def test_extract_content_with_complex_formats(self):
        """Test content extraction with various content formats"""
        
        # Test with content as dict
        entry_dict_content = Mock(
            summary='',
            content={'value': 'Dict content'},
            description=''
        )
        content = self.scraper._extract_content(entry_dict_content)
        self.assertEqual(content, 'Dict content')
        
        # Test with content as list of strings
        entry_list_content = Mock(
            summary='',
            content=['String content'],
            description=''
        )
        content = self.scraper._extract_content(entry_list_content)
        self.assertEqual(content, 'String content')
        
        # Test with no content
        entry_no_content = Mock(
            summary='',
            content='',
            description=''
        )
        content = self.scraper._extract_content(entry_no_content)
        self.assertEqual(content, '')
    
    @patch('ai_news.src.parsers.rss_base.feedparser.parse')
    def test_rss_scraping_filters_invalid_entries(self, mock_parse):
        """Test that RSS scraping filters out invalid entries"""
        
        # Create mock feed with valid and invalid entries
        mock_feed = Mock()
        mock_feed.entries = [
            # Valid entry
            Mock(
                title='Valid Entry',
                summary='Valid summary',
                link='https://example.com/valid',
                published='2023-01-01T00:00:00Z',
                author='Valid Author'
            ),
            # Invalid entry (no title)
            Mock(
                title='',
                summary='No title summary',
                link='https://example.com/invalid1',
                published='2023-01-02T00:00:00Z',
                author='Invalid Author'
            ),
            # Invalid entry (no URL)
            Mock(
                title='No URL Entry',
                summary='No URL summary',
                link='',
                published='2023-01-03T00:00:00Z',
                author='Another Author'
            )
        ]
        
        mock_parse.return_value = mock_feed
        
        articles = self.scraper.scrape()
        
        # Should only return valid entries
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, 'Valid Entry')
    
    @patch('ai_news.src.parsers.rss_base.feedparser.parse')
    @patch('ai_news.src.parsers.rss_base.logger')
    def test_rss_scraping_logs_appropriately(self, mock_logger, mock_parse):
        """Test that RSS scraping logs appropriately"""
        
        mock_feed = self.create_mock_rss_feed(entry_count=3)
        mock_parse.return_value = mock_feed
        
        articles = self.scraper.scrape()
        
        # Should log info messages
        mock_logger.info.assert_called()
        
        # Verify log messages contain expected info
        log_calls = mock_logger.info.call_args_list
        self.assertTrue(any('Scraping RSS feed' in str(call) for call in log_calls))
        self.assertTrue(any('Successfully scraped' in str(call) for call in log_calls))
    
    @patch('ai_news.src.parsers.rss_base.feedparser.parse')
    def test_rss_entry_processing_error_handling(self, mock_parse):
        """Test error handling during individual entry processing"""
        
        # Create mock feed with problematic entry
        mock_feed = Mock()
        problematic_entry = Mock()
        # Make get() method raise exception
        problematic_entry.get.side_effect = Exception('Entry processing error')
        
        mock_feed.entries = [problematic_entry]
        mock_parse.return_value = mock_feed
        
        # Should handle entry processing errors gracefully
        articles = self.scraper.scrape()
        self.assertEqual(articles, [])