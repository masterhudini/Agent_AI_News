"""
Django REST Framework API Views for AI News Application
Provides secure, scalable API endpoints using DRF best practices
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, throttle_classes, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.http import Http404
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional

# Local imports
from .models import BlogSummary, NewsArticle
from .serializers import (
    BlogSummaryDetailSerializer, BlogSummaryListSerializer,
    SystemStatusSerializer, APIResponseSerializer, APIErrorSerializer
)
from .src.permissions import (
    SecureAPIPermission, SecurityAwareAnonRateThrottle, BurstRateThrottle
)
from .src.security import SecurityAuditor

logger = logging.getLogger(__name__)


class BaseSecureAPIView(APIView):
    """
    Base API view with security features and standardized responses.
    All API views should inherit from this class.
    """
    
    # Default security settings
    permission_classes = [SecureAPIPermission]
    throttle_classes = [SecurityAwareAnonRateThrottle, BurstRateThrottle]
    
    def get_client_ip(self) -> str:
        """Extract client IP from request."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip or 'unknown'
    
    def build_response(self, data: Any, success: bool = True, 
                      metadata: Optional[Dict] = None) -> Response:
        """
        Build standardized API response with metadata.
        
        Args:
            data: Response data
            success: Success status
            metadata: Additional metadata
            
        Returns:
            Response: Standardized DRF response
        """
        if metadata is None:
            metadata = {}
        
        # Add standard metadata
        metadata.update({
            'generated_at': datetime.now().isoformat(),
            'api_version': '1.0'
        })
        
        response_data = {
            'success': success,
            'data': data,
            'metadata': metadata
        }
        
        return Response(response_data)
    
    def build_error_response(self, error: str, message: str, 
                           status_code: int = 400, retry_after: Optional[int] = None) -> Response:
        """
        Build standardized error response.
        
        Args:
            error: Error type/code
            message: Human-readable error message
            status_code: HTTP status code
            retry_after: Seconds to wait before retry (for rate limiting)
            
        Returns:
            Response: Standardized error response
        """
        error_data = {
            'success': False,
            'error': error,
            'message': message
        }
        
        if retry_after:
            error_data['retry_after'] = retry_after
        
        return Response(error_data, status=status_code)
    
    def handle_exception(self, exc):
        """
        Custom exception handling with security logging.
        """
        # Log API errors for monitoring (without exposing internal details)
        SecurityAuditor.log_security_event(
            "api_exception",
            {
                "endpoint": self.request.path,
                "client_ip": self.get_client_ip(),
                "exception_type": type(exc).__name__,
                "view_name": self.__class__.__name__
            },
            "error"
        )
        
        # Handle common exceptions with user-friendly messages
        if isinstance(exc, Http404):
            return self.build_error_response(
                "not_found",
                "The requested resource was not found.",
                404
            )
        
        # Generic error response (don't expose internal details)
        return self.build_error_response(
            "internal_error",
            "An unexpected error occurred. Please try again later.",
            500
        )


class LatestSummaryAPIView(BaseSecureAPIView):
    """
    API view to retrieve the latest news summary.
    
    GET /api/v1/summaries/latest/
    
    Returns the most recent AI news summary with comprehensive metadata.
    Includes security features, caching, and rate limiting.
    """
    
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, request, *args, **kwargs):
        """
        Get the latest news summary.
        
        Returns:
            Response: Latest summary with metadata
        """
        try:
            # Get the most recent summary
            try:
                latest_summary = BlogSummary.objects.prefetch_related('articles').latest('created_date')
            except BlogSummary.DoesNotExist:
                return self.build_error_response(
                    "no_summaries",
                    "No news summaries have been generated yet. Please try again later.",
                    404
                )
            
            # Serialize the summary with security sanitization
            serializer = BlogSummaryDetailSerializer(
                latest_summary, 
                context={'request': request}
            )
            
            # Add additional metadata
            metadata = {
                'cache_expires': (datetime.now() + timedelta(minutes=5)).isoformat(),
                'total_sources': len(serializer.data.get('sources', [])),
                'endpoint': 'latest_summary'
            }
            
            # Log successful API access
            SecurityAuditor.log_security_event(
                "api_success",
                {
                    "endpoint": "/api/v1/summaries/latest/",
                    "client_ip": self.get_client_ip(),
                    "summary_id": latest_summary.id,
                    "response_size": len(str(serializer.data))
                },
                "info"
            )
            
            return self.build_response(serializer.data, metadata=metadata)
            
        except Exception as e:
            logger.error(f"Error in LatestSummaryAPIView: {e}")
            return self.handle_exception(e)


class SummaryListAPIView(BaseSecureAPIView, generics.ListAPIView):
    """
    API view to list recent summaries with pagination.
    
    GET /api/v1/summaries/
    
    Returns paginated list of recent summaries with basic information.
    """
    
    serializer_class = BlogSummaryListSerializer
    permission_classes = [SecureAPIPermission]
    throttle_classes = [SecurityAwareAnonRateThrottle]
    
    def get_queryset(self):
        """
        Get queryset of recent summaries.
        Optimized query with prefetch_related for performance.
        """
        return BlogSummary.objects.prefetch_related('articles').order_by('-created_date')
    
    @method_decorator(cache_page(60 * 10))  # Cache for 10 minutes
    def list(self, request, *args, **kwargs):
        """
        List summaries with standardized response format.
        """
        try:
            # Get paginated queryset
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                paginated_response = self.get_paginated_response(serializer.data)
                
                # Wrap in standardized format
                return self.build_response(
                    paginated_response.data,
                    metadata={
                        'endpoint': 'summary_list',
                        'cache_expires': (datetime.now() + timedelta(minutes=10)).isoformat()
                    }
                )
            
            serializer = self.get_serializer(queryset, many=True)
            return self.build_response(
                serializer.data,
                metadata={'endpoint': 'summary_list'}
            )
            
        except Exception as e:
            logger.error(f"Error in SummaryListAPIView: {e}")
            return self.handle_exception(e)


class SystemStatusAPIView(BaseSecureAPIView):
    """
    System status and health check API view.
    
    GET /api/v1/status/
    
    Provides basic system statistics without exposing sensitive information.
    """
    
    @method_decorator(cache_page(60 * 10))  # Cache for 10 minutes
    def get(self, request, *args, **kwargs):
        """
        Get system status and basic statistics.
        
        Returns:
            Response: System health information
        """
        try:
            # Calculate system statistics
            total_summaries = BlogSummary.objects.count()
            total_articles = NewsArticle.objects.count()
            unique_articles = NewsArticle.objects.filter(is_duplicate=False).count()
            
            # Get available sources count
            from .src.parsers import ScraperFactory
            available_sources = len(ScraperFactory.get_available_scrapers())
            
            # Calculate latest summary age
            latest_summary_age = "No summaries yet"
            try:
                latest_summary = BlogSummary.objects.latest('created_date')
                age_delta = datetime.now() - latest_summary.created_date.replace(tzinfo=None)
                
                if age_delta.days > 0:
                    latest_summary_age = f"{age_delta.days} days ago"
                elif age_delta.seconds > 3600:
                    hours = age_delta.seconds // 3600
                    latest_summary_age = f"{hours} hours ago"
                else:
                    minutes = age_delta.seconds // 60
                    latest_summary_age = f"{minutes} minutes ago"
            except BlogSummary.DoesNotExist:
                pass
            
            # Build status data (no sensitive information)
            status_data = {
                'status': 'healthy',
                'total_summaries': total_summaries,
                'latest_summary_age': latest_summary_age,
                'available_sources': available_sources,
                'system_uptime': 'operational',
                'total_articles': total_articles,
                'unique_articles': unique_articles,
                'deduplication_rate': f"{((total_articles - unique_articles) / max(total_articles, 1)) * 100:.1f}%" if total_articles > 0 else "0%"
            }
            
            # Serialize status data
            serializer = SystemStatusSerializer(status_data)
            
            # Add metadata
            metadata = {
                'cache_expires': (datetime.now() + timedelta(minutes=10)).isoformat(),
                'endpoint': 'system_status'
            }
            
            return self.build_response(serializer.data, metadata=metadata)
            
        except Exception as e:
            logger.error(f"Error in SystemStatusAPIView: {e}")
            
            # Return minimal error status
            error_status = {
                'status': 'error',
                'message': 'Unable to retrieve system status'
            }
            
            return self.build_response(
                error_status, 
                success=False,
                metadata={'endpoint': 'system_status'}
            )


class SummaryDetailAPIView(BaseSecureAPIView):
    """
    API view to retrieve a specific summary by ID.
    
    GET /api/v1/summaries/{id}/
    
    Returns detailed information about a specific summary.
    """
    
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes (longer for specific summaries)
    def get(self, request, summary_id, *args, **kwargs):
        """
        Get detailed information about a specific summary.
        
        Args:
            summary_id: ID of the summary to retrieve
            
        Returns:
            Response: Detailed summary information
        """
        try:
            # Get specific summary
            try:
                summary = BlogSummary.objects.prefetch_related('articles').get(id=summary_id)
            except BlogSummary.DoesNotExist:
                return self.build_error_response(
                    "summary_not_found",
                    f"Summary with ID {summary_id} was not found.",
                    404
                )
            
            # Serialize with full details
            serializer = BlogSummaryDetailSerializer(
                summary,
                context={'request': request}
            )
            
            # Add metadata
            metadata = {
                'cache_expires': (datetime.now() + timedelta(minutes=15)).isoformat(),
                'endpoint': 'summary_detail',
                'summary_id': summary_id
            }
            
            # Log access to specific summary
            SecurityAuditor.log_security_event(
                "api_summary_detail_access",
                {
                    "summary_id": summary_id,
                    "client_ip": self.get_client_ip(),
                    "endpoint": f"/api/v1/summaries/{summary_id}/"
                },
                "info"
            )
            
            return self.build_response(serializer.data, metadata=metadata)
            
        except Exception as e:
            logger.error(f"Error in SummaryDetailAPIView: {e}")
            return self.handle_exception(e)


# Optional: Function-based view for simple endpoints (keeping for backwards compatibility)
@api_view(['GET'])
@throttle_classes([SecurityAwareAnonRateThrottle])
@permission_classes([SecureAPIPermission])
def api_root(request):
    """
    API root endpoint with available endpoints information.
    
    GET /api/v1/
    
    Returns information about available API endpoints.
    """
    try:
        endpoints = {
            'summaries_latest': request.build_absolute_uri('/api/v1/summaries/latest/'),
            'summaries_list': request.build_absolute_uri('/api/v1/summaries/'),
            'summary_detail': request.build_absolute_uri('/api/v1/summaries/{id}/'),
            'status': request.build_absolute_uri('/api/v1/status/'),
        }
        
        api_info = {
            'api_version': '1.0',
            'description': 'AI News API - Secure access to news summaries',
            'endpoints': endpoints,
            'rate_limits': {
                'anonymous': '100 requests per hour',
                'burst_protection': '10 requests per minute'
            },
            'security_features': [
                'Rate limiting',
                'Input sanitization', 
                'Security headers',
                'Request logging',
                'Response caching'
            ]
        }
        
        response_data = {
            'success': True,
            'data': api_info,
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'api_version': '1.0'
            }
        }
        
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"Error in api_root: {e}")
        return Response({
            'success': False,
            'error': 'internal_error',
            'message': 'Unable to load API information'
        }, status=500)