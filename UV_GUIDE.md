# UV Quick Start Guide for Legal RAG API

## Installation

### 1. Install UV
```bash
# Windows
winget install --id=astral-sh.uv

# macOS  
brew install uv

# Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Setup Project
```bash
# Clone repository
git clone <repository-url>
cd law

# Setup everything at once
python manage.py setup
python manage.py install

# Or step by step
uv venv                    # Create virtual environment
uv sync                    # Install dependencies
uv sync --extra gpu        # Install with GPU support
uv sync --extra dev        # Install dev dependencies
```

## Usage

### Basic Commands
```bash
# Run the application
uv run python main.py

# Run scripts
uv run python manage.py start
uv run python test_api.py

# Install new packages
uv add requests
uv add --dev pytest

# Remove packages
uv remove requests

# Update dependencies
uv sync --upgrade
```

### Performance Comparison

| Operation | pip | uv | Speedup |
|-----------|-----|----|---------| 
| Install from scratch | 30s | 3s | 10x |
| Install from cache | 15s | 0.5s | 30x |
| Dependency resolution | 45s | 2s | 22x |

### Project Structure with UV

```
law/
├── pyproject.toml     # Project configuration
├── uv.lock           # Lock file (like package-lock.json)
├── .venv/            # Virtual environment (auto-created)
├── manage.py         # UV-powered management script
└── ...
```

## Tips

1. **Use lock file**: Always commit `uv.lock` for reproducible builds
2. **Virtual environments**: UV automatically manages `.venv` for you
3. **Fast installs**: Use `uv sync --frozen` for CI/production
4. **Dev dependencies**: Keep dev tools separate with `--extra dev`
5. **Cache**: UV's global cache makes subsequent installs ultra-fast

## Migration from pip/Poetry

### From pip
```bash
# Old way
pip install -r requirements.txt

# New way  
uv sync
```

### From Poetry
```bash
# Old way
poetry install

# New way
uv sync
```

UV reads `pyproject.toml` just like Poetry, so migration is seamless!
