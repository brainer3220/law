#!/usr/bin/env python3
"""
Management script for Legal RAG API using UV
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd: list, check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess:
    """Run a command with proper error handling"""
    print(f"🔧 Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True,
            cwd=Path(__file__).parent
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        if capture_output and e.stdout:
            print(f"STDOUT: {e.stdout}")
        if capture_output and e.stderr:
            print(f"STDERR: {e.stderr}")
        sys.exit(1)


def check_uv_installed():
    """Check if UV is installed"""
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ UV version: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ UV is not installed. Please install it first:")
    print("   Windows: winget install --id=astral-sh.uv")
    print("   macOS: brew install uv")
    print("   Linux: curl -LsSf https://astral.sh/uv/install.sh | sh")
    print("   Or visit: https://docs.astral.sh/uv/getting-started/installation/")
    return False


def install_deps(gpu: bool = False, dev: bool = False):
    """Install dependencies using UV"""
    print("📦 Installing dependencies with UV...")
    
    if not check_uv_installed():
        return False
    
    # Create virtual environment if it doesn't exist
    if not Path(".venv").exists():
        print("🔨 Creating virtual environment...")
        run_command(["uv", "venv"])
    
    # Install dependencies
    cmd = ["uv", "sync"]
    
    if gpu:
        cmd.extend(["--extra", "gpu"])
        print("🚀 Installing with GPU support...")
    
    if dev:
        cmd.extend(["--extra", "dev"])
        print("🔧 Installing development dependencies...")
    
    run_command(cmd)
    print("✅ Dependencies installed successfully!")
    return True


def setup_environment():
    """Setup the development environment"""
    print("🛠️ Setting up development environment...")
    
    # Create necessary directories
    dirs = ["cache", "logs", "datasets"]
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"📁 Created directory: {dir_name}")
    
    # Copy environment file if it doesn't exist
    if not Path(".env").exists():
        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("📄 Created .env file from .env.example")
        else:
            # Create basic .env file
            env_content = """# Legal RAG API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
EMBEDDING_MODEL=jhgan/ko-sroberta-multitask
TFIDF_MAX_FEATURES=10000
CACHE_DIR=cache
ENABLE_CACHE=true
DEFAULT_TOP_K=5
MAX_TOP_K=100
MIN_SIMILARITY_SCORE=0.1
BATCH_SIZE=32
LOG_LEVEL=INFO
LOG_FILE=legal_rag.log
"""
            with open(".env", "w", encoding="utf-8") as f:
                f.write(env_content)
            print("📄 Created basic .env file")
    
    print("✅ Environment setup completed!")


def start_server(host: str = None, port: int = None, no_reload: bool = False):
    """Start the API server"""
    print("🚀 Starting Legal RAG API server...")
    
    if not check_uv_installed():
        return False
    
    # Build uvicorn command
    cmd = ["uv", "run", "uvicorn", "main:app"]
    
    # Add host and port
    if host:
        cmd.extend(["--host", host])
    else:
        cmd.extend(["--host", "0.0.0.0"])
    
    if port:
        cmd.extend(["--port", str(port)])
    else:
        cmd.extend(["--port", "8000"])
    
    # Add reload if not disabled
    if not no_reload:
        cmd.append("--reload")
    
    try:
        subprocess.run(cmd, cwd=Path(__file__).parent)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")


def run_tests(test_type: str = "unit", coverage: bool = False):
    """Run the test suite"""
    print(f"🧪 Running {test_type} tests...")
    
    if not check_uv_installed():
        return False
    
    # Check if server is needed for integration tests
    if test_type in ["integration", "e2e", "performance", "all"]:
        print("🔍 Checking if server is running...")
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code != 200:
                print("❌ Server is not running. Please start it first:")
                print("   python manage.py start")
                return False
            
            health_data = response.json()
            if not health_data.get("data_loaded"):
                print("❌ Server is running but data is not loaded.")
                return False
                
            print("✅ Server is running and ready")
            
        except ImportError:
            print("📦 Installing requests for server check...")
            run_command(["uv", "add", "requests", "--group", "dev"])
            print("🔄 Please run the test command again")
            return False
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            print("   Please start the server first: python manage.py start")
            return False
    
    # Build test command
    cmd = ["uv", "run", "python", "-m", "pytest"]
    
    if test_type == "unit":
        cmd.extend([
            "tests/test_comprehensive.py::TestModels",
            "tests/test_comprehensive.py::TestDataLoader",
            "tests/test_comprehensive.py::TestCacheManager", 
            "tests/test_comprehensive.py::TestRetrievers",
            "-m", "not integration"
        ])
    elif test_type == "integration":
        cmd.extend([
            "tests/test_comprehensive.py::TestAPIEndpoints",
            "tests/test_comprehensive.py::TestIntegration",
            "-m", "integration"
        ])
    elif test_type == "performance":
        cmd.extend(["tests/test_performance.py", "-s"])
    elif test_type == "e2e":
        cmd.extend(["tests/test_e2e.py"])
    elif test_type == "all":
        cmd.append("tests/")
    else:
        cmd.extend(["tests/", "-k", test_type])
    
    # Add coverage if requested
    if coverage:
        cmd.extend([
            "--cov=.",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml"
        ])
    
    # Add verbose output
    cmd.extend(["-v", "--tb=short"])
    
    try:
        run_command(cmd)
        print("✅ Tests completed!")
        
        if coverage:
            print("📊 Coverage report generated:")
            print("   HTML: htmlcov/index.html")
            print("   XML: coverage.xml")
        
        return True
        
    except Exception as e:
        print(f"❌ Tests failed: {e}")
        return False


def check_health():
    """Check API health"""
    print("🏥 Checking API health...")
    
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API is healthy!")
            print(f"   Status: {data.get('status')}")
            print(f"   Data loaded: {data.get('data_loaded')}")
            print(f"   Total sentences: {data.get('total_sentences')}")
            
            models = data.get('models_ready', {})
            print("   Models ready:")
            for model, ready in models.items():
                status = "✅" if ready else "❌"
                print(f"     {model}: {status}")
        else:
            print(f"❌ API returned status {response.status_code}")
            print(f"   Response: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is the server running?")
        print("   Start the server with: python manage.py start")
    except ImportError:
        print("❌ requests library not found. Installing...")
        run_command(["uv", "add", "requests"])
        print("✅ Please run the health check again")
    except Exception as e:
        print(f"❌ Health check failed: {e}")


def clear_cache():
    """Clear application cache"""
    print("🧹 Clearing cache...")
    
    cache_dir = Path("cache")
    if cache_dir.exists():
        import shutil
        shutil.rmtree(cache_dir)
        cache_dir.mkdir()
        print("✅ Cache cleared successfully!")
    else:
        print("ℹ️ No cache directory found")


def reload_data():
    """Reload application data"""
    print("🔄 Reloading data...")
    
    try:
        import requests
        response = requests.post("http://localhost:8000/reload", timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Data reloaded successfully!")
            print(f"   Message: {data.get('message')}")
            print(f"   Total sentences: {data.get('total_sentences')}")
            print(f"   Total documents: {data.get('total_documents')}")
            print(f"   Execution time: {data.get('execution_time_ms', 0):.2f}ms")
        else:
            print(f"❌ Reload failed with status {response.status_code}")
            print(f"   Response: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is the server running?")
    except ImportError:
        print("❌ requests library not found. Installing...")
        run_command(["uv", "add", "requests"])
        print("✅ Please run the reload command again")
    except Exception as e:
        print(f"❌ Reload failed: {e}")


def format_code():
    """Format code using black and isort"""
    print("🎨 Formatting code...")
    
    if not check_uv_installed():
        return False
    
    try:
        print("Running black...")
        run_command(["uv", "run", "black", "."])
        
        print("Running isort...")
        run_command(["uv", "run", "isort", "."])
        
        print("✅ Code formatted successfully!")
    except Exception as e:
        print(f"❌ Code formatting failed: {e}")
        print("💡 Make sure dev dependencies are installed: python manage.py install --dev")


def lint_code():
    """Lint code using flake8 and mypy"""
    print("🔍 Linting code...")
    
    if not check_uv_installed():
        return False
    
    try:
        print("Running flake8...")
        run_command(["uv", "run", "flake8", ".", "--max-line-length=100"])
        
        print("Running mypy...")
        run_command(["uv", "run", "mypy", ".", "--ignore-missing-imports"])
        
        print("✅ Code linting completed!")
    except Exception as e:
        print(f"❌ Code linting failed: {e}")
        print("💡 Make sure dev dependencies are installed: python manage.py install --dev")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Legal RAG API Management Script")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Install command
    install_parser = subparsers.add_parser("install", help="Install dependencies")
    install_parser.add_argument("--gpu", action="store_true", help="Install GPU dependencies")
    install_parser.add_argument("--dev", action="store_true", help="Install development dependencies")
    
    # Setup command
    subparsers.add_parser("setup", help="Setup development environment")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the API server")
    start_parser.add_argument("--host", help="Host to bind to")
    start_parser.add_argument("--port", type=int, help="Port to bind to")
    start_parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument(
        "test_type", 
        nargs="?", 
        default="unit",
        choices=["unit", "integration", "performance", "e2e", "all"],
        help="Type of tests to run"
    )
    test_parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    subparsers.add_parser("health", help="Check API health")
    subparsers.add_parser("clear-cache", help="Clear application cache")
    subparsers.add_parser("reload", help="Reload application data")
    subparsers.add_parser("format", help="Format code with black and isort")
    subparsers.add_parser("lint", help="Lint code with flake8 and mypy")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print(f"🎯 Legal RAG API Management - Running: {args.command}")
    print("=" * 50)
    
    if args.command == "install":
        install_deps(gpu=args.gpu, dev=args.dev)
    elif args.command == "setup":
        setup_environment()
    elif args.command == "start":
        start_server(host=args.host, port=args.port, no_reload=args.no_reload)
    elif args.command == "test":
        run_tests(test_type=args.test_type, coverage=args.coverage)
    elif args.command == "health":
        check_health()
    elif args.command == "clear-cache":
        clear_cache()
    elif args.command == "reload":
        reload_data()
    elif args.command == "format":
        format_code()
    elif args.command == "lint":
        lint_code()


if __name__ == "__main__":
    main()
