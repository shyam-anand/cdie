#!/usr/bin/env python3
"""
Test runner script for the cdie project.
"""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run all tests using pytest."""
    # Get the project root directory
    project_root = Path(__file__).parent

    # Run pytest with coverage
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "--verbose",
        "--tb=short",
        "--cov=src/cdie",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
    ]

    print("Running tests with coverage...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 80)

    try:
        result = subprocess.run(cmd, cwd=project_root, check=True)
        print("\n" + "=" * 80)
        print("✅ All tests passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 80)
        print(f"❌ Tests failed with exit code {e.returncode}")
        return e.returncode


def run_specific_test(test_file):
    """Run a specific test file."""
    project_root = Path(__file__).parent
    test_path = project_root / "tests" / test_file

    if not test_path.exists():
        print(f"❌ Test file not found: {test_path}")
        return 1

    cmd = [sys.executable, "-m", "pytest", str(test_path), "--verbose", "--tb=short"]

    print(f"Running specific test: {test_file}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 80)

    try:
        result = subprocess.run(cmd, cwd=project_root, check=True)
        print("\n" + "=" * 80)
        print("✅ Test passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 80)
        print(f"❌ Test failed with exit code {e.returncode}")
        return e.returncode


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Run specific test file
        test_file = sys.argv[1]
        return run_specific_test(test_file)
    else:
        # Run all tests
        return run_tests()


if __name__ == "__main__":
    sys.exit(main())
