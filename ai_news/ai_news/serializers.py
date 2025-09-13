"""
Django REST Framework serializers for AI News API
Provides secure data serialization with input validation and sanitization
"""
from rest_framework import serializers
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

# Security imports
from .src.security import InputSanitizer, SecurityAuditor

logger = logging.getLogger(__name__)


class NewsArticleBasicSerializer(serializers.Serializer):
    """
    Basic serializer for NewsArticle model - minimal data exposure.
    Used for nested serialization in summary responses.
    """
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=500, read_only=True)
    source = serializers.CharField(max_length=200, read_only=True)
    url = serializers.URLField(read_only=True)
    published_date = serializers.DateTimeField(read_only=True)
    
    def to_representation(self, instance):
        """
        Custom representation with security sanitization.
        Ensures all output is safe from prompt injection and XSS.
        """
        data = super().to_representation(instance)
        
        # SECURITY: Sanitize all text fields before sending to client
        if data.get('title'):
            data['title'] = InputSanitizer.sanitize_text_for_llm(
                data['title'], max_length=500, strict=False
            )
        
        if data.get('source'):
            data['source'] = InputSanitizer.sanitize_text_for_llm(
                data['source'], max_length=200, strict=False
            )
        
        return data


class BlogSummaryDetailSerializer(serializers.Serializer):
    """
    Detailed serializer for BlogSummary model with related articles.
    Provides comprehensive summary data with security features.
    """
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=500, read_only=True)
    summary = serializers.CharField(read_only=True)
    topic_category = serializers.CharField(max_length=100, read_only=True)
    created_at = serializers.DateTimeField(source='created_date', read_only=True)
    
    # Computed fields
    article_count = serializers.SerializerMethodField()
    sources = serializers.SerializerMethodField()
    
    def get_article_count(self, obj) -> int:
        """Get total number of articles in this summary."""
        return obj.articles.count()
    
    def get_sources(self, obj) -> list:
        """
        Get unique sources from articles, limited for response size.
        Returns up to 20 unique source names.
        """
        articles = obj.articles.all()
        sources = list(set(article.source for article in articles))
        
        # Limit to 20 sources and sanitize each one
        limited_sources = sources[:20]
        sanitized_sources = [
            InputSanitizer.sanitize_text_for_llm(source, max_length=200, strict=False)
            for source in limited_sources
        ]
        
        return sanitized_sources
    
    def to_representation(self, instance):
        """
        Custom representation with comprehensive security sanitization.
        """
        data = super().to_representation(instance)
        
        # SECURITY: Sanitize all text content
        if data.get('title'):
            original_title = data['title']
            data['title'] = InputSanitizer.sanitize_text_for_llm(
                original_title, max_length=500, strict=False
            )
            
            # Log if content was modified during sanitization
            if data['title'] != original_title:
                SecurityAuditor.log_security_event(
                    "api_content_sanitization",
                    {
                        "field": "title",
                        "summary_id": instance.id,
                        "client_ip": getattr(self.context.get('request'), 'META', {}).get('REMOTE_ADDR', 'unknown')
                    },
                    "info"
                )
        
        if data.get('summary'):
            original_summary = data['summary']
            data['summary'] = InputSanitizer.sanitize_text_for_llm(
                original_summary, max_length=10000, strict=False
            )
            
            # Log if summary was sanitized
            if data['summary'] != original_summary:
                SecurityAuditor.log_security_event(
                    "api_content_sanitization",
                    {
                        "field": "summary",
                        "summary_id": instance.id,
                        "content_length": len(original_summary)
                    },
                    "info"
                )
        
        if data.get('topic_category'):
            data['topic_category'] = InputSanitizer.sanitize_text_for_llm(
                data['topic_category'], max_length=100, strict=False
            )
        
        return data


class BlogSummaryListSerializer(serializers.Serializer):
    """
    List serializer for BlogSummary model - minimal data for list views.
    Optimized for performance with reduced data exposure.
    """
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(max_length=500, read_only=True)
    topic_category = serializers.CharField(max_length=100, read_only=True)
    created_at = serializers.DateTimeField(source='created_date', read_only=True)
    article_count = serializers.SerializerMethodField()
    
    def get_article_count(self, obj) -> int:
        """Get article count efficiently."""
        return obj.articles.count()
    
    def to_representation(self, instance):
        """Sanitize list view data."""
        data = super().to_representation(instance)
        
        # Basic sanitization for list view
        if data.get('title'):
            data['title'] = InputSanitizer.sanitize_text_for_llm(
                data['title'], max_length=500, strict=False
            )
        
        return data


class SystemStatusSerializer(serializers.Serializer):
    """
    System status serializer for health check endpoint.
    Provides basic system metrics without exposing sensitive information.
    """
    status = serializers.CharField(read_only=True)
    total_summaries = serializers.IntegerField(read_only=True)
    latest_summary_age = serializers.CharField(read_only=True)
    available_sources = serializers.IntegerField(read_only=True)
    system_uptime = serializers.CharField(read_only=True)
    
    def to_representation(self, instance):
        """
        Generate system status data.
        
        Args:
            instance: Dictionary with system status data
        """
        # If instance is not a dict, create default status
        if not isinstance(instance, dict):
            instance = {
                'status': 'healthy',
                'total_summaries': 0,
                'latest_summary_age': 'No summaries yet',
                'available_sources': 0,
                'system_uptime': 'operational'
            }
        
        return super().to_representation(instance)


class APIResponseSerializer(serializers.Serializer):
    """
    Standard API response wrapper serializer.
    Ensures consistent response format across all endpoints.
    """
    success = serializers.BooleanField(default=True)
    data = serializers.JSONField()
    metadata = serializers.JSONField(required=False)
    error = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)
    
    def to_representation(self, instance):
        """
        Build standardized API response with metadata.
        """
        if not isinstance(instance, dict):
            instance = {'success': True, 'data': instance}
        
        # Add standard metadata
        if 'metadata' not in instance:
            instance['metadata'] = {
                'generated_at': datetime.now().isoformat(),
                'api_version': '1.0'
            }
        
        # Add cache expiration info if not present
        if 'cache_expires' not in instance.get('metadata', {}):
            instance['metadata']['cache_expires'] = (
                datetime.now() + timedelta(minutes=5)
            ).isoformat()
        
        return super().to_representation(instance)


class APIErrorSerializer(serializers.Serializer):
    """
    Error response serializer for consistent error formatting.
    """
    success = serializers.BooleanField(default=False)
    error = serializers.CharField()
    message = serializers.CharField()
    retry_after = serializers.IntegerField(required=False)
    
    def to_representation(self, instance):
        """
        Format error responses consistently.
        """
        if not isinstance(instance, dict):
            instance = {
                'success': False,
                'error': 'Unknown error',
                'message': str(instance)
            }
        
        return super().to_representation(instance)