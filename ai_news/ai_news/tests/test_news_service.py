"""
Tests for news service orchestration functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from ai_news.src.news_service import NewsOrchestrationService
from ai_news.tests.base import BaseTestCase


class TestNewsOrchestrationService(BaseTestCase):
    """Test main news orchestration service"""
    
    def setUp(self):
        super().setUp()
        
        # Mock all dependencies
        self.mock_deduplication_service = Mock()
        self.mock_blog_summary_service = Mock()
        self.mock_langchain_orchestrator = Mock()
        
        with patch('ai_news.src.news_service.DuplicationService', return_value=self.mock_deduplication_service), \
             patch('ai_news.src.news_service.BlogSummaryService', return_value=self.mock_blog_summary_service), \
             patch('ai_news.src.news_service.LangChainNewsOrchestrator', return_value=self.mock_langchain_orchestrator):
            
            self.service = NewsOrchestrationService()
    
    def test_service_initialization(self):
        """Test service initialization with parameters"""
        
        self.assertIsNotNone(self.service.duplication_service)
        self.assertIsNotNone(self.service.blog_summary_service)
        self.assertIsNotNone(self.service.langchain_orchestrator)
    
    def test_service_initialization_with_custom_params(self):
        """Test service initialization with custom parameters"""
        
        with patch('ai_news.src.news_service.DuplicationService') as mock_dedup, \
             patch('ai_news.src.news_service.BlogSummaryService') as mock_blog, \
             patch('ai_news.src.news_service.LangChainNewsOrchestrator') as mock_lang:
            
            service = NewsOrchestrationService(
                embedding_model="text-embedding-3-large",
                llm_model="gpt-4",
                temperature=0.5
            )
            
            # Should initialize with custom parameters
            mock_dedup.assert_called_with(model="text-embedding-3-large")
            mock_blog.assert_called_with(model="gpt-4", temperature=0.5)
    
    @patch('ai_news.src.news_service.ScraperFactory')
    def test_scrape_all_sources(self, mock_factory):
        """Test scraping all available sources"""
        
        # Mock available scrapers
        mock_factory.get_available_scrapers.return_value = ['source1', 'source2', 'source3']
        
        # Mock scraping results
        self.service.scrape_single_source = Mock(side_effect=[5, 3, 7])
        
        results = self.service.scrape_all_sources()
        
        # Should return results for all sources
        expected_results = {
            'source1': 5,
            'source2': 3,
            'source3': 7
        }
        self.assertEqual(results, expected_results)
    
    @patch('ai_news.src.news_service.ScraperFactory')
    def test_scrape_all_sources_with_errors(self, mock_factory):
        """Test scraping all sources with some errors"""
        
        mock_factory.get_available_scrapers.return_value = ['good_source', 'bad_source']
        
        # Mock one successful, one error
        def mock_scrape_side_effect(source_name):
            if source_name == 'good_source':
                return 10
            else:
                raise Exception("Scraping error")
        
        self.service.scrape_single_source = Mock(side_effect=mock_scrape_side_effect)
        
        results = self.service.scrape_all_sources()
        
        # Should handle errors gracefully
        self.assertEqual(results['good_source'], 10)
        self.assertEqual(results['bad_source'], 0)
    
    @patch('ai_news.src.news_service.ScraperFactory')
    @patch('ai_news.models.NewsArticle')
    def test_scrape_single_source_success(self, mock_article_model, mock_factory):
        """Test successful single source scraping"""
        
        # Mock scraper
        mock_scraper = Mock()
        mock_articles_data = [
            Mock(title='Article 1', content='Content 1', url='http://example.com/1',
                 source='Test Source', published_date=datetime.now(), author='Author 1'),
            Mock(title='Article 2', content='Content 2', url='http://example.com/2',
                 source='Test Source', published_date=datetime.now(), author='Author 2')
        ]
        mock_scraper.scrape.return_value = mock_articles_data
        mock_factory.create_scraper.return_value = mock_scraper
        
        # Mock database operations
        mock_article_model.objects.filter.return_value.exists.return_value = False
        mock_article_instance = Mock()
        mock_article_model.return_value = mock_article_instance
        
        # Mock deduplication (not duplicates)
        self.mock_deduplication_service.process_article_for_duplicates.return_value = False
        
        result = self.service.scrape_single_source('test_source')
        
        # Should return count of new articles
        self.assertEqual(result, 2)
        
        # Should process deduplication for each article
        self.assertEqual(self.mock_deduplication_service.process_article_for_duplicates.call_count, 2)
    
    @patch('ai_news.src.news_service.ScraperFactory')
    @patch('ai_news.models.NewsArticle')
    def test_scrape_single_source_with_duplicates(self, mock_article_model, mock_factory):
        """Test single source scraping with duplicate detection"""
        
        mock_scraper = Mock()
        mock_articles_data = [
            Mock(title='New Article', content='Content', url='http://example.com/new',
                 source='Test', published_date=datetime.now(), author='Author'),
            Mock(title='Duplicate Article', content='Duplicate', url='http://example.com/dup',
                 source='Test', published_date=datetime.now(), author='Author')
        ]
        mock_scraper.scrape.return_value = mock_articles_data
        mock_factory.create_scraper.return_value = mock_scraper
        
        # Mock no existing URL duplicates
        mock_article_model.objects.filter.return_value.exists.return_value = False
        mock_article_model.return_value = Mock()
        
        # Mock deduplication results (one duplicate, one not)
        self.mock_deduplication_service.process_article_for_duplicates.side_effect = [False, True]
        
        result = self.service.scrape_single_source('test_source')
        
        # Should return count of unique articles only
        self.assertEqual(result, 1)
    
    @patch('ai_news.src.news_service.ScraperFactory')
    def test_scrape_single_source_error_handling(self, mock_factory):
        """Test single source scraping error handling"""
        
        # Mock scraper that raises error
        mock_factory.create_scraper.side_effect = Exception("Scraper creation failed")
        
        result = self.service.scrape_single_source('failing_source')
        
        # Should return 0 on error
        self.assertEqual(result, 0)
    
    def test_generate_daily_summary(self):
        """Test daily summary generation"""
        
        mock_summary = Mock()
        mock_summary.title = "Daily AI Summary"
        self.mock_blog_summary_service.create_daily_summary.return_value = mock_summary
        
        result = self.service.generate_daily_summary("AI News")
        
        self.assertEqual(result, mock_summary)
        self.mock_blog_summary_service.create_daily_summary.assert_called_with("AI News")
    
    def test_generate_weekly_summary(self):
        """Test weekly summary generation"""
        
        mock_summary = Mock()
        mock_summary.title = "Weekly AI Summary"
        self.mock_blog_summary_service.create_weekly_summary.return_value = mock_summary
        
        result = self.service.generate_weekly_summary("AI News")
        
        self.assertEqual(result, mock_summary)
        self.mock_blog_summary_service.create_weekly_summary.assert_called_with("AI News")
    
    @patch('ai_news.models.NewsArticle')
    def test_run_full_pipeline(self, mock_article_model):
        """Test complete news pipeline execution"""
        
        # Mock scraping results
        self.service.scrape_all_sources = Mock(return_value={
            'source1': 5,
            'source2': 3
        })
        
        # Mock database counts
        mock_article_model.objects.filter.side_effect = [
            Mock(count=Mock(return_value=8)),    # unique articles
            Mock(count=Mock(return_value=2))     # duplicates
        ]
        
        # Mock summary generation
        mock_daily = Mock()
        mock_weekly = Mock()
        self.service.generate_daily_summary = Mock(return_value=mock_daily)
        self.service.generate_weekly_summary = Mock(return_value=mock_weekly)
        
        results = self.service.run_full_pipeline(generate_summary=True)
        
        # Should return complete results
        expected_structure = {
            'scraping_results',
            'daily_summary', 
            'weekly_summary',
            'total_unique_articles',
            'total_duplicates'
        }
        self.assertEqual(set(results.keys()), expected_structure)
        
        # Should have correct counts
        self.assertEqual(results['total_unique_articles'], 8)
        self.assertEqual(results['total_duplicates'], 2)
        
        # Should generate summaries
        self.assertEqual(results['daily_summary'], mock_daily)
        self.assertEqual(results['weekly_summary'], mock_weekly)
    
    def test_run_full_pipeline_no_summaries(self):
        """Test pipeline without summary generation"""
        
        self.service.scrape_all_sources = Mock(return_value={'source1': 1})
        
        with patch('ai_news.models.NewsArticle') as mock_model:
            mock_model.objects.filter.side_effect = [
                Mock(count=Mock(return_value=1)),
                Mock(count=Mock(return_value=0))
            ]
            
            results = self.service.run_full_pipeline(generate_summary=False)
            
            # Should not generate summaries
            self.assertIsNone(results['daily_summary'])
            self.assertIsNone(results['weekly_summary'])
    
    @patch('ai_news.models.NewsArticle')
    def test_get_latest_articles(self, mock_article_model):
        """Test getting latest articles"""
        
        mock_articles = [Mock(), Mock(), Mock()]
        mock_queryset = Mock()
        mock_queryset.order_by.return_value.__getitem__.return_value = mock_articles
        mock_article_model.objects.all.return_value = mock_queryset
        
        result = self.service.get_latest_articles(limit=3, unique_only=True)
        
        self.assertEqual(result, mock_articles)
        
        # Should filter for unique articles
        mock_queryset.filter.assert_called_with(is_duplicate=False)
    
    @patch('ai_news.models.NewsArticle')
    def test_get_articles_by_source(self, mock_article_model):
        """Test getting articles by source"""
        
        mock_articles = [Mock(), Mock()]
        mock_queryset = Mock()
        mock_queryset.filter.return_value.order_by.return_value.__getitem__.return_value = mock_articles
        mock_article_model.objects = mock_queryset
        
        result = self.service.get_articles_by_source('OpenAI Blog', limit=10)
        
        self.assertEqual(result, mock_articles)
        
        # Should filter by source and unique articles
        mock_queryset.filter.assert_called_with(
            source='OpenAI Blog',
            is_duplicate=False
        )
    
    @patch('ai_news.models.NewsArticle')
    @patch('ai_news.models.BlogSummary')
    @patch('ai_news.src.news_service.ScraperFactory')
    def test_get_statistics(self, mock_factory, mock_blog_model, mock_article_model):
        """Test getting comprehensive statistics"""
        
        # Mock article counts
        mock_article_model.objects.count.return_value = 100
        mock_article_model.objects.filter.side_effect = [
            Mock(count=Mock(return_value=85)),  # unique
            Mock(count=Mock(return_value=15))   # duplicates
        ]
        
        # Mock source statistics
        mock_article_model.objects.values_list.return_value.distinct.return_value = ['Source1', 'Source2']
        
        def mock_source_filter(**kwargs):
            if kwargs.get('source') == 'Source1':
                return Mock(count=Mock(return_value=60))
            else:
                return Mock(count=Mock(return_value=40))
        
        mock_article_model.objects.filter = Mock(side_effect=mock_source_filter)
        
        # Mock other data
        mock_blog_model.objects.count.return_value = 10
        mock_factory.get_available_scrapers.return_value = ['scraper1', 'scraper2']
        
        result = self.service.get_statistics()
        
        # Should return comprehensive stats
        self.assertEqual(result['total_articles'], 100)
        self.assertEqual(result['unique_articles'], 85)
        self.assertEqual(result['duplicates'], 15)
        self.assertEqual(result['duplicate_rate'], 15.0)
        self.assertIn('source_statistics', result)
        self.assertEqual(result['total_summaries'], 10)
    
    @patch('ai_news.models.NewsArticle')
    def test_cleanup_old_articles(self, mock_article_model):
        """Test cleaning up old articles"""
        
        # Mock old articles
        old_articles = [Mock(id=1), Mock(id=2), Mock(id=3)]
        mock_queryset = Mock()
        mock_queryset.filter.return_value = old_articles
        mock_queryset.count.return_value = 3
        mock_queryset.delete.return_value = None
        mock_article_model.objects = mock_queryset
        
        # Mock vector index removal
        self.mock_deduplication_service.vector_deduplicator.remove_article_from_index = Mock()
        
        result = self.service.cleanup_old_articles(days=30)
        
        # Should return count of cleaned articles
        self.assertEqual(result, 3)
        
        # Should remove from vector index
        removal_calls = self.mock_deduplication_service.vector_deduplicator.remove_article_from_index.call_args_list
        self.assertEqual(len(removal_calls), 3)
    
    @patch('ai_news.models.NewsArticle')
    @patch('ai_news.models.BlogSummary')
    def test_create_intelligent_blog_summary(self, mock_blog_model, mock_article_model):
        """Test creating intelligent blog summary"""
        
        # Mock recent articles
        mock_articles = [Mock(), Mock()]
        mock_article_model.objects.filter.return_value.order_by.return_value = mock_articles
        
        # Mock LangChain result
        mock_langchain_result = {
            'blog_post': {
                'title': 'AI News Summary',
                'introduction': 'Recent developments...',
                'main_content': 'Key insights...',
                'conclusion': 'Looking forward...'
            },
            'analyzed_articles': []
        }
        self.mock_langchain_orchestrator.create_intelligent_blog_post.return_value = mock_langchain_result
        
        # Mock blog summary creation
        mock_summary = Mock()
        mock_summary.articles = Mock()
        mock_blog_model.objects.create.return_value = mock_summary
        
        result = self.service.create_intelligent_blog_summary("AI News")
        
        # Should return created summary
        self.assertEqual(result, mock_summary)
        
        # Should create with LangChain content
        create_call = mock_blog_model.objects.create.call_args
        self.assertEqual(create_call[1]['title'], 'AI News Summary')
        self.assertIn('Recent developments', create_call[1]['summary'])
        
        # Should associate articles
        mock_summary.articles.set.assert_called_with(mock_articles)
    
    def test_search_similar_articles(self):
        """Test searching for similar articles"""
        
        mock_results = [Mock(), Mock()]
        self.mock_deduplication_service.search_similar_content.return_value = mock_results
        
        result = self.service.search_similar_articles("AI query", limit=5)
        
        self.assertEqual(result, mock_results)
        self.mock_deduplication_service.search_similar_content.assert_called_with("AI query", 5)
    
    def test_analyze_articles_with_langchain(self):
        """Test analyzing articles with LangChain"""
        
        mock_analysis_results = [
            {'article': Mock(), 'analysis': {'category': 'AI'}},
            {'article': Mock(), 'analysis': {'category': 'ML'}}
        ]
        self.mock_langchain_orchestrator.process_articles_with_analysis.return_value = mock_analysis_results
        
        articles = [Mock(), Mock()]
        result = self.service.analyze_articles_with_langchain(articles)
        
        self.assertEqual(result, mock_analysis_results)
        self.mock_langchain_orchestrator.process_articles_with_analysis.assert_called_with(articles)
    
    def test_interactive_news_query(self):
        """Test interactive news query"""
        
        self.mock_langchain_orchestrator.interactive_news_query.return_value = "Query response"
        
        result = self.service.interactive_news_query("What's trending in AI?")
        
        self.assertEqual(result, "Query response")
        self.mock_langchain_orchestrator.interactive_news_query.assert_called_with("What's trending in AI?")


class TestNewsServiceIntegration(BaseTestCase):
    """Integration tests for news service"""
    
    def test_service_component_initialization_chain(self):
        """Test that service properly initializes all components"""
        
        with patch('ai_news.src.news_service.DuplicationService') as mock_dedup, \
             patch('ai_news.src.news_service.BlogSummaryService') as mock_blog, \
             patch('ai_news.src.news_service.LangChainNewsOrchestrator') as mock_lang:
            
            service = NewsOrchestrationService()
            
            # Should initialize all components
            mock_dedup.assert_called_once()
            mock_blog.assert_called_once()
            mock_lang.assert_called_once()
    
    def test_error_propagation_and_handling(self):
        """Test error handling across service methods"""
        
        with patch('ai_news.src.news_service.DuplicationService'), \
             patch('ai_news.src.news_service.BlogSummaryService'), \
             patch('ai_news.src.news_service.LangChainNewsOrchestrator'):
            
            service = NewsOrchestrationService()
            
            # Test methods handle errors gracefully
            service.duplication_service.search_similar_content.side_effect = Exception("Search error")
            
            result = service.search_similar_articles("query")
            self.assertEqual(result, [])  # Should return empty list on error
    
    @patch('ai_news.src.news_service.logger')
    def test_service_logging(self, mock_logger):
        """Test that service logs appropriately"""
        
        with patch('ai_news.src.news_service.DuplicationService'), \
             patch('ai_news.src.news_service.BlogSummaryService'), \
             patch('ai_news.src.news_service.LangChainNewsOrchestrator'):
            
            service = NewsOrchestrationService()
            
            # Mock scraping to trigger logging
            service.scrape_all_sources = Mock(return_value={'source1': 5})
            
            with patch('ai_news.models.NewsArticle') as mock_model:
                mock_model.objects.filter.side_effect = [Mock(count=Mock(return_value=5)), Mock(count=Mock(return_value=0))]
                
                service.run_full_pipeline()
                
                # Should log pipeline execution
                mock_logger.info.assert_called()