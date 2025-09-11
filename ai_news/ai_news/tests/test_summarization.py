"""
Tests for summarization service functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from ai_news.src.summarization import BlogSummarizer, BlogSummaryService
from ai_news.tests.base import BaseTestCase


class TestBlogSummarizer(BaseTestCase):
    """Test blog summarization functionality"""
    
    def setUp(self):
        super().setUp()
        
        # Mock OpenAI client
        self.mock_llm = Mock()
        self.mock_llm.invoke.return_value.content = "Generated summary content"
        
        with patch('ai_news.src.summarization.ChatOpenAI', return_value=self.mock_llm):
            self.summarizer = BlogSummarizer(model="gpt-4o-mini")
    
    def test_summarizer_initialization(self):
        """Test summarizer initialization"""
        
        self.assertEqual(self.summarizer.model, "gpt-4o-mini")
        self.assertEqual(self.summarizer.temperature, 0.7)
        self.assertIsNotNone(self.summarizer.llm)
    
    def test_create_summary_single_article(self):
        """Test creating summary from single article"""
        
        articles = [self.create_mock_article_data()]
        
        summary = self.summarizer.create_summary(articles, "AI News")
        
        # Should return summary
        self.assertIsNotNone(summary)
        self.assertIn("Generated summary content", summary)
        
        # Should have called LLM
        self.mock_llm.invoke.assert_called()
    
    def test_create_summary_multiple_articles(self):
        """Test creating summary from multiple articles"""
        
        articles = self.create_mock_articles_list(count=5)
        
        summary = self.summarizer.create_summary(articles, "AI News")
        
        self.assertIsNotNone(summary)
        self.mock_llm.invoke.assert_called()
    
    def test_create_summary_empty_articles(self):
        """Test creating summary with empty articles list"""
        
        summary = self.summarizer.create_summary([], "AI News")
        
        # Should handle empty list gracefully
        self.assertIsNone(summary)
    
    @patch('ai_news.src.summarization.load_summarize_chain')
    def test_modern_map_reduce_summarize(self, mock_load_chain):
        """Test modern map-reduce summarization"""
        
        # Mock the map-reduce chain
        mock_chain = Mock()
        mock_chain.run.return_value = "Map-reduce summary result"
        mock_load_chain.return_value = mock_chain
        
        articles = self.create_mock_articles_list(count=10)  # Large number for map-reduce
        
        # Mock Document creation
        with patch('ai_news.src.summarization.Document') as mock_document:
            mock_docs = [Mock() for _ in range(10)]
            mock_document.side_effect = mock_docs
            
            result = self.summarizer._modern_map_reduce_summarize(mock_docs, "AI News")
            
            self.assertEqual(result, "Map-reduce summary result")
            mock_load_chain.assert_called()
    
    def test_prepare_articles_for_summarization(self):
        """Test preparing articles for summarization"""
        
        articles = self.create_mock_articles_list(count=3)
        
        # Mock the document preparation
        with patch('ai_news.src.summarization.Document') as mock_document:
            prepared_docs = self.summarizer._prepare_articles_for_summarization(articles)
            
            # Should create documents for each article
            self.assertEqual(mock_document.call_count, 3)
    
    def test_summarizer_error_handling(self):
        """Test summarizer handles errors gracefully"""
        
        # Mock LLM error
        self.mock_llm.invoke.side_effect = Exception("API Error")
        
        articles = [self.create_mock_article_data()]
        
        summary = self.summarizer.create_summary(articles, "AI News")
        
        # Should handle error and return None or fallback
        self.assertIsNone(summary)


class TestBlogSummaryService(BaseTestCase):
    """Test blog summary service functionality"""
    
    def setUp(self):
        super().setUp()
        
        # Mock dependencies
        self.mock_summarizer = Mock()
        self.mock_summarizer.create_summary.return_value = "Generated blog summary"
        
        with patch('ai_news.src.summarization.BlogSummarizer', return_value=self.mock_summarizer):
            self.service = BlogSummaryService()
    
    def test_service_initialization(self):
        """Test service initialization"""
        
        self.assertIsNotNone(self.service.summarizer)
        self.assertEqual(self.service.model, "gpt-4o-mini")
    
    @patch('ai_news.models.NewsArticle.objects.filter')
    @patch('ai_news.models.BlogSummary.objects.create')
    def test_create_daily_summary(self, mock_create_summary, mock_filter_articles):
        """Test creating daily summary"""
        
        # Mock articles from today
        mock_articles = self.create_mock_articles_list(count=3)
        mock_filter_articles.return_value = mock_articles
        
        # Mock created summary
        mock_summary = Mock()
        mock_summary.id = 1
        mock_summary.title = "Daily AI News Summary"
        mock_create_summary.return_value = mock_summary
        
        result = self.service.create_daily_summary("AI News")
        
        # Should create summary
        self.assertEqual(result, mock_summary)
        mock_create_summary.assert_called_once()
        
        # Should filter articles correctly (today's articles)
        mock_filter_articles.assert_called()
        filter_args = mock_filter_articles.call_args
        self.assertTrue(any('published_date__date' in str(arg) for arg in filter_args))
    
    @patch('ai_news.models.NewsArticle.objects.filter')
    @patch('ai_news.models.BlogSummary.objects.create')
    def test_create_weekly_summary(self, mock_create_summary, mock_filter_articles):
        """Test creating weekly summary"""
        
        mock_articles = self.create_mock_articles_list(count=10)
        mock_filter_articles.return_value = mock_articles
        
        mock_summary = Mock()
        mock_summary.id = 2
        mock_summary.title = "Weekly AI News Summary"
        mock_create_summary.return_value = mock_summary
        
        result = self.service.create_weekly_summary("AI News")
        
        self.assertEqual(result, mock_summary)
        mock_create_summary.assert_called_once()
        
        # Should filter for past week
        mock_filter_articles.assert_called()
    
    @patch('ai_news.models.NewsArticle.objects.filter')
    def test_create_summary_no_articles(self, mock_filter_articles):
        """Test creating summary when no articles exist"""
        
        # Mock no articles
        mock_filter_articles.return_value = []
        
        result = self.service.create_daily_summary("AI News")
        
        # Should return None when no articles
        self.assertIsNone(result)
    
    @patch('ai_news.models.NewsArticle.objects.filter')
    @patch('ai_news.models.BlogSummary.objects.create')
    def test_create_summary_with_article_association(self, mock_create_summary, mock_filter_articles):
        """Test that summary is properly associated with articles"""
        
        mock_articles = self.create_mock_articles_list(count=2)
        mock_filter_articles.return_value = mock_articles
        
        # Mock summary with articles relationship
        mock_summary = Mock()
        mock_summary.articles = Mock()
        mock_summary.articles.set = Mock()
        mock_create_summary.return_value = mock_summary
        
        result = self.service.create_daily_summary("AI News")
        
        # Should associate articles with summary
        mock_summary.articles.set.assert_called_with(mock_articles)
    
    def test_generate_summary_title(self):
        """Test summary title generation"""
        
        # Test daily title
        daily_title = self.service._generate_summary_title("daily", "AI News")
        self.assertIn("Daily", daily_title)
        self.assertIn("AI News", daily_title)
        
        # Test weekly title
        weekly_title = self.service._generate_summary_title("weekly", "Machine Learning")
        self.assertIn("Weekly", weekly_title)
        self.assertIn("Machine Learning", weekly_title)
        
        # Test with current date
        from datetime import date
        today = date.today()
        daily_title = self.service._generate_summary_title("daily", "AI")
        self.assertIn(str(today.year), daily_title)
    
    @patch('ai_news.models.NewsArticle.objects.filter')
    def test_create_summary_error_handling(self, mock_filter_articles):
        """Test summary creation error handling"""
        
        mock_articles = self.create_mock_articles_list(count=2)
        mock_filter_articles.return_value = mock_articles
        
        # Mock summarizer error
        self.mock_summarizer.create_summary.side_effect = Exception("Summarization failed")
        
        result = self.service.create_daily_summary("AI News")
        
        # Should handle error gracefully
        self.assertIsNone(result)
    
    def test_service_with_different_models(self):
        """Test service with different LLM models"""
        
        # Test with different model
        with patch('ai_news.src.summarization.BlogSummarizer') as mock_summarizer_class:
            service = BlogSummaryService(model="gpt-4", temperature=0.5)
            
            # Should initialize summarizer with correct parameters
            mock_summarizer_class.assert_called_with(model="gpt-4", temperature=0.5)


class TestSummarizationIntegration(BaseTestCase):
    """Integration tests for summarization components"""
    
    @patch('ai_news.src.summarization.ChatOpenAI')
    def test_full_summarization_pipeline(self, mock_openai):
        """Test complete summarization pipeline"""
        
        # Mock OpenAI response
        mock_llm = Mock()
        mock_llm.invoke.return_value.content = "Complete pipeline summary"
        mock_openai.return_value = mock_llm
        
        # Create service
        service = BlogSummaryService()
        
        # Create test articles
        articles = self.create_mock_articles_list(count=3)
        
        # Test summarization
        with patch('ai_news.models.NewsArticle.objects.filter', return_value=articles), \
             patch('ai_news.models.BlogSummary.objects.create') as mock_create:
            
            mock_summary = Mock()
            mock_summary.articles = Mock()
            mock_create.return_value = mock_summary
            
            result = service.create_daily_summary("AI News")
            
            # Should complete full pipeline
            self.assertIsNotNone(result)
            mock_llm.invoke.assert_called()
            mock_create.assert_called_once()
    
    def test_summarization_with_various_article_content_lengths(self):
        """Test summarization with different content lengths"""
        
        with patch('ai_news.src.summarization.ChatOpenAI') as mock_openai:
            mock_llm = Mock()
            mock_llm.invoke.return_value.content = "Variable length summary"
            mock_openai.return_value = mock_llm
            
            summarizer = BlogSummarizer()
            
            # Test with short articles
            short_articles = [
                self.create_mock_article_data(content="Short content")
            ]
            
            # Test with long articles  
            long_articles = [
                self.create_mock_article_data(content="Very long content " * 100)
            ]
            
            short_summary = summarizer.create_summary(short_articles, "Test")
            long_summary = summarizer.create_summary(long_articles, "Test")
            
            # Both should produce summaries
            self.assertIsNotNone(short_summary)
            self.assertIsNotNone(long_summary)
    
    def test_concurrent_summarization_safety(self):
        """Test that summarization is thread-safe"""
        
        import threading
        
        with patch('ai_news.src.summarization.ChatOpenAI') as mock_openai:
            mock_llm = Mock()
            mock_llm.invoke.return_value.content = "Thread-safe summary"
            mock_openai.return_value = mock_llm
            
            summarizer = BlogSummarizer()
            results = []
            
            def summarize_articles():
                articles = self.create_mock_articles_list(count=2)
                summary = summarizer.create_summary(articles, "Concurrent Test")
                results.append(summary)
            
            # Run multiple threads
            threads = []
            for _ in range(3):
                t = threading.Thread(target=summarize_articles)
                threads.append(t)
                t.start()
            
            # Wait for completion
            for t in threads:
                t.join()
            
            # All should complete successfully
            self.assertEqual(len(results), 3)
            self.assertTrue(all(r is not None for r in results))