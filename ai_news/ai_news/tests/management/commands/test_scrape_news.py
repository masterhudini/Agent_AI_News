"""
Tests for scrape_news management command
"""

import unittest
from unittest.mock import Mock, patch, call
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from ai_news.tests.base import BaseTestCase


class TestScrapeNewsCommand(BaseTestCase):
    """Test scrape_news management command"""
    
    def setUp(self):
        super().setUp()
        self.stdout = StringIO()
        self.stderr = StringIO()
    
    @patch('ai_news.src.management.commands.scrape_news.ScraperFactory')
    def test_list_sources_option(self, mock_factory):
        """Test --list-sources option"""
        
        mock_factory.get_available_scrapers.return_value = [
            'openai_blog', 'google_ai_blog', 'hackernews'
        ]
        
        call_command('scrape_news', '--list-sources', stdout=self.stdout)
        
        output = self.stdout.getvalue()
        
        # Should list all available sources
        self.assertIn('Available news sources:', output)
        self.assertIn('openai_blog', output)
        self.assertIn('google_ai_blog', output)
        self.assertIn('hackernews', output)
    
    @patch('ai_news.src.management.commands.scrape_news.NewsOrchestrationService')
    def test_scrape_all_sources(self, mock_service_class):
        """Test --all option to scrape all sources"""
        
        mock_service = Mock()
        mock_service.scrape_all_sources.return_value = {
            'openai_blog': 5,
            'google_ai_blog': 3,
            'hackernews': 8
        }
        mock_service_class.return_value = mock_service
        
        call_command('scrape_news', '--all', stdout=self.stdout)
        
        output = self.stdout.getvalue()
        
        # Should report scraping results
        self.assertIn('Scraping all available sources', output)
        self.assertIn('openai_blog: 5 new articles', output)
        self.assertIn('google_ai_blog: 3 new articles', output)
        self.assertIn('hackernews: 8 new articles', output)
        self.assertIn('Total: 16 new articles', output)
        
        # Should call service method
        mock_service.scrape_all_sources.assert_called_once()
    
    @patch('ai_news.src.management.commands.scrape_news.NewsOrchestrationService')
    def test_scrape_specific_source(self, mock_service_class):
        """Test --source option to scrape specific source"""
        
        mock_service = Mock()
        mock_service.scrape_single_source.return_value = 7
        mock_service_class.return_value = mock_service
        
        call_command('scrape_news', '--source', 'openai_blog', stdout=self.stdout)
        
        output = self.stdout.getvalue()
        
        # Should report scraping result
        self.assertIn('Scraping source: openai_blog', output)
        self.assertIn('Found 7 new articles', output)
        
        # Should call service method with correct source
        mock_service.scrape_single_source.assert_called_once_with('openai_blog')
    
    @patch('ai_news.src.management.commands.scrape_news.NewsOrchestrationService')
    def test_scrape_with_summary_generation(self, mock_service_class):
        """Test scraping with --generate-summary option"""
        
        mock_service = Mock()
        mock_service.scrape_all_sources.return_value = {'source1': 5}
        mock_service.generate_daily_summary.return_value = Mock(title='Daily Summary')
        mock_service_class.return_value = mock_service
        
        call_command('scrape_news', '--all', '--generate-summary', stdout=self.stdout)
        
        output = self.stdout.getvalue()
        
        # Should report summary generation
        self.assertIn('Generating daily summary', output)
        self.assertIn('Generated summary: Daily Summary', output)
        
        # Should call summary generation
        mock_service.generate_daily_summary.assert_called_once()
    
    @patch('ai_news.src.management.commands.scrape_news.NewsOrchestrationService')
    def test_scrape_with_summary_failure(self, mock_service_class):
        """Test scraping when summary generation fails"""
        
        mock_service = Mock()
        mock_service.scrape_all_sources.return_value = {'source1': 3}
        mock_service.generate_daily_summary.return_value = None  # Summary failed
        mock_service_class.return_value = mock_service
        
        call_command('scrape_news', '--all', '--generate-summary', stdout=self.stdout)
        
        output = self.stdout.getvalue()
        
        # Should handle summary failure gracefully
        self.assertIn('No new articles found for summary', output)
    
    @patch('ai_news.src.management.commands.scrape_news.NewsOrchestrationService')
    def test_scrape_source_error_handling(self, mock_service_class):
        """Test error handling during source scraping"""
        
        mock_service = Mock()
        mock_service.scrape_single_source.side_effect = Exception('Scraping error')
        mock_service_class.return_value = mock_service
        
        with self.assertRaises(CommandError):
            call_command('scrape_news', '--source', 'failing_source')
    
    @patch('ai_news.src.management.commands.scrape_news.ScraperFactory')
    def test_list_sources_empty(self, mock_factory):
        """Test --list-sources when no sources available"""
        
        mock_factory.get_available_scrapers.return_value = []
        
        call_command('scrape_news', '--list-sources', stdout=self.stdout)
        
        output = self.stdout.getvalue()
        
        # Should handle empty source list
        self.assertIn('No news sources available', output)
    
    def test_no_options_provided(self):
        """Test command when no options are provided"""
        
        call_command('scrape_news', stdout=self.stdout, stderr=self.stderr)
        
        output = self.stderr.getvalue()
        
        # Should show error message
        self.assertIn('Please specify an action', output)
    
    @patch('ai_news.src.management.commands.scrape_news.NewsOrchestrationService')
    def test_scrape_all_with_zero_results(self, mock_service_class):
        """Test scraping all sources with zero results"""
        
        mock_service = Mock()
        mock_service.scrape_all_sources.return_value = {
            'source1': 0,
            'source2': 0
        }
        mock_service_class.return_value = mock_service
        
        call_command('scrape_news', '--all', stdout=self.stdout)
        
        output = self.stdout.getvalue()
        
        # Should report zero results appropriately
        self.assertIn('Total: 0 new articles', output)
        self.assertIn('source1: 0 new articles', output)
    
    @patch('ai_news.src.management.commands.scrape_news.NewsOrchestrationService')
    def test_scrape_with_verbose_output(self, mock_service_class):
        """Test scraping with verbose output"""
        
        mock_service = Mock()
        mock_service.scrape_single_source.return_value = 10
        mock_service_class.return_value = mock_service
        
        call_command('scrape_news', '--source', 'test_source', '--verbosity', '2', stdout=self.stdout)
        
        output = self.stdout.getvalue()
        
        # Should include verbose information
        self.assertIn('Scraping source: test_source', output)
        self.assertIn('Found 10 new articles', output)
    
    @patch('ai_news.src.management.commands.scrape_news.ScraperFactory')
    def test_scraper_factory_integration(self, mock_factory):
        """Test integration with ScraperFactory"""
        
        mock_factory.get_available_scrapers.return_value = ['source1', 'source2', 'source3']
        
        call_command('scrape_news', '--list-sources', stdout=self.stdout)
        
        # Should call factory to get available scrapers
        mock_factory.get_available_scrapers.assert_called_once()


class TestScrapeNewsCommandIntegration(BaseTestCase):
    """Integration tests for scrape_news command"""
    
    @patch('ai_news.src.management.commands.scrape_news.NewsOrchestrationService')
    @patch('ai_news.src.management.commands.scrape_news.ScraperFactory')
    def test_full_scraping_workflow(self, mock_factory, mock_service_class):
        """Test complete scraping workflow"""
        
        # Mock available sources
        mock_factory.get_available_scrapers.return_value = ['openai_blog', 'hackernews']
        
        # Mock service
        mock_service = Mock()
        mock_service.scrape_all_sources.return_value = {
            'openai_blog': 3,
            'hackernews': 5
        }
        mock_summary = Mock()
        mock_summary.title = 'Generated Daily Summary'
        mock_service.generate_daily_summary.return_value = mock_summary
        mock_service_class.return_value = mock_service
        
        # Execute full workflow
        call_command('scrape_news', '--all', '--generate-summary', stdout=self.stdout)
        
        output = self.stdout.getvalue()
        
        # Should complete full workflow
        self.assertIn('Scraping all available sources', output)
        self.assertIn('Total: 8 new articles', output)
        self.assertIn('Generating daily summary', output)
        self.assertIn('Generated summary: Generated Daily Summary', output)
        
        # Should call all necessary methods
        mock_service.scrape_all_sources.assert_called_once()
        mock_service.generate_daily_summary.assert_called_once()
    
    def test_command_argument_parsing(self):
        """Test command argument parsing and validation"""
        
        # Test invalid combination (both --all and --source)
        with self.assertRaises(SystemExit):
            call_command('scrape_news', '--all', '--source', 'test')
    
    def test_command_help_text(self):
        """Test command help text is informative"""
        
        from django.core.management import get_commands
        from django.core.management.commands.scrape_news import Command
        
        # Command should be registered
        commands = get_commands()
        self.assertIn('scrape_news', commands)
        
        # Help text should be informative
        command = Command()
        self.assertIsNotNone(command.help)
        self.assertIn('Scrape news articles', command.help)