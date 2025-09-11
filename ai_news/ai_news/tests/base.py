"""
Base test classes and utilities for AI News Scraper tests
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

from django.test import TestCase
from django.utils import timezone

from ai_news.src.parsers.base import NewsArticleData


class BaseTestCase(TestCase):
    """Base test case with common utilities"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.maxDiff = None
        
    def create_mock_article_data(self, **kwargs) -> NewsArticleData:
        """Create mock NewsArticleData for testing"""
        defaults = {
            'title': 'Test AI Article',
            'content': 'This is a test article about artificial intelligence and machine learning.',
            'url': 'https://example.com/test-article',
            'source': 'Test Source',
            'published_date': timezone.now(),
            'author': 'Test Author'
        }
        defaults.update(kwargs)
        return NewsArticleData(**defaults)
    
    def create_mock_articles_list(self, count: int = 5) -> List[NewsArticleData]:
        """Create a list of mock articles for testing"""
        articles = []
        for i in range(count):
            articles.append(self.create_mock_article_data(
                title=f'Test Article {i+1}',
                content=f'Content for article {i+1} about AI and ML topics.',
                url=f'https://example.com/article-{i+1}',
                published_date=timezone.now() - timedelta(hours=i)
            ))
        return articles
    
    def create_mock_rss_entry(self, **kwargs) -> Dict[str, Any]:
        """Create mock RSS entry for testing RSS parsers"""
        defaults = {
            'title': 'Mock RSS Entry',
            'summary': 'This is a mock RSS entry for testing purposes.',
            'link': 'https://example.com/rss-entry',
            'published': timezone.now().isoformat(),
            'author': 'Mock Author'
        }
        defaults.update(kwargs)
        return defaults
    
    def create_mock_rss_feed(self, entry_count: int = 3) -> Mock:
        """Create mock RSS feed with entries"""
        mock_feed = Mock()
        mock_feed.entries = []
        
        for i in range(entry_count):
            entry = self.create_mock_rss_entry(
                title=f'RSS Entry {i+1}',
                summary=f'Summary for RSS entry {i+1}',
                link=f'https://example.com/rss-entry-{i+1}'
            )
            mock_feed.entries.append(Mock(**entry))
        
        return mock_feed
    
    def create_mock_openai_response(self, **kwargs) -> Dict[str, Any]:
        """Create mock OpenAI API response"""
        defaults = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'key_topics': ['AI', 'Machine Learning'],
                        'importance_score': 0.8,
                        'category': 'Technology',
                        'summary': 'Mock AI article summary'
                    })
                }
            }]
        }
        defaults.update(kwargs)
        return defaults
    
    def create_mock_qdrant_response(self, **kwargs) -> List[Dict]:
        """Create mock Qdrant search response"""
        defaults = [{
            'id': 'mock-id-1',
            'score': 0.85,
            'payload': {
                'article_id': 1,
                'title': 'Mock Similar Article',
                'content': 'Mock content for similar article'
            }
        }]
        return defaults


class MockRequestsResponse:
    """Mock requests.Response object"""
    
    def __init__(self, json_data: Dict = None, status_code: int = 200, text: str = ""):
        self._json_data = json_data or {}
        self.status_code = status_code
        self.text = text
        
    def json(self):
        return self._json_data
    
    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise Exception(f"HTTP {self.status_code}")


class MockDjangoModel:
    """Mock Django model for testing"""
    
    def __init__(self, **kwargs):
        self.objects = Mock()
        for key, value in kwargs.items():
            setattr(self, key, value)
        
    def save(self):
        pass
    
    def delete(self):
        pass


def mock_feedparser_parse(url: str) -> Mock:
    """Mock feedparser.parse function"""
    mock_feed = Mock()
    mock_feed.entries = [
        Mock(
            title='Mock Feed Entry 1',
            summary='Mock summary 1',
            link='https://example.com/1',
            published='2023-01-01T00:00:00Z',
            author='Mock Author 1'
        ),
        Mock(
            title='Mock Feed Entry 2', 
            summary='Mock summary 2',
            link='https://example.com/2',
            published='2023-01-02T00:00:00Z',
            author='Mock Author 2'
        )
    ]
    return mock_feed


def mock_openai_embedding_response() -> List[float]:
    """Mock OpenAI embedding response"""
    return [0.1] * 1536  # Mock 1536-dimensional embedding


def mock_qdrant_client():
    """Mock Qdrant client"""
    client = Mock()
    client.search.return_value = [
        Mock(
            id='mock-1',
            score=0.85,
            payload={'article_id': 1, 'title': 'Mock Article 1'}
        )
    ]
    client.upsert.return_value = Mock(status='completed')
    client.delete.return_value = Mock(status='completed')
    return client