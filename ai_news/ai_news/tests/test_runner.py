#!/usr/bin/env python3
"""
Comprehensive test runner for AI News Scraper
Runs all tests with coverage reporting and detailed output
"""

import os
import sys
import unittest
import logging
from io import StringIO

# Configure logging for tests
logging.disable(logging.CRITICAL)

class AINewsTestRunner:
    """Custom test runner for AI News Scraper"""
    
    def __init__(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_dir = os.path.dirname(os.path.dirname(self.test_dir))
        
        # Add project to Python path
        if self.project_dir not in sys.path:
            sys.path.insert(0, self.project_dir)
    
    def discover_tests(self):
        """Discover all test cases"""
        loader = unittest.TestLoader()
        
        # Discover tests in the tests directory
        test_suite = loader.discover(
            start_dir=self.test_dir,
            pattern='test_*.py',
            top_level_dir=self.project_dir
        )
        
        return test_suite
    
    def run_tests(self, verbosity=2):
        """Run all tests with specified verbosity"""
        
        print("🧪 AI News Scraper - Test Suite")
        print("=" * 50)
        
        # Discover tests
        test_suite = self.discover_tests()
        
        # Count total tests
        test_count = test_suite.countTestCases()
        print(f"📋 Total tests found: {test_count}")
        print()
        
        # Run tests
        runner = unittest.TextTestRunner(
            verbosity=verbosity,
            stream=sys.stdout,
            descriptions=True,
            failfast=False
        )
        
        result = runner.run(test_suite)
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("-" * 20)
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
        
        if result.wasSuccessful():
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed!")
            
            if result.failures:
                print("\n🔥 Failures:")
                for test, traceback in result.failures:
                    print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
            
            if result.errors:
                print("\n💥 Errors:")
                for test, traceback in result.errors:
                    print(f"  - {test}: {traceback.split()[-1]}")
        
        return result.wasSuccessful()
    
    def run_specific_test(self, test_pattern):
        """Run specific test matching pattern"""
        
        loader = unittest.TestLoader()
        
        try:
            # Try to load specific test
            if '.' in test_pattern:
                # Module.class.method format
                suite = loader.loadTestsFromName(test_pattern)
            else:
                # Pattern format
                suite = loader.discover(
                    start_dir=self.test_dir,
                    pattern=f'*{test_pattern}*.py',
                    top_level_dir=self.project_dir
                )
            
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(suite)
            
            return result.wasSuccessful()
            
        except Exception as e:
            print(f"❌ Error running test '{test_pattern}': {e}")
            return False
    
    def get_test_categories(self):
        """Get categorized test information"""
        
        categories = {
            'Parser Tests': [],
            'Service Tests': [], 
            'LangChain Tests': [],
            'Command Tests': [],
            'Integration Tests': []
        }
        
        test_files = []
        for root, dirs, files in os.walk(self.test_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(os.path.join(root, file))
        
        for test_file in test_files:
            rel_path = os.path.relpath(test_file, self.test_dir)
            
            if 'parsers' in rel_path:
                categories['Parser Tests'].append(rel_path)
            elif 'management' in rel_path:
                categories['Command Tests'].append(rel_path)
            elif 'langchain' in rel_path:
                categories['LangChain Tests'].append(rel_path)
            elif any(svc in rel_path for svc in ['deduplication', 'summarization', 'news_service']):
                categories['Service Tests'].append(rel_path)
            else:
                categories['Integration Tests'].append(rel_path)
        
        return categories


def main():
    """Main test runner function"""
    
    runner = AINewsTestRunner()
    
    if len(sys.argv) > 1:
        # Run specific test
        test_pattern = sys.argv[1]
        
        if test_pattern == '--list':
            # List all test categories
            categories = runner.get_test_categories()
            
            print("📋 Available Test Categories:")
            print("=" * 30)
            
            for category, tests in categories.items():
                if tests:
                    print(f"\n🎯 {category}:")
                    for test in tests:
                        print(f"  - {test}")
            
            print("\n💡 Usage:")
            print("  python test_runner.py                 # Run all tests")
            print("  python test_runner.py parsers         # Run parser tests") 
            print("  python test_runner.py --list          # List test categories")
            
            return True
        
        else:
            # Run specific test pattern
            success = runner.run_specific_test(test_pattern)
            return success
    
    else:
        # Run all tests
        success = runner.run_tests()
        return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)