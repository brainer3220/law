"""
Test runner script for Legal RAG API
"""
import sys
import subprocess
import argparse
from pathlib import Path
import time
import requests


def check_server_running(base_url: str = "http://localhost:8000") -> bool:
    """Check if the API server is running"""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("data_loaded", False)
    except:
        pass
    return False


def run_tests(test_type: str = "unit", verbose: bool = True, coverage: bool = False):
    """Run tests based on type"""
    
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term"])
    
    # Test selection based on type
    if test_type == "unit":
        cmd.extend([
            "tests/test_comprehensive.py::TestModels",
            "tests/test_comprehensive.py::TestDataLoader", 
            "tests/test_comprehensive.py::TestCacheManager",
            "tests/test_comprehensive.py::TestRetrievers",
            "tests/test_comprehensive.py::TestUtilities",
            "-m", "not integration"
        ])
        print("🧪 Running unit tests...")
        
    elif test_type == "integration":
        if not check_server_running():
            print("❌ Server is not running. Please start the server first:")
            print("   python manage.py start")
            return False
            
        cmd.extend([
            "tests/test_comprehensive.py::TestAPIEndpoints",
            "tests/test_comprehensive.py::TestIntegration",
            "tests/test_e2e.py",
            "-m", "integration"
        ])
        print("🔗 Running integration tests...")
        
    elif test_type == "performance":
        if not check_server_running():
            print("❌ Server is not running. Please start the server first:")
            print("   python manage.py start")
            return False
            
        cmd.extend([
            "tests/test_performance.py",
            "-m", "performance",
            "-s"  # Don't capture output for performance tests
        ])
        print("⚡ Running performance tests...")
        
    elif test_type == "e2e":
        if not check_server_running():
            print("❌ Server is not running. Please start the server first:")
            print("   python manage.py start")
            return False
            
        cmd.append("tests/test_e2e.py")
        print("🎯 Running end-to-end tests...")
        
    elif test_type == "all":
        if not check_server_running():
            print("❌ Server is not running for integration tests.")
            print("   Only unit tests will run.")
            cmd.extend(["tests/", "-m", "not integration"])
        else:
            cmd.append("tests/")
        print("🚀 Running all tests...")
        
    else:
        print(f"❌ Unknown test type: {test_type}")
        return False
    
    # Run the tests
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\\n⏹️ Tests interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def generate_test_report():
    """Generate comprehensive test report"""
    print("📊 Generating test report...")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "--cov=.",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "--cov-report=term-missing",
        "--html=test_report.html",
        "--self-contained-html",
        "-v"
    ]
    
    try:
        subprocess.run(cmd, cwd=Path(__file__).parent)
        print("✅ Test report generated:")
        print("   📄 HTML Report: test_report.html") 
        print("   📊 Coverage Report: htmlcov/index.html")
        return True
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Legal RAG API Test Runner")
    parser.add_argument(
        "test_type",
        choices=["unit", "integration", "performance", "e2e", "all", "report"],
        default="unit",
        nargs="?",
        help="Type of tests to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true", 
        help="Generate coverage report"
    )
    parser.add_argument(
        "--check-server",
        action="store_true",
        help="Only check if server is running"
    )
    
    args = parser.parse_args()
    
    if args.check_server:
        if check_server_running():
            print("✅ Server is running and ready")
            sys.exit(0)
        else:
            print("❌ Server is not running or not ready")
            sys.exit(1)
    
    print("🧪 Legal RAG API Test Runner")
    print("=" * 40)
    
    if args.test_type == "report":
        success = generate_test_report()
    else:
        success = run_tests(
            test_type=args.test_type,
            verbose=args.verbose,
            coverage=args.coverage
        )
    
    if success:
        print("\\n✅ Tests completed successfully!")
        sys.exit(0)
    else:
        print("\\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
