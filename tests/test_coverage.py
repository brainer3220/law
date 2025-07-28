"""
Coverage reporting and test quality metrics
"""
import pytest
import coverage
import json
import time
from pathlib import Path
from typing import Dict, Any


class CoverageReporter:
    """Custom test coverage reporter"""
    
    def __init__(self):
        self.coverage_data = {}
        self.start_time = None
        self.end_time = None
    
    def start_coverage(self):
        """Start coverage collection"""
        self.start_time = time.time()
        # Coverage is handled by pytest-cov, this is for additional metrics
    
    def stop_coverage(self):
        """Stop coverage collection"""
        self.end_time = time.time()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate coverage report"""
        return {
            "timestamp": time.time(),
            "duration": self.end_time - self.start_time if self.end_time and self.start_time else 0,
            "additional_metrics": self.coverage_data
        }


@pytest.fixture(scope="session")
def coverage_reporter():
    """Fixture for coverage reporting"""
    reporter = CoverageReporter()
    reporter.start_coverage()
    yield reporter
    reporter.stop_coverage()


def pytest_sessionstart(session):
    """Called after the Session object has been created"""
    print("🧪 Starting test session with coverage reporting...")
    
    # Create coverage reports directory
    reports_dir = Path("test_reports")
    reports_dir.mkdir(exist_ok=True)


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished"""
    print(f"\n✅ Test session finished with exit status: {exitstatus}")
    
    # Generate test summary
    if hasattr(session, 'testscollected'):
        print(f"📊 Tests collected: {session.testscollected}")
    
    # Create test summary report
    reports_dir = Path("test_reports")
    summary_file = reports_dir / "test_summary.json"
    
    summary = {
        "timestamp": time.time(),
        "exit_status": exitstatus,
        "tests_collected": getattr(session, 'testscollected', 0),
        "session_duration": getattr(session, 'duration', 0)
    }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)


def pytest_runtest_setup(item):
    """Called to perform the setup phase for a test item"""
    # Mark test start time
    item._test_start_time = time.time()


def pytest_runtest_teardown(item, nextitem):
    """Called to perform the teardown phase for a test item"""
    # Calculate test duration
    if hasattr(item, '_test_start_time'):
        duration = time.time() - item._test_start_time
        if duration > 10:  # Log slow tests
            print(f"⚠️ Slow test detected: {item.nodeid} took {duration:.2f}s")


def pytest_report_teststatus(report, config):
    """Called to report test status"""
    if report.when == "call":
        if report.passed:
            return "PASSED", "✅", "PASSED"
        elif report.failed:
            return "FAILED", "❌", "FAILED"
        elif report.skipped:
            return "SKIPPED", "⏭️", "SKIPPED"
    return None


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Add additional information to terminal summary"""
    terminalreporter.write_sep("=", "Test Quality Metrics")
    
    # Get test results
    passed = len(terminalreporter.stats.get('passed', []))
    failed = len(terminalreporter.stats.get('failed', []))
    skipped = len(terminalreporter.stats.get('skipped', []))
    total = passed + failed + skipped
    
    if total > 0:
        success_rate = (passed / total) * 100
        terminalreporter.write_line(f"📊 Success Rate: {success_rate:.1f}% ({passed}/{total})")
        terminalreporter.write_line(f"❌ Failed Tests: {failed}")
        terminalreporter.write_line(f"⏭️ Skipped Tests: {skipped}")
        
        # Quality assessment
        if success_rate >= 95:
            terminalreporter.write_line("🏆 Test Quality: Excellent")
        elif success_rate >= 90:
            terminalreporter.write_line("🥇 Test Quality: Very Good")
        elif success_rate >= 80:
            terminalreporter.write_line("🥈 Test Quality: Good")
        elif success_rate >= 70:
            terminalreporter.write_line("🥉 Test Quality: Fair")
        else:
            terminalreporter.write_line("⚠️ Test Quality: Needs Improvement")
    
    # Coverage reminder
    terminalreporter.write_sep("-", "Coverage Report")
    terminalreporter.write_line("📈 To view detailed coverage report:")
    terminalreporter.write_line("   Open: htmlcov/index.html")
    terminalreporter.write_line("   Or run: coverage report --show-missing")


# Hook for custom markers
def pytest_configure(config):
    """Configure additional pytest settings"""
    # Add quality markers
    config.addinivalue_line(
        "markers",
        "critical: mark test as critical (must pass for release)"
    )
    config.addinivalue_line(
        "markers", 
        "regression: mark test as regression test"
    )
    config.addinivalue_line(
        "markers",
        "smoke: mark test as smoke test (quick validation)"
    )
