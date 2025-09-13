# AI News Application - REST API Documentation

## 🚀 API Overview

The AI News REST API provides secure, rate-limited access to the latest AI news summaries and system statistics. The API is designed with security-first principles and includes comprehensive protection against common attacks.

**Base URL**: `http://localhost:8000/api/`
**API Version**: v1.0
**Authentication**: None required (configurable for production)

---

## 🔒 Security Features

### **Built-in Security Protections**:
- ✅ **Rate Limiting**: 100 requests per hour per IP address
- ✅ **Input Sanitization**: All content sanitized against prompt injection  
- ✅ **Security Headers**: XSS protection, content sniffing prevention
- ✅ **Error Handling**: No internal information disclosure
- ✅ **Request Logging**: All API access logged for monitoring
- ✅ **Response Caching**: Optimized performance with cache headers

### **Security Headers Added**:
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY  
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'none'; frame-ancestors 'none';
Cache-Control: public, max-age=300
```

---

## 📡 API Endpoints

### **1. Get Latest Summary**

Get the most recent AI news summary with metadata.

```http
GET /api/latest-summary/
GET /api/v1/latest-summary/
```

**Response Format**:
```json
{
  "success": true,
  "data": {
    "id": 3,
    "title": "AI News Summary", 
    "summary": "Technical content about neuro-symbolic AI...",
    "topic_category": "Machine Learning",
    "created_at": "2025-09-11T21:10:05.850606+00:00",
    "article_count": 484,
    "sources": ["AWS ML Blog", "TechCrunch", "Hacker News", ...]
  },
  "metadata": {
    "generated_at": "2025-09-12T20:22:08.925698",
    "cache_expires": "2025-09-12T20:27:08.925698", 
    "api_version": "1.0",
    "total_sources": 18
  }
}
```

**Cache**: 5 minutes
**Rate Limit**: Included in global limit

---

### **2. Get System Status**

Health check endpoint with basic system statistics.

```http
GET /api/status/
GET /api/v1/status/  
```

**Response Format**:
```json
{
  "success": true,
  "status": "healthy",
  "data": {
    "total_summaries": 3,
    "latest_summary_age": "23 hours ago",
    "available_sources": 35,
    "system_uptime": "operational"
  },
  "metadata": {
    "generated_at": "2025-09-12T20:22:18.074201",
    "api_version": "1.0"
  }
}
```

**Cache**: 10 minutes
**Rate Limit**: Included in global limit

---

## 📋 Response Codes

| Code | Status | Description |
|------|--------|-------------|
| **200** | OK | Request successful |
| **404** | Not Found | No summaries available |
| **429** | Too Many Requests | Rate limit exceeded |
| **500** | Internal Server Error | Server error (generic message) |

### **Error Response Format**:
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "message": "Too many requests. Try again in 3542 seconds.",
  "retry_after": 3542
}
```

---

## 🛡️ Rate Limiting

**Global Rate Limit**: 100 requests per hour per IP address

**Rate Limit Headers**: 
- `retry_after`: Seconds to wait before next request (in error response)

**Rate Limit Response**:
```json
{
  "success": false,
  "error": "Rate limit exceeded", 
  "message": "Too many requests. Try again in 1847 seconds.",
  "retry_after": 1847
}
```

**Best Practices**:
- Monitor response status codes
- Implement exponential backoff for 429 responses
- Cache responses locally when appropriate
- Use the `cache_expires` timestamp to minimize requests

---

## 🔧 Usage Examples

### **Bash/cURL**:
```bash
# Get latest summary
curl -s "http://localhost:8000/api/latest-summary/" | jq .

# Check system status
curl -s "http://localhost:8000/api/status/" | jq .

# Test with headers
curl -I "http://localhost:8000/api/latest-summary/"
```

### **Python**:
```python
import requests
import json
from datetime import datetime

# Get latest summary
def get_latest_summary():
    response = requests.get('http://localhost:8000/api/latest-summary/')
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            summary = data['data']
            print(f"Title: {summary['title']}")
            print(f"Articles: {summary['article_count']}")
            print(f"Sources: {len(summary['sources'])}")
            return summary
    elif response.status_code == 429:
        error_data = response.json()
        print(f"Rate limited. Wait {error_data['retry_after']} seconds")
    else:
        print(f"Error: {response.status_code}")
    
    return None

# Check system health
def check_system_status():
    response = requests.get('http://localhost:8000/api/status/')
    
    if response.status_code == 200:
        status = response.json()['data']
        print(f"System Status: {status}")
        return status['status'] == 'healthy'
    
    return False

# Example usage
if __name__ == \"__main__\":
    if check_system_status():
        summary = get_latest_summary()
        if summary:
            print(\"Successfully retrieved latest summary!\")
```

### **JavaScript/Node.js**:
```javascript
const axios = require('axios');

// Get latest summary with error handling
async function getLatestSummary() {
    try {
        const response = await axios.get('http://localhost:8000/api/latest-summary/');
        
        if (response.data.success) {
            const { data, metadata } = response.data;
            console.log(`Title: ${data.title}`);
            console.log(`Articles: ${data.article_count}`);
            console.log(`Cache expires: ${metadata.cache_expires}`);
            return data;
        }
    } catch (error) {
        if (error.response?.status === 429) {
            const retryAfter = error.response.data.retry_after;
            console.log(`Rate limited. Retry in ${retryAfter} seconds`);
        } else {
            console.log(`Error: ${error.message}`);
        }
    }
    return null;
}

// Usage
getLatestSummary().then(summary => {
    if (summary) {
        console.log('Summary retrieved successfully!');
    }
});
```

---

## 🔍 Monitoring and Logging

### **Security Events Logged**:
- API access attempts with IP and user agent
- Rate limit violations
- Input sanitization events  
- API errors and exceptions

### **Log Examples**:
```
INFO SECURITY EVENT [api_access]: {'endpoint': '/api/latest-summary', 'client_ip': '127.0.0.1', 'user_agent': 'curl/7.68.0'}
WARNING SECURITY EVENT [api_rate_limit_exceeded]: {'client_ip': '192.168.1.100', 'wait_time': 3542}
ERROR SECURITY EVENT [api_error]: {'endpoint': '/api/status', 'client_ip': '10.0.0.1', 'error_type': 'DatabaseError'}
```

### **Monitoring Recommendations**:
- Monitor rate limit violations for potential abuse
- Track response times and error rates
- Alert on unusual IP patterns or user agents
- Monitor cache hit rates for performance optimization

---

## 🚀 Production Deployment

### **Environment Variables**:
```bash
# Required for API security
DJANGO_SECRET_KEY=your_secure_secret_key_here
DEBUG=false
ENVIRONMENT=production

# Optional API authentication
API_KEY=your_api_key_for_authentication  # Not enabled by default
```

### **Security Hardening for Production**:

1. **Enable HTTPS**:
   ```python
   # Add to settings.py
   SECURE_SSL_REDIRECT = True
   SECURE_HSTS_SECONDS = 31536000
   SECURE_HSTS_INCLUDE_SUBDOMAINS = True
   ```

2. **Enable API Key Authentication** (Optional):
   ```python
   # Uncomment in api.py require_api_key decorator
   api_key = request.headers.get('X-API-Key')
   if not api_key or api_key != settings.API_KEY:
       return JsonResponse({'error': 'Invalid API key'}, status=401)
   ```

3. **Configure Reverse Proxy**:
   ```nginx
   # Nginx configuration
   location /api/ {
       proxy_pass http://127.0.0.1:8000/api/;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header Host $host;
       
       # Rate limiting at proxy level
       limit_req zone=api burst=20 nodelay;
   }
   ```

4. **Database Connection Pooling**:
   - Configure connection pooling for high-traffic scenarios
   - Enable query optimization and indexing

---

## 🔧 Configuration Options

### **Cache Configuration**:
```python
# In settings.py - adjust cache backend for production
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'TIMEOUT': 300,  # 5 minutes
    }
}
```

### **Rate Limiting Configuration**:
```python
# In api.py - adjust rate limits per endpoint
api_rate_limiter = RateLimiter(
    max_requests=200,    # Increase for production
    time_window=3600     # Per hour
)
```

---

## 🐛 Troubleshooting

### **Common Issues**:

1. **Rate Limit Errors**:
   - **Solution**: Wait for the `retry_after` time or implement exponential backoff
   - **Prevention**: Cache responses and implement request queuing

2. **404 No Summaries**:
   - **Cause**: No summaries generated yet
   - **Solution**: Run `python manage.py generate_summary --type daily`

3. **500 Internal Server Error**:
   - **Check**: Django logs for specific error details
   - **Common**: Database connection issues or missing environment variables

4. **Security Headers Not Present**:
   - **Check**: Reverse proxy configuration
   - **Solution**: Ensure `api_security_headers()` function is being called

### **Debug Commands**:
```bash
# Check if summaries exist
python manage.py shell -c \"from ai_news.models import BlogSummary; print(f'Summaries: {BlogSummary.objects.count()}')\"

# Test security validation
python manage.py shell -c \"from ai_news.src.security import SecurityAuditor; SecurityAuditor.validate_environment()\"

# Check API endpoint
curl -v http://localhost:8000/api/status/
```

---

## 📞 Support and Security

### **Security Issues**:
- All security events are logged automatically
- Review logs regularly for suspicious patterns
- Report security vulnerabilities through proper channels

### **API Changes**:
- API versioning ensures backward compatibility
- Monitor the `api_version` field in responses
- Breaking changes will increment major version number

This REST API provides secure, efficient access to AI news summaries with enterprise-grade security features and comprehensive monitoring capabilities.