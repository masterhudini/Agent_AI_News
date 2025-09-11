"""
Tests for langchain_analysis management command
"""

import unittest
from unittest.mock import Mock, patch, call
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from ai_news.tests.base import BaseTestCase


class TestLangChainAnalysisCommand(BaseTestCase):
    """Test langchain_analysis management command"""
    
    def setUp(self):
        super().setUp()
        self.stdout = StringIO()
        self.stderr = StringIO()
    
    @patch('ai_news.src.management.commands.langchain_analysis.NewsOrchestrationService')
    def test_interactive_query(self, mock_service_class):
        """Test --query option for interactive querying"""
        
        mock_service = Mock()
        mock_service.interactive_news_query.return_value = "AI is trending with new developments in LLMs"
        mock_service_class.return_value = mock_service
        
        call_command(
            'langchain_analysis', 
            '--query', 'What are the latest AI trends?',
            stdout=self.stdout
        )
        
        output = self.stdout.getvalue()
        
        # Should process query and display response
        self.assertIn('Processing query: What are the latest AI trends?', output)
        self.assertIn('AI is trending with new developments in LLMs', output)
        
        # Should call service method
        mock_service.interactive_news_query.assert_called_once_with('What are the latest AI trends?')
    
    @patch('ai_news.src.management.commands.langchain_analysis.NewsOrchestrationService')
    def test_search_similar_articles(self, mock_service_class):
        """Test --search option for finding similar articles"""
        
        mock_service = Mock()
        
        # Create mock articles
        mock_articles = [
            Mock(title='Machine Learning Breakthrough', source='OpenAI Blog', 
                 url='http://example.com/1', published_date='2023-01-01'),
            Mock(title='Deep Learning Advances', source='Google AI', 
                 url='http://example.com/2', published_date='2023-01-02')
        ]
        mock_service.search_similar_articles.return_value = mock_articles
        mock_service_class.return_value = mock_service
        
        call_command(
            'langchain_analysis',
            '--search', 'machine learning',
            '--limit', '5',
            stdout=self.stdout
        )
        
        output = self.stdout.getvalue()
        
        # Should display search results
        self.assertIn('Searching for articles similar to: machine learning', output)
        self.assertIn('Found 2 similar articles:', output)
        self.assertIn('Machine Learning Breakthrough (OpenAI Blog)', output)
        self.assertIn('Deep Learning Advances (Google AI)', output)
        
        # Should call service with correct parameters
        mock_service.search_similar_articles.assert_called_once_with('machine learning', limit=5)
    
    @patch('ai_news.src.management.commands.langchain_analysis.NewsOrchestrationService')
    def test_search_no_results(self, mock_service_class):
        """Test search when no similar articles found"""
        
        mock_service = Mock()
        mock_service.search_similar_articles.return_value = []
        mock_service_class.return_value = mock_service
        
        call_command('langchain_analysis', '--search', 'nonexistent topic', stdout=self.stdout)
        
        output = self.stdout.getvalue()
        
        # Should handle no results gracefully
        self.assertIn('No similar articles found', output)
    
    @patch('ai_news.src.management.commands.langchain_analysis.NewsOrchestrationService')
    @patch('ai_news.models.NewsArticle')
    def test_analyze_articles(self, mock_article_model, mock_service_class):
        """Test --analyze option for article analysis"""
        
        # Mock articles from database
        mock_articles = [
            Mock(title='AI Research Paper', source='arXiv', id=1),
            Mock(title='ML Implementation Guide', source='Tech Blog', id=2)
        ]
        mock_queryset = Mock()
        mock_queryset.filter.return_value.order_by.return_value.__getitem__.return_value = mock_articles
        mock_article_model.objects = mock_queryset
        
        # Mock analysis results
        mock_analysis_results = [
            {
                'article': mock_articles[0],
                'analysis': {
                    'category': 'Research',
                    'importance_score': 0.9,
                    'key_topics': ['AI', 'Research'],
                    'summary': 'Important AI research findings'
                }
            },
            {
                'article': mock_articles[1], 
                'analysis': {
                    'category': 'Tutorial',
                    'importance_score': 0.7,
                    'key_topics': ['ML', 'Implementation'],
                    'summary': 'Practical ML implementation guide'
                }
            }
        ]
        
        mock_service = Mock()
        mock_service.analyze_articles_with_langchain.return_value = mock_analysis_results
        mock_service_class.return_value = mock_service
        
        call_command(
            'langchain_analysis',
            '--analyze',
            '--topic', 'AI Research',
            '--limit', '10',
            stdout=self.stdout
        )
        
        output = self.stdout.getvalue()
        
        # Should display analysis results
        self.assertIn('Analyzing recent articles about AI Research', output)
        self.assertIn('Analyzed 2 articles:', output)
        self.assertIn('--- AI Research Paper ---', output)
        self.assertIn('Category: Research', output)
        self.assertIn('Importance Score: 0.9', output)
        self.assertIn('Key Topics: AI, Research', output)
        self.assertIn('Summary: Important AI research findings', output)
        
        # Should call analysis with correct articles
        mock_service.analyze_articles_with_langchain.assert_called_once_with(mock_articles)
    
    @patch('ai_news.models.NewsArticle')
    def test_analyze_no_articles(self, mock_article_model):
        """Test analysis when no articles are found"""
        
        # Mock empty queryset
        mock_queryset = Mock()
        mock_queryset.filter.return_value.order_by.return_value.__getitem__.return_value = []
        mock_article_model.objects = mock_queryset
        
        call_command('langchain_analysis', '--analyze', stdout=self.stdout)
        
        output = self.stdout.getvalue()
        
        # Should handle no articles gracefully
        self.assertIn('No articles found to analyze', output)
    
    @patch('ai_news.src.management.commands.langchain_analysis.NewsOrchestrationService')
    def test_intelligent_summary_creation(self, mock_service_class):
        """Test --intelligent-summary option"""
        
        mock_summary = Mock()
        mock_summary.title = 'Weekly AI Insights'
        mock_summary.id = 123
        mock_summary.articles.count.return_value = 15
        mock_summary.summary = 'This week saw significant developments in AI research...' * 10  # Long summary
        
        mock_service = Mock()
        mock_service.create_intelligent_blog_summary.return_value = mock_summary
        mock_service_class.return_value = mock_service
        
        call_command(
            'langchain_analysis',
            '--intelligent-summary',
            '--topic', 'Weekly AI',
            stdout=self.stdout
        )
        
        output = self.stdout.getvalue()
        
        # Should display summary creation results
        self.assertIn('Creating intelligent blog summary for Weekly AI', output)
        self.assertIn('Successfully created intelligent summary: Weekly AI Insights', output)
        self.assertIn('Summary ID: 123', output)
        self.assertIn('Articles included: 15', output)
        self.assertIn('Preview:', output)
        
        # Should call service with correct topic
        mock_service.create_intelligent_blog_summary.assert_called_once_with('Weekly AI')
    
    @patch('ai_news.src.management.commands.langchain_analysis.NewsOrchestrationService')
    def test_intelligent_summary_failure(self, mock_service_class):
        """Test intelligent summary when no summary is generated"""
        
        mock_service = Mock()
        mock_service.create_intelligent_blog_summary.return_value = None
        mock_service_class.return_value = mock_service
        
        call_command('langchain_analysis', '--intelligent-summary', stdout=self.stdout)
        
        output = self.stdout.getvalue()
        
        # Should handle failure gracefully
        self.assertIn('No intelligent summary generated', output)
        self.assertIn('possibly no new articles found', output)
    
    def test_no_options_provided(self):
        """Test command when no action options are provided"""
        
        call_command('langchain_analysis', stdout=self.stdout, stderr=self.stderr)
        
        output = self.stderr.getvalue()
        
        # Should show error and examples
        self.assertIn('Please specify an action', output)
        self.assertIn('Examples:', output)
        self.assertIn('--query', output)
        self.assertIn('--search', output)
        self.assertIn('--analyze', output)
        self.assertIn('--intelligent-summary', output)
    
    @patch('ai_news.src.management.commands.langchain_analysis.NewsOrchestrationService')
    def test_custom_model_parameter(self, mock_service_class):
        """Test using custom model parameter"""
        
        mock_service = Mock()
        mock_service.interactive_news_query.return_value = "Response from custom model"
        mock_service_class.return_value = mock_service
        
        call_command(
            'langchain_analysis',
            '--query', 'Test query',
            '--model', 'gpt-4',
            stdout=self.stdout
        )
        
        # Should initialize service with custom model
        mock_service_class.assert_called_once_with(llm_model='gpt-4')
        
        output = self.stdout.getvalue()
        self.assertIn('using gpt-4', output)
    
    @patch('ai_news.src.management.commands.langchain_analysis.NewsOrchestrationService')
    def test_default_parameters(self, mock_service_class):
        """Test command uses correct default parameters"""
        
        mock_service = Mock()
        mock_service.interactive_news_query.return_value = "Default response"
        mock_service_class.return_value = mock_service
        
        call_command('langchain_analysis', '--query', 'Test', stdout=self.stdout)
        
        # Should use default model
        mock_service_class.assert_called_once_with(llm_model='gpt-4o-mini')
    
    @patch('ai_news.src.management.commands.langchain_analysis.NewsOrchestrationService')
    def test_service_error_handling(self, mock_service_class):
        """Test error handling when service methods fail"""
        
        mock_service = Mock()
        mock_service.interactive_news_query.side_effect = Exception("Service error")
        mock_service_class.return_value = mock_service
        
        # Should not crash, but may show error
        call_command('langchain_analysis', '--query', 'Test query', stdout=self.stdout)
        
        # Service error should be handled (might be logged or displayed)
        mock_service.interactive_news_query.assert_called_once()
    
    def test_command_argument_validation(self):
        """Test command argument validation"""
        
        # Test limit parameter validation
        call_command(
            'langchain_analysis',
            '--search', 'test',
            '--limit', '5',
            stdout=self.stdout
        )
        
        # Should accept valid limit
        self.assertTrue(True)  # If we get here, validation passed
    
    @patch('ai_news.src.management.commands.langchain_analysis.NewsOrchestrationService')
    def test_topic_parameter_usage(self, mock_service_class):
        """Test --topic parameter in various contexts"""
        
        mock_service = Mock()
        mock_service.create_intelligent_blog_summary.return_value = Mock(
            title='Custom Topic Summary', id=1, articles=Mock(count=Mock(return_value=5)),
            summary='Summary content'
        )
        mock_service_class.return_value = mock_service
        
        call_command(
            'langchain_analysis',
            '--intelligent-summary',
            '--topic', 'Custom AI Topic',
            stdout=self.stdout
        )
        
        # Should use custom topic
        mock_service.create_intelligent_blog_summary.assert_called_once_with('Custom AI Topic')


class TestLangChainAnalysisCommandIntegration(BaseTestCase):
    """Integration tests for langchain_analysis command"""
    
    def test_command_help_text(self):
        """Test command has informative help text"""
        
        from django.core.management.commands.langchain_analysis import Command
        
        command = Command()
        self.assertIsNotNone(command.help)
        self.assertIn('LangChain', command.help)
    
    def test_argument_parser_configuration(self):
        """Test argument parser is configured correctly"""
        
        from django.core.management.commands.langchain_analysis import Command
        
        command = Command()
        parser = command.create_parser('test', 'langchain_analysis')
        
        # Should have all expected arguments
        actions = [action.dest for action in parser._actions]
        self.assertIn('query', actions)
        self.assertIn('search', actions)
        self.assertIn('analyze', actions)
        self.assertIn('intelligent_summary', actions)
        self.assertIn('topic', actions)
        self.assertIn('limit', actions)
        self.assertIn('model', actions)
    
    @patch('ai_news.src.management.commands.langchain_analysis.NewsOrchestrationService')
    def test_full_analysis_workflow(self, mock_service_class):
        """Test complete analysis workflow"""
        
        # Setup comprehensive mock service
        mock_service = Mock()
        
        # Mock query response
        mock_service.interactive_news_query.return_value = "Comprehensive analysis response"
        
        # Mock search results
        mock_articles = [Mock(title='Article 1', source='Source 1', url='http://1', published_date='2023-01-01')]
        mock_service.search_similar_articles.return_value = mock_articles
        
        # Mock analysis results
        mock_service.analyze_articles_with_langchain.return_value = [
            {'article': mock_articles[0], 'analysis': {'category': 'AI', 'importance_score': 0.8}}
        ]
        
        # Mock summary creation
        mock_summary = Mock(title='Generated Summary', id=99, articles=Mock(count=Mock(return_value=3)))
        mock_summary.summary = 'Generated summary content'
        mock_service.create_intelligent_blog_summary.return_value = mock_summary
        
        mock_service_class.return_value = mock_service
        
        # Test each major function
        # 1. Query
        call_command('langchain_analysis', '--query', 'Test query', stdout=StringIO())
        mock_service.interactive_news_query.assert_called()
        
        # 2. Search
        call_command('langchain_analysis', '--search', 'AI', stdout=StringIO())
        mock_service.search_similar_articles.assert_called()
        
        # 3. Summary
        call_command('langchain_analysis', '--intelligent-summary', stdout=StringIO())
        mock_service.create_intelligent_blog_summary.assert_called()
        
        # All functions should work without errors
        self.assertTrue(True)