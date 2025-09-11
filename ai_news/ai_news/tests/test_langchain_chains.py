"""
Tests for LangChain chains and AI processing functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

from ai_news.src.langchain_chains import (
    NewsAnalyzer,
    BlogGenerator, 
    NewsProcessingAgent,
    LangChainNewsOrchestrator,
    NewsAnalysisResult,
    BlogPostStructure
)
from ai_news.tests.base import BaseTestCase


class TestNewsAnalysisResult(BaseTestCase):
    """Test Pydantic models for structured output"""
    
    def test_news_analysis_result_creation(self):
        """Test creating NewsAnalysisResult"""
        
        result = NewsAnalysisResult(
            key_topics=['AI', 'Machine Learning'],
            importance_score=0.8,
            category='Technology',
            summary='Test summary'
        )
        
        self.assertEqual(result.key_topics, ['AI', 'Machine Learning'])
        self.assertEqual(result.importance_score, 0.8)
        self.assertEqual(result.category, 'Technology')
        self.assertEqual(result.summary, 'Test summary')
    
    def test_news_analysis_result_validation(self):
        """Test NewsAnalysisResult validation"""
        
        # Test valid importance score
        valid_result = NewsAnalysisResult(
            key_topics=['AI'],
            importance_score=0.5,
            category='Tech',
            summary='Valid'
        )
        self.assertEqual(valid_result.importance_score, 0.5)
        
        # Test invalid importance score (should raise validation error)
        with self.assertRaises(Exception):  # Pydantic validation error
            NewsAnalysisResult(
                key_topics=['AI'],
                importance_score=1.5,  # Above 1.0
                category='Tech',
                summary='Invalid'
            )
    
    def test_blog_post_structure_creation(self):
        """Test creating BlogPostStructure"""
        
        blog_post = BlogPostStructure(
            title='Test Blog Title',
            introduction='Test introduction',
            main_content='Test main content',
            conclusion='Test conclusion',
            tags=['ai', 'tech']
        )
        
        self.assertEqual(blog_post.title, 'Test Blog Title')
        self.assertEqual(blog_post.tags, ['ai', 'tech'])


class TestNewsAnalyzer(BaseTestCase):
    """Test NewsAnalyzer LangChain component"""
    
    def setUp(self):
        super().setUp()
        
        # Mock ChatOpenAI
        self.mock_llm = Mock()
        self.mock_chain = Mock()
        
        with patch('ai_news.src.langchain_chains.ChatOpenAI', return_value=self.mock_llm):
            self.analyzer = NewsAnalyzer(model="gpt-4o-mini")
    
    def test_analyzer_initialization(self):
        """Test NewsAnalyzer initialization"""
        
        self.assertIsNotNone(self.analyzer.llm)
        self.assertIsNotNone(self.analyzer.output_parser)
        self.assertIsNotNone(self.analyzer.analysis_chain)
    
    @patch('ai_news.src.langchain_chains.NewsAnalyzer.analysis_chain')
    def test_analyze_article_success(self, mock_chain):
        """Test successful article analysis"""
        
        # Mock successful analysis result
        mock_result = NewsAnalysisResult(
            key_topics=['AI', 'Deep Learning'],
            importance_score=0.9,
            category='Technology',
            summary='Advanced AI research breakthrough'
        )
        mock_chain.invoke.return_value = mock_result
        
        article = self.create_mock_article_data()
        result = self.analyzer.analyze_article(article)
        
        self.assertIsInstance(result, NewsAnalysisResult)
        self.assertEqual(result.key_topics, ['AI', 'Deep Learning'])
        self.assertEqual(result.importance_score, 0.9)
        
        # Should call chain with correct parameters
        mock_chain.invoke.assert_called_once()
        call_args = mock_chain.invoke.call_args[0][0]
        self.assertEqual(call_args['title'], article.title)
        self.assertEqual(call_args['source'], article.source)
    
    @patch('ai_news.src.langchain_chains.NewsAnalyzer.analysis_chain')
    def test_analyze_article_error_handling(self, mock_chain):
        """Test article analysis error handling"""
        
        # Mock analysis error
        mock_chain.invoke.side_effect = Exception("LLM API Error")
        
        article = self.create_mock_article_data()
        result = self.analyzer.analyze_article(article)
        
        # Should return default result on error
        self.assertIsInstance(result, NewsAnalysisResult)
        self.assertEqual(result.key_topics, ['news'])
        self.assertEqual(result.importance_score, 0.5)
        self.assertEqual(result.category, 'General')
    
    def test_analyze_article_content_truncation(self):
        """Test that long content is truncated"""
        
        with patch.object(self.analyzer, 'analysis_chain') as mock_chain:
            mock_chain.invoke.return_value = NewsAnalysisResult(
                key_topics=['AI'],
                importance_score=0.7,
                category='Tech',
                summary='Test'
            )
            
            # Create article with very long content
            long_content = "Very long content " * 200  # > 2000 chars
            article = self.create_mock_article_data(content=long_content)
            
            self.analyzer.analyze_article(article)
            
            # Should truncate content to 2000 chars
            call_args = mock_chain.invoke.call_args[0][0]
            self.assertLessEqual(len(call_args['content']), 2000)


class TestBlogGenerator(BaseTestCase):
    """Test BlogGenerator LangChain component"""
    
    def setUp(self):
        super().setUp()
        
        self.mock_llm = Mock()
        
        with patch('ai_news.src.langchain_chains.ChatOpenAI', return_value=self.mock_llm):
            self.generator = BlogGenerator(model="gpt-4o-mini")
    
    def test_generator_initialization(self):
        """Test BlogGenerator initialization"""
        
        self.assertIsNotNone(self.generator.llm)
        self.assertIsNotNone(self.generator.output_parser)
        self.assertIsNotNone(self.generator.blog_chain)
    
    @patch('ai_news.src.langchain_chains.BlogGenerator.blog_chain')
    def test_generate_blog_post_success(self, mock_chain):
        """Test successful blog post generation"""
        
        mock_result = BlogPostStructure(
            title='AI News Weekly Roundup',
            introduction='This week in AI...',
            main_content='Key developments include...',
            conclusion='Looking ahead...',
            tags=['ai', 'news', 'weekly']
        )
        mock_chain.invoke.return_value = mock_result
        
        articles = self.create_mock_articles_list(count=3)
        result = self.generator.generate_blog_post('AI News', articles)
        
        self.assertIsInstance(result, BlogPostStructure)
        self.assertEqual(result.title, 'AI News Weekly Roundup')
        self.assertEqual(result.tags, ['ai', 'news', 'weekly'])
        
        # Should call chain with correct parameters
        mock_chain.invoke.assert_called_once()
    
    def test_generate_blog_post_article_limit(self):
        """Test that article count is limited"""
        
        with patch.object(self.generator, 'blog_chain') as mock_chain:
            mock_chain.invoke.return_value = BlogPostStructure(
                title='Test', introduction='Test', main_content='Test',
                conclusion='Test', tags=['test']
            )
            
            # Create more than 10 articles
            many_articles = self.create_mock_articles_list(count=15)
            
            self.generator.generate_blog_post('Test Topic', many_articles)
            
            # Should limit to 10 articles in summary
            call_args = mock_chain.invoke.call_args[0][0]
            articles_summary = call_args['articles_summary']
            
            # Count number of articles in summary (each starts with "- ")
            article_count = articles_summary.count('- ')
            self.assertLessEqual(article_count, 10)
    
    @patch('ai_news.src.langchain_chains.BlogGenerator.blog_chain')
    def test_generate_blog_post_error_handling(self, mock_chain):
        """Test blog generation error handling"""
        
        mock_chain.invoke.side_effect = Exception("Generation failed")
        
        articles = [self.create_mock_article_data()]
        result = self.generator.generate_blog_post('Test Topic', articles)
        
        # Should return fallback result on error
        self.assertIsInstance(result, BlogPostStructure)
        self.assertEqual(result.title, 'Test Topic - Latest Updates')


class TestNewsProcessingAgent(BaseTestCase):
    """Test NewsProcessingAgent LangChain agent"""
    
    def setUp(self):
        super().setUp()
        
        self.mock_llm = Mock()
        self.mock_agent_executor = Mock()
        
        with patch('ai_news.src.langchain_chains.ChatOpenAI', return_value=self.mock_llm), \
             patch('ai_news.src.langchain_chains.create_openai_functions_agent'), \
             patch('ai_news.src.langchain_chains.AgentExecutor', return_value=self.mock_agent_executor):
            
            self.agent = NewsProcessingAgent()
    
    def test_agent_initialization(self):
        """Test NewsProcessingAgent initialization"""
        
        self.assertIsNotNone(self.agent.llm)
        self.assertIsNotNone(self.agent.tools)
        self.assertIsNotNone(self.agent.agent_executor)
        
        # Should have created tools
        self.assertEqual(len(self.agent.tools), 3)
    
    def test_process_request_success(self):
        """Test successful request processing"""
        
        self.mock_agent_executor.invoke.return_value = {
            'output': 'Agent response to user query'
        }
        
        response = self.agent.process_request('What are the latest AI trends?')
        
        self.assertEqual(response, 'Agent response to user query')
        self.mock_agent_executor.invoke.assert_called_once_with({
            'input': 'What are the latest AI trends?'
        })
    
    def test_process_request_error_handling(self):
        """Test request processing error handling"""
        
        self.mock_agent_executor.invoke.side_effect = Exception("Agent error")
        
        response = self.agent.process_request('Test query')
        
        # Should handle error gracefully
        self.assertIn('Sorry, I encountered an error', response)
    
    def test_agent_tools_creation(self):
        """Test that agent tools are created correctly"""
        
        tools = self.agent._create_tools()
        
        # Should have 3 tools
        self.assertEqual(len(tools), 3)
        
        # Check tool names
        tool_names = [tool.name for tool in tools]
        self.assertIn('search_articles', tool_names)
        self.assertIn('get_article_stats', tool_names)
        self.assertIn('analyze_trends', tool_names)


class TestLangChainNewsOrchestrator(BaseTestCase):
    """Test main LangChain orchestrator"""
    
    def setUp(self):
        super().setUp()
        
        # Mock all components
        self.mock_analyzer = Mock()
        self.mock_generator = Mock()
        self.mock_agent = Mock()
        
        with patch('ai_news.src.langchain_chains.NewsAnalyzer', return_value=self.mock_analyzer), \
             patch('ai_news.src.langchain_chains.BlogGenerator', return_value=self.mock_generator), \
             patch('ai_news.src.langchain_chains.NewsProcessingAgent', return_value=self.mock_agent):
            
            self.orchestrator = LangChainNewsOrchestrator()
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization"""
        
        self.assertIsNotNone(self.orchestrator.analyzer)
        self.assertIsNotNone(self.orchestrator.blog_generator)
        self.assertIsNotNone(self.orchestrator.agent)
    
    def test_process_articles_with_analysis(self):
        """Test processing articles with analysis"""
        
        # Mock analysis results
        mock_analysis = NewsAnalysisResult(
            key_topics=['AI', 'ML'],
            importance_score=0.8,
            category='Technology',
            summary='Test analysis'
        )
        self.mock_analyzer.analyze_article.return_value = mock_analysis
        
        articles = self.create_mock_articles_list(count=2)
        results = self.orchestrator.process_articles_with_analysis(articles)
        
        # Should return processed results
        self.assertEqual(len(results), 2)
        
        for result in results:
            self.assertIn('article', result)
            self.assertIn('analysis', result)
            self.assertIn('processed_at', result)
            
            # Analysis should be converted to dict (Pydantic v2)
            self.assertIsInstance(result['analysis'], dict)
    
    def test_create_intelligent_blog_post(self):
        """Test creating intelligent blog post"""
        
        # Mock analysis and generation
        mock_analysis = NewsAnalysisResult(
            key_topics=['AI'], importance_score=0.7,
            category='Tech', summary='Test'
        )
        self.mock_analyzer.analyze_article.return_value = mock_analysis
        
        mock_blog = BlogPostStructure(
            title='Generated Blog', introduction='Intro',
            main_content='Content', conclusion='Conclusion',
            tags=['ai']
        )
        self.mock_generator.generate_blog_post.return_value = mock_blog
        
        articles = [self.create_mock_article_data()]
        result = self.orchestrator.create_intelligent_blog_post('AI News', articles)
        
        # Should return complete result
        self.assertIn('blog_post', result)
        self.assertIn('analyzed_articles', result)
        self.assertIn('metadata', result)
        
        # Blog post should be dict (Pydantic v2)
        self.assertIsInstance(result['blog_post'], dict)
        
        # Metadata should contain correct info
        self.assertEqual(result['metadata']['topic'], 'AI News')
        self.assertEqual(result['metadata']['articles_processed'], 1)
    
    def test_create_intelligent_blog_post_error_handling(self):
        """Test blog post creation error handling"""
        
        # Mock analysis error
        self.mock_analyzer.analyze_article.side_effect = Exception("Analysis failed")
        
        articles = [self.create_mock_article_data()]
        result = self.orchestrator.create_intelligent_blog_post('AI News', articles)
        
        # Should return error result
        self.assertIn('error', result)
    
    def test_interactive_news_query(self):
        """Test interactive news query"""
        
        self.mock_agent.process_request.return_value = 'Agent response'
        
        response = self.orchestrator.interactive_news_query('What is trending?')
        
        self.assertEqual(response, 'Agent response')
        self.mock_agent.process_request.assert_called_with('What is trending?')


class TestLangChainIntegration(BaseTestCase):
    """Integration tests for LangChain components"""
    
    @patch('ai_news.src.langchain_chains.ChatOpenAI')
    def test_full_analysis_pipeline(self, mock_openai):
        """Test complete analysis pipeline"""
        
        # Mock OpenAI responses
        mock_llm = Mock()
        
        # Mock analysis response
        analysis_response = Mock()
        analysis_response.content = json.dumps({
            'key_topics': ['AI', 'Machine Learning'],
            'importance_score': 0.85,
            'category': 'Technology',
            'summary': 'Breakthrough in AI research'
        })
        
        mock_llm.invoke.return_value = analysis_response
        mock_openai.return_value = mock_llm
        
        # Test full pipeline
        orchestrator = LangChainNewsOrchestrator()
        
        articles = self.create_mock_articles_list(count=2)
        
        # This would normally use real LangChain components
        # In test, we're verifying the structure and flow
        self.assertIsNotNone(orchestrator.analyzer)
        self.assertIsNotNone(orchestrator.blog_generator)
        self.assertIsNotNone(orchestrator.agent)
    
    def test_pydantic_model_serialization(self):
        """Test Pydantic model serialization for API compatibility"""
        
        # Test NewsAnalysisResult serialization
        analysis = NewsAnalysisResult(
            key_topics=['AI', 'ML'],
            importance_score=0.9,
            category='Tech',
            summary='Test summary'
        )
        
        # Should be serializable to dict
        analysis_dict = analysis.model_dump()
        self.assertIsInstance(analysis_dict, dict)
        self.assertEqual(analysis_dict['key_topics'], ['AI', 'ML'])
        
        # Test BlogPostStructure serialization
        blog_post = BlogPostStructure(
            title='Test Blog',
            introduction='Intro',
            main_content='Content',
            conclusion='Conclusion',
            tags=['test']
        )
        
        blog_dict = blog_post.model_dump()
        self.assertIsInstance(blog_dict, dict)
        self.assertEqual(blog_dict['title'], 'Test Blog')