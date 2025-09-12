"""
Security utilities for AI News Application
Provides input sanitization, validation, and security controls
"""
import re
import html
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """Raised when security validation fails"""
    pass

class InputSanitizer:
    """
    Comprehensive input sanitization and validation for AI News application.
    Protects against prompt injection, XSS, and other input-based attacks.
    """
    
    # Dangerous prompt injection patterns
    PROMPT_INJECTION_PATTERNS = [
        # Direct instruction attempts
        r'\b(?:ignore|forget|disregard)\s+(?:previous|above|earlier|past)\b',
        r'\b(?:system|assistant|user)\s*:',
        r'\b(?:you are|act as|pretend to be|role.?play)\b',
        r'\b(?:instruction|directive|command|order)\b.*(?:ignore|override|bypass)\b',
        
        # AI model manipulation
        r'\b(?:openai|gpt|claude|llm|model)\b.*(?:jailbreak|hack|bypass)\b',
        r'\bprompt\s+(?:injection|hack|attack)\b',
        r'\b(?:break|exit|escape)\s+(?:character|role|mode)\b',
        
        # Template injection attempts
        r'\{\{.*\}\}',  # Template literals
        r'\$\{.*\}',    # Variable interpolation
        r'<%.*%>',      # Template tags
        
        # Code injection patterns
        r'\b(?:eval|exec|import|__)\b',
        r'(?:javascript|script|onclick|onload):',
        
        # Social engineering patterns
        r'\b(?:urgent|immediately|asap|emergency)\b.*(?:ignore|bypass|override)\b',
        r'\b(?:developer|admin|system)\s+(?:told|said|instructed)\b',
    ]
    
    # Compile patterns for performance
    COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE | re.MULTILINE) for pattern in PROMPT_INJECTION_PATTERNS]
    
    @classmethod
    def sanitize_text_for_llm(cls, text: str, max_length: int = 8000, strict: bool = True) -> str:
        """
        Sanitize text input before sending to LLM to prevent prompt injection.
        
        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length
            strict: If True, raises SecurityError on detection. If False, filters content.
            
        Returns:
            Sanitized text safe for LLM processing
            
        Raises:
            SecurityError: If dangerous patterns detected and strict=True
        """
        if not text or not isinstance(text, str):
            return ""
        
        original_text = text
        
        # 1. Length validation
        if len(text) > max_length:
            text = text[:max_length]
            logger.warning(f"Text truncated from {len(original_text)} to {max_length} characters")
        
        # 2. HTML escape for safety
        text = html.escape(text)
        
        # 3. Check for prompt injection patterns
        detected_patterns = []
        for i, pattern in enumerate(cls.COMPILED_PATTERNS):
            if pattern.search(text):
                detected_patterns.append(cls.PROMPT_INJECTION_PATTERNS[i])
        
        if detected_patterns:
            if strict:
                logger.error(f"Prompt injection attempt detected: {detected_patterns[:3]}")
                raise SecurityError(f"Input contains potentially dangerous patterns: {len(detected_patterns)} patterns detected")
            else:
                # Filter mode - replace dangerous patterns
                for pattern in cls.COMPILED_PATTERNS:
                    text = pattern.sub('[FILTERED]', text)
                logger.warning(f"Filtered {len(detected_patterns)} potentially dangerous patterns")
        
        # 4. Additional cleaning
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove non-printable characters except common ones
        text = re.sub(r'[^\x20-\x7E\n\r\t]', '', text)
        
        return text
    
    @classmethod
    def sanitize_url(cls, url: str) -> str:
        """
        Sanitize and validate URL inputs.
        
        Args:
            url: URL to validate
            
        Returns:
            Sanitized URL
            
        Raises:
            SecurityError: If URL is malicious
        """
        if not url:
            return ""
        
        try:
            parsed = urlparse(url)
            
            # Only allow HTTP/HTTPS
            if parsed.scheme not in ['http', 'https']:
                raise SecurityError(f"Invalid URL scheme: {parsed.scheme}")
            
            # Block common malicious patterns
            malicious_patterns = [
                r'javascript:',
                r'data:',
                r'vbscript:',
                r'file:',
                r'ftp:',
            ]
            
            for pattern in malicious_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    raise SecurityError(f"Potentially malicious URL pattern detected")
            
            return url
        except Exception as e:
            raise SecurityError(f"Invalid URL format: {e}")
    
    @classmethod
    def validate_article_data(cls, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize article data before processing.
        
        Args:
            article_data: Raw article data from scrapers
            
        Returns:
            Sanitized article data
            
        Raises:
            SecurityError: If data contains dangerous content
        """
        if not isinstance(article_data, dict):
            raise SecurityError("Article data must be a dictionary")
        
        required_fields = ['title', 'content', 'url', 'source']
        for field in required_fields:
            if field not in article_data:
                raise SecurityError(f"Missing required field: {field}")
        
        sanitized = {}
        
        # Sanitize text fields
        sanitized['title'] = cls.sanitize_text_for_llm(
            str(article_data.get('title', '')), 
            max_length=500,
            strict=False  # Filter mode for titles
        )
        
        sanitized['content'] = cls.sanitize_text_for_llm(
            str(article_data.get('content', '')),
            max_length=50000,  # Larger limit for content
            strict=False  # Filter mode for content
        )
        
        sanitized['source'] = cls.sanitize_text_for_llm(
            str(article_data.get('source', '')),
            max_length=200,
            strict=False
        )
        
        # Sanitize URL
        sanitized['url'] = cls.sanitize_url(str(article_data.get('url', '')))
        
        # Preserve other safe fields
        safe_fields = ['published_date', 'author', 'tags']
        for field in safe_fields:
            if field in article_data:
                if field == 'tags' and isinstance(article_data[field], list):
                    # Sanitize each tag
                    sanitized[field] = [
                        cls.sanitize_text_for_llm(str(tag), max_length=100, strict=False) 
                        for tag in article_data[field][:10]  # Limit to 10 tags
                    ]
                else:
                    sanitized[field] = cls.sanitize_text_for_llm(
                        str(article_data[field]),
                        max_length=500,
                        strict=False
                    )
        
        return sanitized

class RateLimiter:
    """
    Simple rate limiting for external API calls and resource-intensive operations.
    """
    
    def __init__(self, max_requests: int = 100, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def is_allowed(self) -> bool:
        """Check if request is allowed under rate limit."""
        import time
        now = time.time()
        
        # Remove old requests outside time window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        
        # Check if we're under limit
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def wait_time(self) -> float:
        """Get time to wait before next request is allowed."""
        import time
        if not self.requests:
            return 0.0
        
        oldest_request = min(self.requests)
        return max(0.0, self.time_window - (time.time() - oldest_request))

class SecurityAuditor:
    """
    Security auditing and monitoring utilities.
    """
    
    @staticmethod
    def log_security_event(event_type: str, details: Dict[str, Any], severity: str = 'warning'):
        """
        Log security events for monitoring and analysis.
        
        Args:
            event_type: Type of security event
            details: Event details
            severity: Severity level (info, warning, error, critical)
        """
        log_levels = {
            'info': logger.info,
            'warning': logger.warning, 
            'error': logger.error,
            'critical': logger.critical
        }
        
        log_func = log_levels.get(severity, logger.warning)
        log_func(f"SECURITY EVENT [{event_type}]: {details}")
    
    @staticmethod
    def validate_environment():
        """
        Validate security configuration of the application environment.
        
        Raises:
            SecurityError: If critical security issues found
        """
        import os
        
        issues = []
        
        # Check for debug mode in production
        if os.environ.get('ENVIRONMENT') == 'production' and os.environ.get('DEBUG', '').lower() == 'true':
            issues.append("DEBUG=True in production environment")
        
        # Check for missing critical environment variables
        critical_vars = ['DJANGO_SECRET_KEY', 'OPENAI_API_KEY']
        for var in critical_vars:
            if not os.environ.get(var):
                issues.append(f"Missing critical environment variable: {var}")
        
        # Check for insecure secret keys
        secret_key = os.environ.get('DJANGO_SECRET_KEY', '')
        if 'insecure' in secret_key or len(secret_key) < 32:
            issues.append("Weak or insecure Django SECRET_KEY")
        
        if issues:
            raise SecurityError(f"Security configuration issues: {'; '.join(issues)}")
        
        logger.info("Security environment validation passed")