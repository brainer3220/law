#!/usr/bin/env python3
"""
Utility script for managing the Legal RAG API
"""
import argparse
import subprocess
import sys
import time
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000"

def start_server(host="0.0.0.0", port=8000, reload=True):
    """Start the FastAPI server"""
    print(f"🚀 Starting Legal RAG API server on {host}:{port}")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔍 API Status: http://localhost:8000/health")
    print("⏹️  Press Ctrl+C to stop")
    print("-" * 60)
    
    try:
        cmd = [
            sys.executable, "-m", "uvicorn", "main:app",
            "--host", host,
            "--port", str(port),
            "--log-level", "info"
        ]
        
        if reload:
            cmd.append("--reload")
        
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

def test_api():
    """Run API tests"""
    print("🧪 Running API tests...")
    try:
        subprocess.run([sys.executable, "test_api.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed with exit code {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ test_api.py not found")
        sys.exit(1)

def check_health():
    """Check API health"""
    try:
        print("🏥 Checking API health...")
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API is healthy!")
            print(f"   Data loaded: {data.get('data_loaded', False)}")
            print(f"   Total sentences: {data.get('total_sentences', 0)}")
            print(f"   Total documents: {data.get('total_documents', 0)}")
            
            models = data.get('models_ready', {})
            print("   Models ready:")
            for model, status in models.items():
                status_icon = "✅" if status else "❌"
                print(f"     {model}: {status_icon}")
        else:
            print(f"❌ API health check failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is the server running?")
    except Exception as e:
        print(f"❌ Health check error: {e}")

def clear_cache():
    """Clear API cache"""
    try:
        print("🧹 Clearing cache...")
        response = requests.delete(f"{BASE_URL}/cache", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Cache cleared successfully!")
            print(f"   Files deleted: {len(data.get('deleted_files', []))}")
            print(f"   Space freed: {data.get('freed_space_mb', 0):.2f} MB")
        else:
            print(f"❌ Failed to clear cache: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is the server running?")
    except Exception as e:
        print(f"❌ Cache clear error: {e}")

def reload_data():
    """Reload API data"""
    try:
        print("🔄 Reloading data and models...")
        response = requests.post(f"{BASE_URL}/reload", timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Data reloaded successfully!")
            print(f"   Total sentences: {data.get('total_sentences', 0)}")
            print(f"   Total documents: {data.get('total_documents', 0)}")
            print(f"   Execution time: {data.get('execution_time_ms', 0):.2f}ms")
            
            models = data.get('models_initialized', {})
            print("   Models initialized:")
            for model, status in models.items():
                status_icon = "✅" if status else "❌"
                print(f"     {model}: {status_icon}")
        else:
            print(f"❌ Failed to reload data: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is the server running?")
    except Exception as e:
        print(f"❌ Reload error: {e}")

def install_deps():
    """Install dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True)
        print("✅ Dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)

def setup_env():
    """Setup environment"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print("⚙️  Creating .env file from .env.example...")
        env_file.write_text(env_example.read_text(encoding='utf-8'), encoding='utf-8')
        print("✅ .env file created. Please review and modify as needed.")
    elif env_file.exists():
        print("ℹ️  .env file already exists.")
    else:
        print("❌ .env.example not found. Cannot create .env file.")

def main():
    parser = argparse.ArgumentParser(description="Legal RAG API Management Utility")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start server command
    start_parser = subparsers.add_parser("start", help="Start the API server")
    start_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    start_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    start_parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    
    # Other commands
    subparsers.add_parser("test", help="Run API tests")
    subparsers.add_parser("health", help="Check API health")
    subparsers.add_parser("clear-cache", help="Clear API cache")
    subparsers.add_parser("reload", help="Reload API data")
    subparsers.add_parser("install", help="Install dependencies")
    subparsers.add_parser("setup", help="Setup environment")
    
    args = parser.parse_args()
    
    if args.command == "start":
        start_server(args.host, args.port, not args.no_reload)
    elif args.command == "test":
        test_api()
    elif args.command == "health":
        check_health()
    elif args.command == "clear-cache":
        clear_cache()
    elif args.command == "reload":
        reload_data()
    elif args.command == "install":
        install_deps()
    elif args.command == "setup":
        setup_env()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
