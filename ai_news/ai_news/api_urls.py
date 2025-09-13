"""
URL configuration for AI News REST API endpoints
Uses Django REST Framework with proper class-based views
"""
from django.urls import path

from ai_news.ai_news.api_views import (
    LatestSummaryAPIView,
    SummaryListAPIView, 
    SummaryDetailAPIView,
    SystemStatusAPIView,
    api_root
)

# DRF API URL patterns with versioning
urlpatterns = [
    # API v1 root
    path('api/v1/', api_root, name='api_root'),
    
    # Summary endpoints
    path('api/v1/summaries/latest/', LatestSummaryAPIView.as_view(), name='api_latest_summary'),
    path('api/v1/summaries/', SummaryListAPIView.as_view(), name='api_summary_list'),
    path('api/v1/summaries/<int:summary_id>/', SummaryDetailAPIView.as_view(), name='api_summary_detail'),
    
    # System status
    path('api/v1/status/', SystemStatusAPIView.as_view(), name='api_status'),
    
    # Convenience endpoints without versioning (backwards compatibility)
    path('api/latest-summary/', LatestSummaryAPIView.as_view(), name='api_latest_summary_no_version'),
    path('api/status/', SystemStatusAPIView.as_view(), name='api_status_no_version'),
    path('api/summaries/', SummaryListAPIView.as_view(), name='api_summary_list_no_version'),
]