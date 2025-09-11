"""
Tests for ScraperFactory auto-discovery system
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from ai_news.src.parsers.factory import ScraperFactory
from ai_news.src.parsers.base import BaseScraper
from ai_news.tests.base import BaseTestCase


class TestScraperFactory(BaseTestCase):
    """Test ScraperFactory auto-discovery and management"""
    
    def setUp(self):
        super().setUp()
        # Reset factory state for each test
        ScraperFactory._scrapers.clear()
        ScraperFactory._discovered = False
    
    def test_manual_scraper_registration(self):
        """Test manual scraper registration"""
        
        class TestManualScraper(BaseScraper):
            def scrape(self):
                return []
        
        # Register scraper
        ScraperFactory.register_scraper('manual_test', TestManualScraper)
        
        # Check it's registered
        available = ScraperFactory.get_available_scrapers()
        self.assertIn('manual_test', available)
        
        # Test creating scraper
        scraper = ScraperFactory.create_scraper('manual_test')
        self.assertIsInstance(scraper, TestManualScraper)
    
    def test_invalid_scraper_registration(self):
        """Test registering invalid scraper class"""
        
        class NotAScraper:
            pass
        
        with self.assertRaises(ValueError):
            ScraperFactory.register_scraper('invalid', NotAScraper)
    
    def test_create_unknown_scraper(self):
        """Test creating unknown scraper raises error"""
        
        with self.assertRaises(ValueError) as cm:
            ScraperFactory.create_scraper('nonexistent_scraper')
        
        self.assertIn('Unknown scraper type', str(cm.exception))
        self.assertIn('nonexistent_scraper', str(cm.exception))
    
    def test_case_insensitive_scraper_names(self):
        """Test that scraper names are case insensitive"""
        
        class TestCaseScraper(BaseScraper):
            def scrape(self):
                return []
        
        ScraperFactory.register_scraper('CaSeTest', TestCaseScraper)
        
        # Should work with lowercase
        scraper1 = ScraperFactory.create_scraper('casetest')
        scraper2 = ScraperFactory.create_scraper('CASETEST')
        scraper3 = ScraperFactory.create_scraper('CaSeTest')
        
        self.assertIsInstance(scraper1, TestCaseScraper)
        self.assertIsInstance(scraper2, TestCaseScraper)
        self.assertIsInstance(scraper3, TestCaseScraper)
    
    @patch('os.listdir')
    @patch('importlib.import_module')
    @patch('inspect.getmembers')
    def test_auto_discovery_process(self, mock_getmembers, mock_import, mock_listdir):
        """Test the auto-discovery process"""
        
        # Mock file system
        mock_listdir.return_value = [
            'test_scraper.py',
            '__init__.py',
            'base.py',
            'factory.py',
            'another_scraper.py'
        ]
        
        # Mock module import
        mock_module = Mock()
        mock_import.return_value = mock_module
        
        # Mock scraper classes
        class MockScraper1(BaseScraper):
            def scrape(self):
                return []
                
        class MockScraper2(BaseScraper):
            def scrape(self):
                return []
        
        # Mock inspect.getmembers to return our test classes
        mock_getmembers.return_value = [
            ('MockScraper1', MockScraper1),
            ('MockScraper2', MockScraper2),
            ('SomeOtherClass', str),  # Should be ignored
        ]
        
        # Trigger discovery
        ScraperFactory._discover_scrapers()
        
        # Check that scrapers were discovered
        available = ScraperFactory.get_available_scrapers()
        self.assertIn('mock1', available)  # MockScraper1 -> mock1
        self.assertIn('mock2', available)  # MockScraper2 -> mock2
    
    def test_scraper_info_retrieval(self):
        """Test getting scraper information"""
        
        class InfoTestScraper(BaseScraper):
            def __init__(self):
                super().__init__('Info Test Source')
            
            def scrape(self):
                return []
        
        ScraperFactory.register_scraper('info_test', InfoTestScraper)
        
        scraper_info = ScraperFactory.get_scraper_info()
        
        self.assertIn('info_test', scraper_info)
        info = scraper_info['info_test']
        
        self.assertEqual(info['class_name'], 'InfoTestScraper')
        self.assertIn('module', info)
        self.assertEqual(info['source_name'], 'Info Test Source')
    
    def test_reload_scrapers(self):
        """Test reloading scrapers functionality"""
        
        # Register a scraper
        class ReloadTestScraper(BaseScraper):
            def scrape(self):
                return []
        
        ScraperFactory.register_scraper('reload_test', ReloadTestScraper)
        
        # Verify it exists
        self.assertIn('reload_test', ScraperFactory.get_available_scrapers())
        
        # Reload (will clear and rediscover)
        with patch.object(ScraperFactory, '_discover_scrapers') as mock_discover:
            ScraperFactory.reload_scrapers()
            
            # Should have cleared scrapers and called discover
            mock_discover.assert_called_once()
            self.assertFalse(ScraperFactory._discovered)
    
    @patch('ai_news.src.parsers.factory.logger')
    def test_discovery_error_handling(self, mock_logger):
        """Test error handling during auto-discovery"""
        
        with patch('os.listdir', return_value=['broken_scraper.py']), \
             patch('importlib.import_module', side_effect=ImportError('Mock import error')):
            
            # Should handle import errors gracefully
            ScraperFactory._discover_scrapers()
            
            # Should have logged the error
            mock_logger.error.assert_called()
    
    def test_empty_available_scrapers_initially(self):
        """Test that initially no scrapers are available"""
        
        # Clear any existing scrapers
        ScraperFactory._scrapers.clear()
        ScraperFactory._discovered = False
        
        # With mocked empty discovery
        with patch('os.listdir', return_value=[]):
            available = ScraperFactory.get_available_scrapers()
            self.assertEqual(available, [])