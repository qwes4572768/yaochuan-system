#!/usr/bin/env python
"""於 backend 目錄執行：python run_tests.py"""
import sys
import subprocess

if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]))
