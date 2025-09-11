from django.db import models
from django.utils import timezone
import hashlib


class NewsArticle(models.Model):
    title = models.CharField(max_length=500)
    content = models.TextField()
    url = models.URLField(unique=True)
    source = models.CharField(max_length=100)
    published_date = models.DateTimeField()
    scraped_date = models.DateTimeField(default=timezone.now)
    content_hash = models.CharField(max_length=64, unique=True)
    embedding_vector = models.JSONField(null=True, blank=True)
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-published_date']
        indexes = [
            models.Index(fields=['source', 'published_date']),
            models.Index(fields=['content_hash']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                f"{self.title}{self.content}".encode('utf-8')
            ).hexdigest()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} - {self.source}"


class BlogSummary(models.Model):
    title = models.CharField(max_length=300)
    summary = models.TextField()
    articles = models.ManyToManyField(NewsArticle, related_name='blog_summaries')
    created_date = models.DateTimeField(default=timezone.now)
    topic_category = models.CharField(max_length=100)
    
    class Meta:
        ordering = ['-created_date']
    
    def __str__(self):
        return f"{self.title} - {self.created_date.date()}"