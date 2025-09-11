"""
Tests for base parser classes
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from ai_news.src.parsers.base import BaseScraper, NewsArticleData
from ai_news.tests.base import BaseTestCase


class TestNewsArticleData(BaseTestCase):
    """Test NewsArticleData class"""
    
    def test_news_article_data_creation(self):
        """Test creating NewsArticleData instance"""
        article_data = self.create_mock_article_data()
        
        self.assertEqual(article_data.title, 'Test AI Article')
        self.assertEqual(article_data.source, 'Test Source')
        self.assertIsInstance(article_data.published_date, datetime)
        
    def test_news_article_data_with_optional_fields(self):
        """Test NewsArticleData with optional author field"""
        article_data = self.create_mock_article_data(
            author='Test Author',
            title='Custom Title'
        )
        
        self.assertEqual(article_data.author, 'Test Author')
        self.assertEqual(article_data.title, 'Custom Title')


class TestBaseScraper(BaseTestCase):
    """Test BaseScraper abstract base class"""
    
    def setUp(self):
        super().setUp()
        
        # Create concrete implementation for testing
        class TestScraper(BaseScraper):
            def scrape(self):
                return [self.create_mock_article_data()]
        
        self.TestScraper = TestScraper
    
    def test_base_scraper_initialization(self):
        """Test BaseScraper initialization"""
        scraper = self.TestScraper('Test Source')
        
        self.assertEqual(scraper.source_name, 'Test Source')
        self.assertIsNotNone(scraper.session)
        self.assertIn('User-Agent', scraper.session.headers)
    
    def test_clean_text_method(self):
        """Test _clean_text utility method"""
        scraper = self.TestScraper('Test Source')
        
        # Test cleaning whitespace
        dirty_text = "  This   is   messy    text  "
        clean_text = scraper._clean_text(dirty_text)
        self.assertEqual(clean_text, "This is messy text")
        
        # Test empty string
        self.assertEqual(scraper._clean_text(""), "")
        
        # Test None
        self.assertEqual(scraper._clean_text(None), "")
    
    def test_parse_date_method(self):
        """Test _parse_date utility method"""
        scraper = self.TestScraper('Test Source')
        
        # Test ISO format with Z
        iso_date = "2023-12-01T10:30:00Z"
        parsed_date = scraper._parse_date(iso_date)
        self.assertIsInstance(parsed_date, datetime)
        
        # Test ISO format without Z
        iso_date_no_z = "2023-12-01T10:30:00"
        parsed_date = scraper._parse_date(iso_date_no_z)
        self.assertIsInstance(parsed_date, datetime)
        
        # Test invalid date (should return current time)
        invalid_date = "not-a-date"
        parsed_date = scraper._parse_date(invalid_date)
        self.assertIsInstance(parsed_date, datetime)
        
        # Test empty string
        parsed_date = scraper._parse_date("")
        self.assertIsInstance(parsed_date, datetime)
    
    def test_scrape_method_abstract(self):
        """Test that scrape method must be implemented"""
        with self.assertRaises(TypeError):
            # Should not be able to instantiate BaseScraper directly
            BaseScraper('Test')
    
    def test_concrete_scraper_implementation(self):
        """Test concrete scraper implementation"""
        scraper = self.TestScraper('Test Source')
        articles = scraper.scrape()
        
        self.assertIsInstance(articles, list)
        self.assertEqual(len(articles), 1)
        self.assertIsInstance(articles[0], NewsArticleData)