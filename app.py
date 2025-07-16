"""
Event JSON & Image Editor - Main Application Entry Point
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
root_path = Path(__file__).parent
sys.path.insert(0, str(root_path))

# Import and run the main function
from src.ui.main_app import main

if __name__ == "__main__":
    main() 