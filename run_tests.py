#!/usr/bin/env python3
"""
Main test runner for AI News Scraper
Provides easy access to test suite from project root
"""

import os
import sys

# Add Django app to path
django_path = os.path.join(os.path.dirname(__file__), 'ai_news')
if django_path not in sys.path:
    sys.path.insert(0, django_path)

# Import and run the test runner
from ai_news.tests.test_runner import AINewsTestRunner

def main():
    """Run the test suite"""
    
    print("🚀 AI News Scraper - Test Suite Runner")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('ai_news/ai_news/tests'):
        print("❌ Error: Tests directory not found!")
        print("   Make sure you're running this from the project root directory.")
        return False
    
    # Initialize and run tests
    runner = AINewsTestRunner()
    
    # Pass command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print("\n📖 Test Runner Usage:")
            print("  python run_tests.py                    # Run all tests")
            print("  python run_tests.py parsers            # Run parser tests")
            print("  python run_tests.py deduplication      # Run deduplication tests") 
            print("  python run_tests.py summarization      # Run summarization tests")
            print("  python run_tests.py langchain          # Run LangChain tests")
            print("  python run_tests.py news_service       # Run service tests")
            print("  python run_tests.py commands           # Run management command tests")
            print("  python run_tests.py --list             # List available tests")
            print("  python run_tests.py --help             # Show this help")
            print("\n🎯 Specific Test Examples:")
            print("  python run_tests.py test_factory       # Run factory tests")
            print("  python run_tests.py test_base          # Run base class tests")
            return True
        
        elif sys.argv[1] == '--list':
            categories = runner.get_test_categories()
            
            print("\n📋 Available Test Files:")
            print("-" * 30)
            
            total_tests = 0
            for category, tests in categories.items():
                if tests:
                    print(f"\n🎯 {category} ({len(tests)} files):")
                    for test in sorted(tests):
                        print(f"  • {test}")
                    total_tests += len(tests)
            
            print(f"\n📊 Total: {total_tests} test files")
            print("\n💡 Run specific category with: python run_tests.py <category_name>")
            return True
        
        else:
            # Run specific test
            pattern = sys.argv[1]
            print(f"🔍 Running tests matching: '{pattern}'")
            success = runner.run_specific_test(pattern)
            return success
    
    else:
        # Run all tests
        print("🧪 Running complete test suite...")
        print()
        success = runner.run_tests()
        
        if success:
            print("\n🎉 Test Suite Summary:")
            print("  ✅ All components tested successfully")
            print("  ✅ Parsers: Auto-discovery, RSS feeds, API scrapers")
            print("  ✅ Services: Deduplication, summarization, orchestration") 
            print("  ✅ LangChain: Analysis, generation, agents")
            print("  ✅ Commands: Scraping, analysis management")
            print("\n🚀 System ready for deployment!")
        
        return success


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏸️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)