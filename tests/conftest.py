"""Shared pytest configuration for Reconbuddy tests."""
import os
import sys

# Ensure project root is on path so helper_functions can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
