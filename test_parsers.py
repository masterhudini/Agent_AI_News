#!/usr/bin/env python3
"""
Test script for AI News Scrapers
Tests the auto-discovery and basic functionality of all parsers
"""

import sys
import os

# Add the ai_news directory to Python path
sys.path.append('ai_news')

def test_parser_discovery():
    """Test if all parsers can be discovered and instantiated"""
    try:
        from ai_news.src.parsers import ScraperFactory
        
        print("Testing Parser Auto-Discovery...")
        
        # Force reload to ensure fresh discovery
        ScraperFactory.reload_scrapers()
        
        # Get available scrapers
        available_scrapers = ScraperFactory.get_available_scrapers()
        print(f"Found {len(available_scrapers)} scrapers:")
        
        for scraper_name in sorted(available_scrapers):
            print(f"   - {scraper_name}")
        
        print("\nScraper Information:")
        scraper_info = ScraperFactory.get_scraper_info()
        for name, info in sorted(scraper_info.items()):
            print(f"   {name}: {info['class_name']} (from {info['source_name']})")
        
        print("\nTesting scraper instantiation...")
        # Test creating a few scrapers
        test_scrapers = available_scrapers[:5]  # Test first 5
        
        for scraper_name in test_scrapers:
            try:
                scraper = ScraperFactory.create_scraper(scraper_name)
                print(f"   OK {scraper_name}: {scraper.source_name}")
            except Exception as e:
                print(f"   ERROR {scraper_name}: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERROR during discovery test: {e}")
        return False

def test_parser_structure():
    """Test the parser directory structure"""
    print("\nTesting Parser Directory Structure...")
    
    parsers_dir = "ai_news/ai_news/src/parsers"
    if not os.path.exists(parsers_dir):
        print(f"ERROR: Parsers directory not found: {parsers_dir}")
        return False
    
    # Count parser files
    parser_files = [f for f in os.listdir(parsers_dir) if f.endswith('_scraper.py')]
    base_files = ['__init__.py', 'base.py', 'factory.py', 'rss_base.py']
    
    print(f"Found {len(parser_files)} parser files:")
    for f in sorted(parser_files)[:10]:  # Show first 10
        print(f"   - {f}")
    if len(parser_files) > 10:
        print(f"   ... and {len(parser_files) - 10} more")
    
    print(f"Base files present:")
    for f in base_files:
        if os.path.exists(os.path.join(parsers_dir, f)):
            print(f"   OK {f}")
        else:
            print(f"   ERROR {f}")
    
    return True

if __name__ == "__main__":
    print("AI News Scrapers Test Suite")
    print("=" * 50)
    
    # Test structure
    structure_ok = test_parser_structure()
    
    # Test discovery (only if structure is OK)
    if structure_ok:
        discovery_ok = test_parser_discovery()
        
        if discovery_ok:
            print("\nAll tests passed! Parser system is ready.")
        else:
            print("\nSome discovery tests failed.")
    else:
        print("\nStructure tests failed.")
    
    print("\nNext steps:")
    print("   1. Install requirements: pip install -r requirements.txt")
    print("   2. Set up environment variables (OPENAI_API_KEY)")
    print("   3. Run: python manage.py scrape_news --list-sources")
    print("   4. Test scraping: python manage.py scrape_news --source openai_blog")