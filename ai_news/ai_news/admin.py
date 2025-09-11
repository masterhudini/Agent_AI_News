from django.contrib import admin
from .models import NewsArticle, BlogSummary


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'source', 'published_date', 'is_duplicate', 'scraped_date']
    list_filter = ['source', 'is_duplicate', 'published_date', 'scraped_date']
    search_fields = ['title', 'content', 'url']
    readonly_fields = ['content_hash', 'scraped_date']
    date_hierarchy = 'published_date'
    
    fieldsets = (
        ('Article Information', {
            'fields': ('title', 'content', 'url', 'source', 'published_date')
        }),
        ('Deduplication', {
            'fields': ('content_hash', 'is_duplicate', 'duplicate_of'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('scraped_date', 'embedding_vector'),
            'classes': ('collapse',)
        })
    )


@admin.register(BlogSummary)
class BlogSummaryAdmin(admin.ModelAdmin):
    list_display = ['title', 'topic_category', 'created_date', 'article_count']
    list_filter = ['topic_category', 'created_date']
    search_fields = ['title', 'summary']
    readonly_fields = ['created_date']
    date_hierarchy = 'created_date'
    
    def article_count(self, obj):
        return obj.articles.count()
    
    article_count.short_description = 'Article Count'