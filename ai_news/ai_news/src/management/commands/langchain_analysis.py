# Django management command framework
from django.core.management.base import BaseCommand, CommandError

# Core application services
from ai_news.src.news_service import NewsOrchestrationService  # Main orchestration service
from ai_news.models import NewsArticle                          # Django model dla database queries


class Command(BaseCommand):
    """
    Advanced Django management command dla LangChain-powered news analysis i AI operations.
    
    Comprehensive CLI tool dla sophisticated AI-powered news analysis, semantic search,
    article insights extraction, i intelligent content generation. Leverages cały
    LangChain ecosystem dla advanced natural language processing operations.
    
    Architektura:
    - Django BaseCommand: Standard CLI framework integration
    - NewsOrchestrationService: Unified AI operations orchestration
    - LangChain Integration: Advanced NLP capabilities
    - OpenAI Models: Configurable AI backend (GPT-4o-mini default)
    
    Core Capabilities:
    1. Interactive Queries: Conversational AI dla news data exploration
    2. Semantic Search: Vector-based similarity search using embeddings
    3. Article Analysis: Structured insights extraction z AI
    4. Intelligent Summaries: Advanced blog generation z multiple sources
    
    Available Operations:
    --query: Natural language queries about news database
    --search: Semantic search dla similar articles
    --analyze: Detailed AI analysis recent articles
    --intelligent-summary: Premium blog post generation
    
    Wykorzystywana przez:
    - Research workflows requiring AI-powered analysis
    - Content creation processes
    - Interactive news data exploration
    - Development i testing AI capabilities
    
    Example Usage:
    python manage.py langchain_analysis --query "What are AI trends?"
    python manage.py langchain_analysis --search "machine learning" --limit 5
    python manage.py langchain_analysis --analyze --topic "Tech News"
    python manage.py langchain_analysis --intelligent-summary --model gpt-4o
    
    Advanced Features:
    - Configurable OpenAI models dla cost/quality optimization
    - Flexible result limits dla performance tuning
    - Topic-based categorization dla focused analysis
    - Comprehensive error handling i user guidance
    """
    
    help = 'Analyze news articles using LangChain and create intelligent summaries'

    def add_arguments(self, parser):
        """
        Defines comprehensive command-line arguments dla advanced AI operations.
        
        Configures flexible argument parser supporting multiple AI-powered workflows.
        Each argument enables different types of analysis i interaction modes.
        
        Argument Categories:
        1. Operation Modes: --query, --search, --analyze, --intelligent-summary
        2. Configuration: --topic, --limit, --model
        3. Content Targeting: topic categorization i result limiting
        
        Design Principles:
        - Mutually exclusive primary operations dla clear workflow
        - Flexible configuration options dla customization
        - Reasonable defaults dla immediate usability
        - Clear help text dla user guidance
        
        Args:
            parser: Django ArgumentParser instance dla configuration
        """
        # PRIMARY OPERATIONS (mutually exclusive)
        
        # Interactive conversational queries
        parser.add_argument(
            '--query',
            type=str,
            help='Natural language query about news data (e.g., "What are AI trends?", "Show me stats")',
        )
        
        # Semantic similarity search
        parser.add_argument(
            '--search',
            type=str,
            help='Search for articles semantically similar to query (vector-based search)',
        )
        
        # Detailed article analysis
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='Analyze recent articles with AI: topics, importance, categorization, summaries',
        )
        
        # Premium blog generation
        parser.add_argument(
            '--intelligent-summary',
            action='store_true',
            help='Create sophisticated blog summary using multi-stage AI analysis',
        )
        
        # CONFIGURATION OPTIONS
        
        # Topic focus dla analysis
        parser.add_argument(
            '--topic',
            type=str,
            default='AI News',
            help='Topic category dla analysis context (default: "AI News", examples: "Tech", "Business")',
        )
        
        # Result limiting dla performance
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum number of articles to process (default: 10, balance performance vs coverage)',
        )
        
        # AI model selection dla cost/quality optimization
        parser.add_argument(
            '--model',
            type=str,
            default='gpt-4o-mini',
            help='OpenAI model dla AI operations (default: gpt-4o-mini, alternatives: gpt-4o, gpt-3.5-turbo)',
        )

    def handle(self, *args, **options):
        """
        Main command execution orchestrating different AI-powered analysis operations.
        
        Routes command-line arguments to appropriate AI workflows i manages
        comprehensive error handling, progress reporting, i result presentation.
        
        Operation Routing:
        1. Interactive Query: Conversational AI using NewsProcessingAgent
        2. Semantic Search: Vector similarity search using embeddings
        3. Article Analysis: Structured AI insights extraction
        4. Intelligent Summary: Multi-stage AI blog generation
        5. Help: Usage examples i guidance
        
        Features:
        - Configurable AI model selection dla cost optimization
        - Flexible result limiting dla performance tuning
        - Comprehensive error handling i user feedback
        - Detailed progress reporting i result presentation
        
        Args:
            *args: Positional arguments (unused)
            **options: Parsed command-line arguments dictionary
            
        Error Handling:
        - CommandError dla user-facing validation errors
        - Graceful degradation dla AI service failures
        - Clear error messages z troubleshooting guidance
        - Fallback help text dla invalid argument combinations
        """
        # Initialize NewsOrchestrationService z user-specified AI model
        # Allows cost/quality optimization through model selection
        service = NewsOrchestrationService(
            llm_model=options['model']  # User-configurable: gpt-4o-mini, gpt-4o, etc.
        )
        
        # Display tool header z configuration info
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🤖 LangChain News Analysis Tool\n"
                f"   AI Model: {options['model']}\n"
                f"   Topic Focus: {options['topic']}\n"
                f"   Result Limit: {options['limit']}\n"
                f"   {'-'*40}"
            )
        )
        
        # OPERATION 1: Interactive Conversational Query
        if options['query']:
            query = options['query']
            self.stdout.write(f"💬 Processing interactive query: '{query}'")
            self.stdout.write("Analyzing query and selecting appropriate tools...")
            
            # Use NewsProcessingAgent dla intelligent query handling
            response = service.interactive_news_query(query)
            
            self.stdout.write("\n" + "="*60)
            self.stdout.write("AI AGENT RESPONSE")
            self.stdout.write("="*60)
            self.stdout.write(response)
            self.stdout.write("="*60)
        
        # OPERATION 2: Semantic Similarity Search
        elif options['search']:
            query = options['search']
            self.stdout.write(f"🔍 Semantic search for: '{query}'")
            self.stdout.write("Using OpenAI embeddings + Qdrant vector database...")
            
            # Execute vector-based similarity search
            articles = service.search_similar_articles(query, limit=options['limit'])
            
            if articles:
                self.stdout.write(
                    self.style.SUCCESS(f"\n✓ Found {len(articles)} semantically similar articles:")
                )
                self.stdout.write("\n" + "-"*80)
                
                for i, article in enumerate(articles, 1):
                    self.stdout.write(f"\n{i}. 📰 {article.title}")
                    self.stdout.write(f"   🏢 Source: {article.source}")
                    self.stdout.write(f"   🔗 URL: {article.url}")
                    self.stdout.write(f"   📅 Published: {article.published_date.strftime('%Y-%m-%d %H:%M')}")
                    
                    # Show content preview
                    preview = article.content[:150] + "..." if len(article.content) > 150 else article.content
                    self.stdout.write(f"   📝 Preview: {preview}")
                    self.stdout.write("-"*80)
            else:
                self.stdout.write(
                    self.style.WARNING("⚠ No similar articles found above similarity threshold (85%)")
                )
        
        # OPERATION 3: Detailed AI Article Analysis
        elif options['analyze']:
            self.stdout.write(f"🧐 Analyzing recent articles about '{options['topic']}'...")
            self.stdout.write("Using LangChain + OpenAI dla structured insights extraction...")
            
            # Query recent unique articles dla analysis
            recent_articles = NewsArticle.objects.filter(
                is_duplicate=False  # Only unique articles
            ).order_by('-published_date')[:options['limit']]  # Most recent first
            
            if not recent_articles:
                self.stdout.write(self.style.WARNING("⚠ No articles found to analyze"))
                return
            
            # Execute comprehensive AI analysis
            self.stdout.write(f"Processing {len(recent_articles)} articles through AI analysis pipeline...")
            analyzed = service.analyze_articles_with_langchain(list(recent_articles))
            
            if analyzed:
                self.stdout.write(
                    self.style.SUCCESS(f"\n✓ Successfully analyzed {len(analyzed)} articles:")
                )
                
                for i, item in enumerate(analyzed, 1):
                    article = item['article']
                    analysis = item['analysis']
                    
                    self.stdout.write(f"\n{'='*60}")
                    self.stdout.write(f"ARTICLE {i}: {article.title}")
                    self.stdout.write(f"{'='*60}")
                    self.stdout.write(f"🏢 Source: {article.source}")
                    self.stdout.write(f"📅 Published: {article.published_date.strftime('%Y-%m-%d %H:%M')}")
                    self.stdout.write(f"🗒 Category: {analysis.get('category', 'N/A')}")
                    
                    # Importance score z visual indicator
                    score = analysis.get('importance_score', 0)
                    score_display = f"{score:.2f}" if isinstance(score, (int, float)) else "N/A"
                    importance_bar = "★" * int(score * 5) if isinstance(score, (int, float)) else ""
                    self.stdout.write(f"⭐ Importance: {score_display}/1.0 {importance_bar}")
                    
                    self.stdout.write(f"🏷️ Key Topics: {', '.join(analysis.get('key_topics', []))}")
                    self.stdout.write(f"📝 AI Summary: {analysis.get('summary', 'N/A')}")
                    self.stdout.write(f"🔗 URL: {article.url}")
            else:
                self.stdout.write(self.style.ERROR("❌ No analysis results available - check AI service status"))
        
        # OPERATION 4: Intelligent Blog Summary Generation
        elif options['intelligent_summary']:
            topic = options['topic']
            self.stdout.write(f"🧐 Creating intelligent blog summary dla '{topic}'...")
            self.stdout.write("Multi-stage AI process: Article Analysis → Blog Generation → Synthesis")
            
            # Execute premium AI-powered blog generation
            summary = service.create_intelligent_blog_summary(topic)
            
            if summary:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✓ Successfully created intelligent blog summary!\n"
                        f"   Title: {summary.title}"
                    )
                )
                
                # Display comprehensive summary metadata
                self.stdout.write("\n" + "-"*60)
                self.stdout.write("BLOG SUMMARY DETAILS")
                self.stdout.write("-"*60)
                self.stdout.write(f"🆔 Summary ID: {summary.id}")
                self.stdout.write(f"📈 Articles analyzed: {summary.articles.count()}")
                self.stdout.write(f"🏷️ Topic category: {summary.topic_category}")
                self.stdout.write(f"📅 Created: {summary.created_date.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Content preview z intelligent truncation
                preview_length = 400
                if len(summary.summary) > preview_length:
                    preview = summary.summary[:preview_length] + "\n\n[...truncated for display...]"
                else:
                    preview = summary.summary
                
                self.stdout.write("\n" + "="*60)
                self.stdout.write("CONTENT PREVIEW")
                self.stdout.write("="*60)
                self.stdout.write(preview)
                self.stdout.write("="*60)
                
                self.stdout.write(
                    f"\n💾 Full summary saved to database (ID: {summary.id})"
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "⚠ No intelligent summary generated\n"
                        "   Possible causes:\n"
                        "   - No recent articles found (last 24h)\n"
                        "   - AI service unavailable\n"
                        "   - OpenAI API rate limits\n"
                        "   - Insufficient article content"
                    )
                )
        
        else:
            # No valid operation specified - show comprehensive help
            self.stdout.write(
                self.style.ERROR("❌ Please specify an AI operation to perform\n")
            )
            
            self.stdout.write("AVAILABLE OPERATIONS:")
            self.stdout.write("-"*50)
            self.stdout.write("💬 --query           Interactive conversational queries")
            self.stdout.write("🔍 --search          Semantic similarity search")
            self.stdout.write("🧐 --analyze         Detailed AI article analysis")
            self.stdout.write("📝 --intelligent-summary  Premium blog generation\n")
            
            self.stdout.write("USAGE EXAMPLES:")
            self.stdout.write("-"*50)
            self.stdout.write("💬 Interactive Query:")
            self.stdout.write("   python manage.py langchain_analysis --query 'What are the latest AI trends?'")
            self.stdout.write("   python manage.py langchain_analysis --query 'Show me database statistics'")
            self.stdout.write("")
            self.stdout.write("🔍 Semantic Search:")
            self.stdout.write("   python manage.py langchain_analysis --search 'machine learning' --limit 5")
            self.stdout.write("   python manage.py langchain_analysis --search 'OpenAI GPT-4' --model gpt-4o")
            self.stdout.write("")
            self.stdout.write("🧐 Article Analysis:")
            self.stdout.write("   python manage.py langchain_analysis --analyze --topic 'AI News' --limit 10")
            self.stdout.write("   python manage.py langchain_analysis --analyze --topic 'Tech' --model gpt-4o")
            self.stdout.write("")
            self.stdout.write("📝 Intelligent Summary:")
            self.stdout.write("   python manage.py langchain_analysis --intelligent-summary --topic 'Tech News'")
            self.stdout.write("   python manage.py langchain_analysis --intelligent-summary --model gpt-4o --topic 'AI'")
            self.stdout.write("")
            self.stdout.write("⚙️ Configuration options: --topic, --limit, --model")
            self.stdout.write("💰 Cost optimization: Use --model gpt-4o-mini dla lower costs")