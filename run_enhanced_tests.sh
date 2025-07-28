#!/bin/bash

# Enhanced test runner script with coverage and reporting
# Usage: ./run_enhanced_tests.sh [test_type] [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="all"
COVERAGE=true
GENERATE_REPORTS=true
PARALLEL=false
VERBOSE=false
SHOW_SLOWEST=false

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Help function
show_help() {
    cat << EOF
Enhanced Test Runner for Legal RAG API

Usage: $0 [OPTIONS] [TEST_TYPE]

TEST_TYPE:
    all         Run all tests (default)
    unit        Run unit tests only
    integration Run integration tests only
    e2e         Run end-to-end tests only
    performance Run performance tests only
    stress      Run stress tests only
    exceptions  Run exception handling tests only
    smoke       Run smoke tests only
    critical    Run critical tests only

OPTIONS:
    -h, --help          Show this help message
    -c, --coverage      Generate coverage report (default: true)
    --no-coverage       Disable coverage reporting
    -r, --reports       Generate HTML reports (default: true)
    --no-reports        Disable HTML report generation
    -p, --parallel      Run tests in parallel
    -v, --verbose       Verbose output
    -s, --slowest       Show slowest tests
    --fast              Run tests without slow markers
    --smoke-only        Run only smoke tests for quick validation

Examples:
    $0                          # Run all tests with coverage
    $0 unit                     # Run unit tests only
    $0 --no-coverage e2e        # Run e2e tests without coverage
    $0 -p --verbose unit        # Run unit tests in parallel with verbose output
    $0 --smoke-only             # Quick smoke test validation
    $0 --fast                   # Run tests excluding slow ones

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        -r|--reports)
            GENERATE_REPORTS=true
            shift
            ;;
        --no-reports)
            GENERATE_REPORTS=false
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -s|--slowest)
            SHOW_SLOWEST=true
            shift
            ;;
        --fast)
            FAST_MODE=true
            shift
            ;;
        --smoke-only)
            TEST_TYPE="smoke"
            shift
            ;;
        *)
            if [[ "$1" =~ ^(all|unit|integration|e2e|performance|stress|exceptions|smoke|critical)$ ]]; then
                TEST_TYPE="$1"
            else
                print_error "Unknown option: $1"
                show_help
                exit 1
            fi
            shift
            ;;
    esac
done

# Create necessary directories
print_info "Setting up test environment..."
mkdir -p test_reports
mkdir -p htmlcov
mkdir -p logs

# Check if server is needed for integration/e2e tests
check_server_needed() {
    if [[ "$TEST_TYPE" == "integration" ]] || [[ "$TEST_TYPE" == "e2e" ]] || [[ "$TEST_TYPE" == "all" ]]; then
        return 0
    fi
    return 1
}

# Check server status
check_server_status() {
    if check_server_needed; then
        print_info "Checking server status..."
        if curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
            print_success "Server is running"
        else
            print_warning "Server is not running. Integration/E2E tests may fail."
            print_info "To start the server, run: python manage.py start-server"
        fi
    fi
}

# Build pytest command
build_pytest_cmd() {
    local cmd="uv run python -m pytest"
    
    # Add test selection based on type
    case $TEST_TYPE in
        "unit")
            cmd="$cmd -m 'unit and not integration and not e2e'"
            ;;
        "integration")
            cmd="$cmd -m 'integration'"
            ;;
        "e2e")
            cmd="$cmd -m 'e2e'"
            ;;
        "performance")
            cmd="$cmd -m 'performance'"
            ;;
        "stress")
            cmd="$cmd -m 'stress'"
            ;;
        "exceptions")
            cmd="$cmd -m 'exceptions'"
            ;;
        "smoke")
            cmd="$cmd -m 'smoke'"
            ;;
        "critical")
            cmd="$cmd -m 'critical'"
            ;;
        "all")
            if [[ "$FAST_MODE" == "true" ]]; then
                cmd="$cmd -m 'not slow'"
            fi
            ;;
    esac
    
    # Add coverage options
    if [[ "$COVERAGE" == "true" ]]; then
        cmd="$cmd --cov=. --cov-report=term-missing"
        if [[ "$GENERATE_REPORTS" == "true" ]]; then
            cmd="$cmd --cov-report=html:htmlcov --cov-report=xml:test_reports/coverage.xml"
        fi
    fi
    
    # Add HTML report
    if [[ "$GENERATE_REPORTS" == "true" ]]; then
        cmd="$cmd --html=test_reports/report.html --self-contained-html"
    fi
    
    # Add parallel execution
    if [[ "$PARALLEL" == "true" ]]; then
        cmd="$cmd -n auto"
    fi
    
    # Add verbose output
    if [[ "$VERBOSE" == "true" ]]; then
        cmd="$cmd -v"
    else
        cmd="$cmd -q"
    fi
    
    # Add slowest tests report
    if [[ "$SHOW_SLOWEST" == "true" ]]; then
        cmd="$cmd --durations=10"
    fi
    
    # Additional options
    cmd="$cmd --tb=short --strict-markers --color=yes"
    
    echo "$cmd"
}

# Clean previous test artifacts
clean_artifacts() {
    print_info "Cleaning previous test artifacts..."
    rm -rf .pytest_cache
    rm -rf test_reports/*.xml
    rm -rf test_reports/*.html
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
}

# Main execution
main() {
    print_info "Starting Enhanced Test Runner"
    print_info "Test Type: $TEST_TYPE"
    print_info "Coverage: $COVERAGE"
    print_info "Reports: $GENERATE_REPORTS"
    print_info "Parallel: $PARALLEL"
    
    # Clean artifacts
    clean_artifacts
    
    # Check server status
    check_server_status
    
    # Build and execute pytest command
    local pytest_cmd=$(build_pytest_cmd)
    print_info "Running command: $pytest_cmd"
    
    echo ""
    print_info "🧪 Executing tests..."
    echo ""
    
    # Execute tests
    if eval $pytest_cmd; then
        print_success "Tests completed successfully!"
        
        # Generate additional reports
        if [[ "$GENERATE_REPORTS" == "true" ]]; then
            print_info "Generating additional reports..."
            
            # Generate coverage badge (if coverage available)
            if [[ "$COVERAGE" == "true" ]] && command -v coverage-badge &> /dev/null; then
                coverage-badge -o test_reports/coverage.svg
                print_success "Coverage badge generated"
            fi
            
            # Generate test summary
            echo "{\"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\", \"test_type\": \"$TEST_TYPE\", \"status\": \"success\"}" > test_reports/summary.json
        fi
        
        # Show final results
        echo ""
        print_success "🎉 All tests passed!"
        
        if [[ "$COVERAGE" == "true" ]] && [[ "$GENERATE_REPORTS" == "true" ]]; then
            print_info "📊 Coverage report available at: htmlcov/index.html"
        fi
        
        if [[ "$GENERATE_REPORTS" == "true" ]]; then
            print_info "📋 Test report available at: test_reports/report.html"
        fi
        
    else
        print_error "Tests failed!"
        
        # Generate failure report
        if [[ "$GENERATE_REPORTS" == "true" ]]; then
            echo "{\"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\", \"test_type\": \"$TEST_TYPE\", \"status\": \"failed\"}" > test_reports/summary.json
        fi
        
        print_info "📋 Check test reports for details"
        exit 1
    fi
}

# Run main function
main "$@"
