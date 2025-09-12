# AI News Application - Security Guide

## 🚨 CRITICAL SECURITY ISSUES FIXED

This document outlines the security vulnerabilities that were identified and fixed in the AI News application, plus ongoing security best practices.

---

## ✅ VULNERABILITIES FIXED

### **1. CRITICAL: API Keys Exposure** 
- **Issue**: Real API keys hardcoded in `.env` file committed to version control
- **Impact**: Financial loss, unauthorized access to OpenAI and Qdrant services
- **Fix**: 
  - Created `.env.example` template with placeholder values
  - Added security warnings to actual `.env` file
  - Implemented environment-based SECRET_KEY management

### **2. CRITICAL: Django Secret Key Hardcoded**
- **Issue**: `SECRET_KEY` hardcoded in `settings.py` 
- **Impact**: Session hijacking, CSRF attacks, data integrity compromise
- **Fix**: Environment variable loading with secure fallbacks

### **3. HIGH: Prompt Injection Vulnerabilities**
- **Issue**: User content directly injected into LLM prompts without sanitization
- **Impact**: AI model manipulation, unexpected responses, security bypasses
- **Fix**: 
  - Created comprehensive `InputSanitizer` class
  - Added prompt injection pattern detection
  - Sanitized all LLM inputs in `langchain_chains.py` and `news_service.py`

### **4. HIGH: No Rate Limiting**
- **Issue**: Unlimited requests to external APIs
- **Impact**: DoS attacks, IP banning, service disruption
- **Fix**: 
  - Implemented `RateLimiter` class
  - Added rate limiting to HackerNews scraper (example)
  - Added delays between API requests

### **5. MEDIUM: Input Validation Missing**
- **Issue**: External data processed without validation
- **Impact**: Data corruption, security bypasses
- **Fix**: Comprehensive article data validation before processing

---

## 🔒 SECURITY FEATURES IMPLEMENTED

### **Input Sanitization System**

```python
from ai_news.src.security import InputSanitizer

# Sanitize text for LLM processing
safe_text = InputSanitizer.sanitize_text_for_llm(
    user_input, 
    max_length=2000, 
    strict=False  # Filter mode
)

# Validate article data
sanitized_article = InputSanitizer.validate_article_data(raw_data)
```

**Protected Against**:
- Prompt injection patterns (`ignore previous`, `system:`, etc.)
- Template injection (`{{}}`, `${}`, `<%>`)
- Code injection (`eval`, `exec`, `import`)
- Social engineering attempts
- Excessive content length

### **Rate Limiting System**

```python
from ai_news.src.security import RateLimiter

# Create rate limiter (10 requests per minute)
limiter = RateLimiter(max_requests=10, time_window=60)

# Check before making request
if limiter.is_allowed():
    # Make API request
    response = requests.get(url)
else:
    # Wait before next request
    time.sleep(limiter.wait_time())
```

### **Security Auditing**

```python
from ai_news.src.security import SecurityAuditor

# Log security events
SecurityAuditor.log_security_event(
    "prompt_injection_attempt", 
    {"source": "hackernews", "pattern": "ignore previous"},
    severity="warning"
)

# Validate environment on startup
SecurityAuditor.validate_environment()
```

---

## 🛡️ SECURITY BEST PRACTICES

### **Environment Configuration**

1. **Never commit real secrets to version control**
   ```bash
   # Use .env.example for templates
   cp .env.example .env
   # Fill in real values in .env (ignored by git)
   ```

2. **Generate secure Django secret key**
   ```python
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```

3. **Set environment-specific settings**
   ```bash
   ENVIRONMENT=production
   DEBUG=false
   DJANGO_SECRET_KEY=your_secure_generated_key_here
   ```

### **API Security**

1. **Rotate API keys regularly**
   - OpenAI: https://platform.openai.com/api-keys
   - Qdrant: Regenerate in your Qdrant cloud dashboard

2. **Monitor API usage**
   - Set up usage alerts in OpenAI dashboard
   - Monitor unusual traffic patterns

3. **Use least privilege principle**
   - Restrict API key permissions where possible
   - Use separate keys for different environments

### **Application Security**

1. **Input validation is enabled by default**
   - All article data is sanitized before processing
   - LLM inputs are filtered for prompt injection
   - URLs are validated before requests

2. **Rate limiting protects external services**
   - APIs have request limits and delays
   - Prevents accidental DoS attacks
   - Can be configured per scraper

3. **Security logging is active**
   - All sanitization events are logged
   - Failed security validations are tracked
   - Check logs regularly for suspicious activity

---

## 🚨 SECURITY MONITORING

### **Log Files to Monitor**

```bash
# Security events
grep "SECURITY EVENT" logs/
grep "prompt_injection" logs/
grep "rate_limit" logs/

# Failed validations
grep "Security validation failed" logs/
grep "Input sanitization" logs/
```

### **Environment Health Checks**

The application automatically validates security on startup:
- Checks for insecure SECRET_KEY
- Validates critical environment variables
- Ensures production settings are secure

### **Regular Security Tasks**

1. **Weekly**:
   - Review security logs for anomalies
   - Check API usage patterns
   - Verify environment configuration

2. **Monthly**:
   - Rotate API keys
   - Update dependencies for security patches
   - Review and test security configurations

3. **Before Production Deployment**:
   - Run security validation: `SecurityAuditor.validate_environment()`
   - Verify all environment variables are set
   - Ensure DEBUG=false in production

---

## 🔧 SECURITY CONFIGURATION REFERENCE

### **Required Environment Variables**

```bash
# Critical - must be set
OPENAI_API_KEY=your_openai_key_here
DJANGO_SECRET_KEY=your_secure_django_key_here

# Qdrant (choose cloud OR local)
QDRANT_URL=your_cloud_qdrant_url
QDRANT_API_KEY=your_qdrant_key

# Security settings
DEBUG=false                    # NEVER true in production
ENVIRONMENT=production         # Set appropriately
```

### **Security Headers (for production web deployment)**

```python
# Add to Django settings.py for web deployment
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True  
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## 📞 INCIDENT RESPONSE

### **If Security Breach Suspected**

1. **Immediate Actions**:
   - Rotate all API keys immediately
   - Check API usage for unauthorized activity
   - Review logs for security events

2. **Investigation**:
   - Identify attack vectors
   - Check data integrity
   - Review affected time periods

3. **Recovery**:
   - Update security configurations
   - Apply additional protective measures
   - Monitor for continued suspicious activity

### **Security Contact**

For security issues or questions:
- Review this security guide
- Check application logs for security events
- Implement additional security measures as needed

---

## 📚 FURTHER READING

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security Guide](https://docs.djangoproject.com/en/5.2/topics/security/)
- [OpenAI API Security Best Practices](https://platform.openai.com/docs/guides/safety-best-practices)
- [AI/ML Security Guidelines](https://owasp.org/www-project-machine-learning-security-top-10/)

This security implementation protects the AI News application against the most common attack vectors while maintaining functionality and performance.