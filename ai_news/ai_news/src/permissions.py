"""
Custom DRF permissions and throttling for AI News API
Provides enhanced security controls beyond default DRF functionality
"""
from rest_framework import permissions
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.core.cache import cache
import logging
from typing import Optional

# Security imports
from .security import SecurityAuditor

logger = logging.getLogger(__name__)


class SecureAPIPermission(permissions.BasePermission):
    """
    Custom permission class with security logging and validation.
    Currently allows all requests but logs access for monitoring.
    """
    
    def has_permission(self, request, view) -> bool:
        """
        Check if user has permission to access the API.
        
        Args:
            request: HTTP request object
            view: DRF view instance
            
        Returns:
            bool: Permission granted
        """
        # Get client information for security logging
        client_ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')[:200]
        
        # Log API access for security monitoring
        SecurityAuditor.log_security_event(
            "api_permission_check",
            {
                "endpoint": request.path,
                "method": request.method,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "view_name": view.__class__.__name__
            },
            "info"
        )
        
        # For now, allow all requests (can be restricted in production)
        return True
    
    def get_client_ip(self, request) -> str:
        """Extract client IP address from request headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'


class APIKeyPermission(permissions.BasePermission):
    """
    Optional API key authentication permission.
    Disabled by default but can be enabled for production.
    """
    
    def has_permission(self, request, view) -> bool:
        """
        Check API key in request headers.
        Currently disabled - returns True always.
        """
        # FUTURE: Enable API key authentication for production
        # 
        # from django.conf import settings
        # api_key = request.META.get('HTTP_X_API_KEY')
        # 
        # if not api_key:
        #     SecurityAuditor.log_security_event(
        #         "api_key_missing",
        #         {"client_ip": self.get_client_ip(request), "endpoint": request.path},
        #         "warning"
        #     )
        #     return False
        # 
        # if api_key != settings.API_KEY:
        #     SecurityAuditor.log_security_event(
        #         "api_key_invalid", 
        #         {"client_ip": self.get_client_ip(request), "provided_key": api_key[:10]},
        #         "error"
        #     )
        #     return False
        
        return True  # Open API for now
    
    def get_client_ip(self, request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'


class SecurityAwareAnonRateThrottle(AnonRateThrottle):
    """
    Enhanced anonymous rate throttling with security logging.
    Extends DRF's AnonRateThrottle with security event logging.
    """
    
    def throttle_failure(self, request, exception=None):
        """
        Called when throttle limit is exceeded.
        Logs security event for monitoring potential abuse.
        """
        client_ip = self.get_client_ip(request)
        
        # Calculate wait time for retry
        wait_time = self.wait()
        
        # Log rate limit violation for security monitoring
        SecurityAuditor.log_security_event(
            "api_rate_limit_exceeded",
            {
                "client_ip": client_ip,
                "endpoint": request.path,
                "method": request.method,
                "rate_limit": self.get_rate(),
                "wait_time": wait_time,
                "user_agent": request.META.get('HTTP_USER_AGENT', 'unknown')[:200]
            },
            "warning"
        )
        
        # Call parent method
        return super().throttle_failure(request, exception)
    
    def get_client_ip(self, request) -> str:
        """Get client IP for throttling and logging."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'anonymous'


class SecurityAwareUserRateThrottle(UserRateThrottle):
    """
    Enhanced user rate throttling with security logging.
    For future authenticated API usage.
    """
    
    def throttle_failure(self, request, exception=None):
        """Log authenticated user rate limit violations."""
        user_id = getattr(request.user, 'id', 'anonymous')
        
        SecurityAuditor.log_security_event(
            "api_user_rate_limit_exceeded",
            {
                "user_id": user_id,
                "endpoint": request.path,
                "method": request.method,
                "rate_limit": self.get_rate(),
                "wait_time": self.wait()
            },
            "warning"
        )
        
        return super().throttle_failure(request, exception)


class BurstRateThrottle(AnonRateThrottle):
    """
    Burst protection throttle - prevents rapid successive requests.
    Allows 10 requests per minute to prevent DoS attacks.
    """
    rate = '10/min'
    scope = 'burst'
    
    def throttle_failure(self, request, exception=None):
        """Log burst rate limit violations."""
        client_ip = self.get_client_ip(request)
        
        SecurityAuditor.log_security_event(
            "api_burst_rate_limit_exceeded",
            {
                "client_ip": client_ip,
                "endpoint": request.path,
                "burst_limit": "10/min",
                "wait_time": self.wait()
            },
            "error"  # Higher severity for burst protection
        )
        
        return super().throttle_failure(request, exception)
    
    def get_client_ip(self, request) -> str:
        """Get client IP for burst throttling."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'anonymous'