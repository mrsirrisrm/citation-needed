#!/usr/bin/env python3
"""
Test runner for Citation Fact-Checker
"""
import sys
import subprocess
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def run_test_suite():
    """Run the complete test suite"""
    print("🧪 Citation Fact-Checker Test Suite")
    print("=" * 50)

    # Check if we have API keys for extended tests
    has_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
    has_firecrawl = bool(os.getenv("FIRECRAWL_API_KEY"))

    print(f"API Keys Available:")
    print(f"  OpenRouter: {'✓' if has_openrouter else '✗'}")
    print(f"  Firecrawl: {'✓' if has_firecrawl else '✗'}")
    print()

    # Run individual test files
    test_files = [
        ("tests/test_ner.py", "NER Citation Extraction"),
        ("tests/test_fact_checker.py", "Fact-Checking"),
        ("tests/test_integration.py", "Integration Tests"),
    ]

    all_passed = True

    for test_file, description in test_files:
        print(f"Running {description} Tests...")
        print("-" * 40)

        try:
            # Try to run the test file directly
            result = subprocess.run([sys.executable, test_file],
                                  capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                print(f"✓ {description} tests PASSED")
                # Print last few lines of output
                output_lines = result.stdout.split('\n')
                for line in output_lines[-3:]:
                    if line.strip():
                        print(f"  {line}")
            else:
                print(f"✗ {description} tests FAILED")
                print("STDOUT:", result.stdout[-500:])  # Last 500 chars
                print("STDERR:", result.stderr[-500:])
                all_passed = False

        except subprocess.TimeoutExpired:
            print(f"✗ {description} tests TIMED OUT")
            all_passed = False
        except Exception as e:
            print(f"✗ {description} tests ERROR: {e}")
            all_passed = False

        print()

    # Summary
    print("=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print()
        print("Your Citation Fact-Checker is ready to use!")
        if not has_openrouter:
            print("ℹ  Add OPENROUTER_API_KEY to .env for full functionality")
        if not has_firecrawl:
            print("ℹ  Add FIRECRAWL_API_KEY to .env for real web search")
    else:
        print("❌ SOME TESTS FAILED")
        print("Please review the errors above and fix any issues.")

    return all_passed


def run_specific_test(test_name):
    """Run a specific test"""
    test_map = {
        "ner": "tests/test_ner.py",
        "fact": "tests/test_fact_checker.py",
        "integration": "tests/test_integration.py",
    }

    if test_name not in test_map:
        print(f"Unknown test: {test_name}")
        print(f"Available tests: {', '.join(test_map.keys())}")
        return False

    test_file = test_map[test_name]
    print(f"Running {test_name} tests...")

    try:
        result = subprocess.run([sys.executable, test_file],
                              capture_output=False, timeout=120)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running test: {e}")
        return False


def run_pytest():
    """Run tests using pytest"""
    print("Running tests with pytest...")
    try:
        result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"],
                              timeout=180)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running pytest: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "pytest":
            success = run_pytest()
        elif command in ["ner", "fact", "integration"]:
            success = run_specific_test(command)
        else:
            print(f"Usage: {sys.argv[0]} [pytest|ner|fact|integration]")
            sys.exit(1)
    else:
        success = run_test_suite()

    sys.exit(0 if success else 1)