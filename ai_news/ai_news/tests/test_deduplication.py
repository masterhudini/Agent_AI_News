"""
Tests for deduplication service functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import hashlib

from ai_news.src.deduplication import (
    ContentHashDeduplicator, 
    VectorDeduplicator, 
    DuplicationService
)
from ai_news.tests.base import BaseTestCase, mock_qdrant_client, mock_openai_embedding_response


class TestContentHashDeduplicator(BaseTestCase):
    """Test content hash-based deduplication"""
    
    def setUp(self):
        super().setUp()
        self.deduplicator = ContentHashDeduplicator()
    
    def test_content_hash_generation(self):
        """Test content hash generation"""
        
        content = "This is test content for hashing"
        hash_result = self.deduplicator.generate_content_hash(content)
        
        # Should return SHA256 hash
        expected_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        self.assertEqual(hash_result, expected_hash)
        self.assertEqual(len(hash_result), 64)  # SHA256 produces 64-char hex string
    
    def test_content_hash_consistency(self):
        """Test that same content produces same hash"""
        
        content = "Consistent content for testing"
        
        hash1 = self.deduplicator.generate_content_hash(content)
        hash2 = self.deduplicator.generate_content_hash(content)
        
        self.assertEqual(hash1, hash2)
    
    def test_different_content_different_hash(self):
        """Test that different content produces different hashes"""
        
        content1 = "First piece of content"
        content2 = "Second piece of content"
        
        hash1 = self.deduplicator.generate_content_hash(content1)
        hash2 = self.deduplicator.generate_content_hash(content2)
        
        self.assertNotEqual(hash1, hash2)
    
    def test_empty_content_hash(self):
        """Test hash generation for empty content"""
        
        empty_hash = self.deduplicator.generate_content_hash("")
        
        self.assertIsNotNone(empty_hash)
        self.assertEqual(len(empty_hash), 64)
    
    @patch('ai_news.models.NewsArticle.objects.filter')
    def test_check_duplicate_exists(self, mock_filter):
        """Test checking if duplicate exists"""
        
        # Mock existing article
        mock_filter.return_value.exists.return_value = True
        
        content = "Test content for duplicate check"
        is_duplicate = self.deduplicator.is_duplicate_content(content)
        
        self.assertTrue(is_duplicate)
        
        # Verify correct hash was used in query
        expected_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        mock_filter.assert_called_with(content_hash=expected_hash)
    
    @patch('ai_news.models.NewsArticle.objects.filter')
    def test_check_duplicate_not_exists(self, mock_filter):
        """Test checking when no duplicate exists"""
        
        # Mock no existing article
        mock_filter.return_value.exists.return_value = False
        
        content = "Unique content"
        is_duplicate = self.deduplicator.is_duplicate_content(content)
        
        self.assertFalse(is_duplicate)


class TestVectorDeduplicator(BaseTestCase):
    """Test vector-based semantic deduplication"""
    
    def setUp(self):
        super().setUp()
        
        # Mock dependencies
        self.mock_client = mock_qdrant_client()
        self.mock_embeddings = Mock()
        self.mock_embeddings.embed_query.return_value = mock_openai_embedding_response()
        
        with patch('ai_news.src.deduplication.QdrantClient', return_value=self.mock_client), \
             patch('ai_news.src.deduplication.OpenAIEmbeddings', return_value=self.mock_embeddings):
            
            self.deduplicator = VectorDeduplicator()
    
    def test_vector_deduplicator_initialization(self):
        """Test vector deduplicator initialization"""
        
        self.assertEqual(self.deduplicator.collection_name, 'news_articles')
        self.assertEqual(self.deduplicator.similarity_threshold, 0.85)
        self.assertIsNotNone(self.deduplicator.client)
        self.assertIsNotNone(self.deduplicator.embeddings)
    
    @patch('ai_news.src.deduplication.QdrantVectorStore')
    def test_add_article_to_index(self, mock_vector_store):
        """Test adding article to vector index"""
        
        article = self.create_mock_article_data()
        
        # Mock vector store
        mock_store_instance = Mock()
        mock_vector_store.return_value = mock_store_instance
        
        self.deduplicator.add_article_to_index(article.title, article.content, article_id=1)
        
        # Should create embedding and add to store
        self.mock_embeddings.embed_query.assert_called()
    
    def test_search_similar_articles(self):
        """Test searching for similar articles"""
        
        query = "Test search query"
        
        # Mock search results
        self.mock_client.search.return_value = [
            Mock(id='1', score=0.9, payload={'article_id': 1, 'title': 'Similar Article 1'}),
            Mock(id='2', score=0.87, payload={'article_id': 2, 'title': 'Similar Article 2'})
        ]
        
        results = self.deduplicator.search_similar_articles(query, limit=5)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['article_id'], 1)
        self.assertEqual(results[0]['score'], 0.9)
    
    def test_is_duplicate_content_similar(self):
        """Test duplicate detection with similar content"""
        
        content = "Test content for similarity"
        
        # Mock high similarity result
        self.mock_client.search.return_value = [
            Mock(id='1', score=0.9, payload={'article_id': 1})  # Above threshold
        ]
        
        is_duplicate = self.deduplicator.is_duplicate_content(content)
        
        self.assertTrue(is_duplicate)
    
    def test_is_duplicate_content_not_similar(self):
        """Test duplicate detection with dissimilar content"""
        
        content = "Unique content"
        
        # Mock low similarity result
        self.mock_client.search.return_value = [
            Mock(id='1', score=0.7, payload={'article_id': 1})  # Below threshold
        ]
        
        is_duplicate = self.deduplicator.is_duplicate_content(content)
        
        self.assertFalse(is_duplicate)
    
    def test_is_duplicate_content_no_results(self):
        """Test duplicate detection with no similar results"""
        
        content = "Completely unique content"
        
        # Mock no results
        self.mock_client.search.return_value = []
        
        is_duplicate = self.deduplicator.is_duplicate_content(content)
        
        self.assertFalse(is_duplicate)
    
    def test_remove_article_from_index(self):
        """Test removing article from vector index"""
        
        article_id = 123
        
        self.deduplicator.remove_article_from_index(article_id)
        
        # Should call delete on client
        self.mock_client.delete.assert_called()


class TestDuplicationService(BaseTestCase):
    """Test main duplication service orchestrator"""
    
    def setUp(self):
        super().setUp()
        
        # Mock the deduplicators
        self.mock_content_deduplicator = Mock()
        self.mock_vector_deduplicator = Mock()
        
        with patch('ai_news.src.deduplication.ContentHashDeduplicator', return_value=self.mock_content_deduplicator), \
             patch('ai_news.src.deduplication.VectorDeduplicator', return_value=self.mock_vector_deduplicator):
            
            self.service = DuplicationService()
    
    def test_service_initialization(self):
        """Test service initialization"""
        
        self.assertIsNotNone(self.service.content_deduplicator)
        self.assertIsNotNone(self.service.vector_deduplicator)
    
    @patch('ai_news.models.NewsArticle.objects.filter')
    def test_process_article_exact_duplicate(self, mock_filter):
        """Test processing article that is exact duplicate"""
        
        # Mock article
        mock_article = Mock()
        mock_article.content = "Test content"
        mock_article.save = Mock()
        
        # Mock exact duplicate found
        self.mock_content_deduplicator.is_duplicate_content.return_value = True
        
        result = self.service.process_article_for_duplicates(mock_article)
        
        # Should be marked as duplicate
        self.assertTrue(result)
        self.assertTrue(mock_article.is_duplicate)
        mock_article.save.assert_called()
    
    @patch('ai_news.models.NewsArticle.objects.filter')
    def test_process_article_semantic_duplicate(self, mock_filter):
        """Test processing article that is semantic duplicate"""
        
        # Mock article
        mock_article = Mock()
        mock_article.content = "Test content"
        mock_article.title = "Test title"
        mock_article.id = 1
        mock_article.save = Mock()
        
        # Mock no exact duplicate but semantic duplicate
        self.mock_content_deduplicator.is_duplicate_content.return_value = False
        self.mock_vector_deduplicator.is_duplicate_content.return_value = True
        
        result = self.service.process_article_for_duplicates(mock_article)
        
        # Should be marked as duplicate
        self.assertTrue(result)
        self.assertTrue(mock_article.is_duplicate)
    
    @patch('ai_news.models.NewsArticle.objects.filter')
    def test_process_article_unique(self, mock_filter):
        """Test processing unique article"""
        
        # Mock article
        mock_article = Mock()
        mock_article.content = "Unique content"
        mock_article.title = "Unique title"
        mock_article.id = 1
        mock_article.save = Mock()
        
        # Mock no duplicates found
        self.mock_content_deduplicator.is_duplicate_content.return_value = False
        self.mock_vector_deduplicator.is_duplicate_content.return_value = False
        
        result = self.service.process_article_for_duplicates(mock_article)
        
        # Should not be marked as duplicate
        self.assertFalse(result)
        self.assertFalse(mock_article.is_duplicate)
        
        # Should be added to vector index
        self.mock_vector_deduplicator.add_article_to_index.assert_called_with(
            mock_article.title, mock_article.content, article_id=mock_article.id
        )
    
    def test_search_similar_content(self):
        """Test searching for similar content"""
        
        query = "Search query"
        
        # Mock search results from vector deduplicator
        mock_results = [{'article_id': 1, 'score': 0.9, 'title': 'Similar Article'}]
        self.mock_vector_deduplicator.search_similar_articles.return_value = mock_results
        
        # Mock database query
        with patch('ai_news.models.NewsArticle.objects.filter') as mock_filter:
            mock_articles = [Mock(id=1, title='Similar Article')]
            mock_filter.return_value = mock_articles
            
            results = self.service.search_similar_content(query, limit=5)
            
            self.assertEqual(results, mock_articles)
            self.mock_vector_deduplicator.search_similar_articles.assert_called_with(query, limit=5)
    
    def test_service_error_handling(self):
        """Test service handles errors gracefully"""
        
        mock_article = Mock()
        mock_article.content = "Test content"
        mock_article.save = Mock()
        
        # Mock error in content deduplicator
        self.mock_content_deduplicator.is_duplicate_content.side_effect = Exception("Deduplication error")
        
        # Should handle error gracefully and not crash
        result = self.service.process_article_for_duplicates(mock_article)
        
        # Should default to not duplicate on error
        self.assertFalse(result)