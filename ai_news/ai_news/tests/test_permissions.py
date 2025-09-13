"""
Tests for DRF permissions and throttling classes
"""
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from ai_news.src.permissions import (
    SecureAPIPermission, APIKeyPermission,
    SecurityAwareAnonRateThrottle, SecurityAwareUserRateThrottle,
    BurstRateThrottle
)


class MockView(APIView):
    """Mock view for testing permissions and throttling."""
    def get(self, request):
        return Response({"message": "success"})


class SecureAPIPermissionTest(TestCase):
    """Tests for SecureAPIPermission class."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.permission = SecureAPIPermission()
        self.view = MockView()
        cache.clear()
    
    def test_has_permission_returns_true(self):
        """Test that permission is granted by default."""
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        
        result = self.permission.has_permission(request, self.view)
        self.assertTrue(result)
    
    @patch('ai_news.src.permissions.SecurityAuditor.log_security_event')
    def test_security_logging_on_permission_check(self, mock_log):
        """Test that security events are logged during permission checks."""
        request = self.factory.get('/test/endpoint/')
        request.user = AnonymousUser()
        request.META['HTTP_USER_AGENT'] = 'Test Browser/1.0'
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        
        result = self.permission.has_permission(request, self.view)
        
        self.assertTrue(result)
        mock_log.assert_called_once_with(
            "api_permission_check",
            {
                "endpoint": "/test/endpoint/",
                "method": "GET",
                "client_ip": "192.168.1.100",
                "user_agent": "Test Browser/1.0",
                "view_name": "MockView"
            },
            "info"
        )
    
    def test_get_client_ip_x_forwarded_for(self):
        """Test client IP extraction from X-Forwarded-For header."""
        request = self.factory.get('/test/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1, 198.51.100.1'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        ip = self.permission.get_client_ip(request)
        self.assertEqual(ip, '203.0.113.1')  # Should use first IP from X-Forwarded-For
    
    def test_get_client_ip_remote_addr(self):
        """Test client IP extraction from REMOTE_ADDR."""
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        ip = self.permission.get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')
    
    def test_get_client_ip_unknown(self):
        """Test client IP when no IP information available."""
        request = self.factory.get('/test/')
        # No IP headers
        
        ip = self.permission.get_client_ip(request)
        self.assertEqual(ip, 'unknown')
    
    def test_user_agent_truncation(self):
        """Test that very long user agents are truncated."""
        long_user_agent = 'A' * 500  # Very long user agent
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        request.META['HTTP_USER_AGENT'] = long_user_agent
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        with patch('ai_news.src.permissions.SecurityAuditor.log_security_event') as mock_log:
            self.permission.has_permission(request, self.view)
            
            # Check that user agent was truncated to 200 characters
            call_args = mock_log.call_args[0][1]
            self.assertEqual(len(call_args['user_agent']), 200)


class APIKeyPermissionTest(TestCase):
    """Tests for APIKeyPermission class."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.permission = APIKeyPermission()
        self.view = MockView()
    
    def test_has_permission_returns_true_by_default(self):
        """Test that API key permission returns True by default (disabled)."""
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        
        result = self.permission.has_permission(request, self.view)
        self.assertTrue(result)
    
    def test_get_client_ip(self):
        """Test client IP extraction in APIKeyPermission."""
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        ip = self.permission.get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')


class SecurityAwareAnonRateThrottleTest(APITestCase):
    """Tests for SecurityAwareAnonRateThrottle class."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.throttle = SecurityAwareAnonRateThrottle()
        self.factory = RequestFactory()
        cache.clear()
    
    def test_throttle_initialization(self):
        """Test throttle initialization."""
        self.assertIsInstance(self.throttle, SecurityAwareAnonRateThrottle)
        self.assertEqual(self.throttle.scope, 'anon')
    
    @patch('ai_news.src.permissions.SecurityAuditor.log_security_event')
    def test_throttle_failure_logging(self, mock_log):
        """Test that throttle failures are logged as security events."""
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Client'
        
        # Mock the throttle to simulate failure
        with patch.object(self.throttle, 'wait', return_value=30.0):
            with patch.object(self.throttle, 'get_rate', return_value='10/min'):
                self.throttle.throttle_failure(request)
        
        mock_log.assert_called_once_with(
            "api_rate_limit_exceeded",
            {
                "client_ip": "192.168.1.1",
                "endpoint": "/test/",
                "method": "GET",
                "rate_limit": "10/min",
                "wait_time": 30.0,
                "user_agent": "Test Client"
            },
            "warning"
        )
    
    def test_get_client_ip_with_proxy(self):
        """Test client IP extraction with proxy headers."""
        request = self.factory.get('/test/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1, 198.51.100.1'
        
        ip = self.throttle.get_client_ip(request)
        self.assertEqual(ip, '203.0.113.1')
    
    def test_get_client_ip_fallback(self):
        """Test client IP extraction fallback."""
        request = self.factory.get('/test/')
        # No IP information available
        
        ip = self.throttle.get_client_ip(request)
        self.assertEqual(ip, 'anonymous')


class SecurityAwareUserRateThrottleTest(APITestCase):
    """Tests for SecurityAwareUserRateThrottle class."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.throttle = SecurityAwareUserRateThrottle()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        cache.clear()
    
    @patch('ai_news.src.permissions.SecurityAuditor.log_security_event')
    def test_throttle_failure_logging_with_user(self, mock_log):
        """Test throttle failure logging for authenticated users."""
        request = self.factory.get('/test/')
        request.user = self.user
        
        # Mock the throttle methods
        with patch.object(self.throttle, 'wait', return_value=60.0):
            with patch.object(self.throttle, 'get_rate', return_value='100/hour'):
                self.throttle.throttle_failure(request)
        
        mock_log.assert_called_once_with(
            "api_user_rate_limit_exceeded",
            {
                "user_id": self.user.id,
                "endpoint": "/test/",
                "method": "GET",
                "rate_limit": "100/hour",
                "wait_time": 60.0
            },
            "warning"
        )
    
    @patch('ai_news.src.permissions.SecurityAuditor.log_security_event')
    def test_throttle_failure_logging_anonymous_user(self, mock_log):
        """Test throttle failure logging for anonymous users."""
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        
        with patch.object(self.throttle, 'wait', return_value=60.0):
            with patch.object(self.throttle, 'get_rate', return_value='100/hour'):
                self.throttle.throttle_failure(request)
        
        # Should log with 'anonymous' as user_id
        call_args = mock_log.call_args[0][1]
        self.assertEqual(call_args['user_id'], 'anonymous')


class BurstRateThrottleTest(APITestCase):
    """Tests for BurstRateThrottle class."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.throttle = BurstRateThrottle()
        self.factory = RequestFactory()
        cache.clear()
    
    def test_burst_throttle_configuration(self):
        """Test burst throttle is configured correctly."""
        self.assertEqual(self.throttle.rate, '10/min')
        self.assertEqual(self.throttle.scope, 'burst')
    
    @patch('ai_news.src.permissions.SecurityAuditor.log_security_event')
    def test_burst_throttle_failure_logging(self, mock_log):
        """Test that burst throttle failures are logged as errors."""
        request = self.factory.get('/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        with patch.object(self.throttle, 'wait', return_value=10.0):
            self.throttle.throttle_failure(request)
        
        mock_log.assert_called_once_with(
            "api_burst_rate_limit_exceeded",
            {
                "client_ip": "192.168.1.1",
                "endpoint": "/test/",
                "burst_limit": "10/min",
                "wait_time": 10.0
            },
            "error"  # Higher severity for burst protection
        )


class ThrottlingIntegrationTest(APITestCase):
    """Integration tests for throttling with real API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        cache.clear()
    
    def test_throttling_headers_in_response(self):
        """Test that throttling information is available in responses."""
        # This would test actual API endpoints with throttling applied
        # Since we can't easily test real throttling in unit tests,
        # we verify the throttling classes are properly configured
        
        from ai_news.api_views import BaseSecureAPIView
        
        # Verify throttle classes are configured
        self.assertIn(SecurityAwareAnonRateThrottle, BaseSecureAPIView.throttle_classes)
        self.assertIn(BurstRateThrottle, BaseSecureAPIView.throttle_classes)
    
    def test_permission_classes_configuration(self):
        """Test that permission classes are properly configured."""
        from ai_news.api_views import BaseSecureAPIView
        
        # Verify permission classes are configured
        self.assertIn(SecureAPIPermission, BaseSecureAPIView.permission_classes)


class MockRequestTest(TestCase):
    """Tests using mock requests to simulate various scenarios."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
    
    def test_malicious_user_agent_handling(self):
        """Test handling of potentially malicious user agents."""
        malicious_user_agents = [
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "<?php system('rm -rf /'); ?>",
            "\x00\x01\x02malicious"
        ]
        
        permission = SecureAPIPermission()
        view = MockView()
        
        for user_agent in malicious_user_agents:
            with patch('ai_news.src.permissions.SecurityAuditor.log_security_event') as mock_log:
                request = self.factory.get('/test/')
                request.user = AnonymousUser()
                request.META['HTTP_USER_AGENT'] = user_agent
                request.META['REMOTE_ADDR'] = '127.0.0.1'
                
                # Should not crash and should log the event
                result = permission.has_permission(request, view)
                self.assertTrue(result)
                mock_log.assert_called_once()
    
    def test_ip_spoofing_attempts(self):
        """Test handling of potential IP spoofing attempts."""
        spoofing_attempts = [
            "127.0.0.1, evil.com, 192.168.1.1",
            "0.0.0.0",
            "999.999.999.999",
            "localhost",
            "../../etc/hosts"
        ]
        
        permission = SecureAPIPermission()
        
        for spoofed_ip in spoofing_attempts:
            request = self.factory.get('/test/')
            request.META['HTTP_X_FORWARDED_FOR'] = spoofed_ip
            
            # Should extract first part and not crash
            ip = permission.get_client_ip(request)
            self.assertIsInstance(ip, str)
            self.assertGreater(len(ip), 0)
    
    def test_extremely_long_headers(self):
        """Test handling of extremely long headers."""
        permission = SecureAPIPermission()
        view = MockView()
        
        # Create request with very long headers
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        request.META['HTTP_USER_AGENT'] = 'A' * 10000  # 10KB user agent
        request.META['HTTP_X_FORWARDED_FOR'] = ','.join(['192.168.1.' + str(i) for i in range(1000)])
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # Should handle gracefully without crashing
        with patch('ai_news.src.permissions.SecurityAuditor.log_security_event'):
            result = permission.has_permission(request, view)
            self.assertTrue(result)
    
    def test_missing_headers_handling(self):
        """Test handling when headers are completely missing."""
        permission = SecureAPIPermission()
        view = MockView()
        
        # Request with minimal headers
        request = self.factory.get('/test/')
        request.user = AnonymousUser()
        # Don't set any META headers
        
        with patch('ai_news.src.permissions.SecurityAuditor.log_security_event'):
            result = permission.has_permission(request, view)
            self.assertTrue(result)
            
            # IP should default to 'unknown'
            ip = permission.get_client_ip(request)
            self.assertEqual(ip, 'unknown')