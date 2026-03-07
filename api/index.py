"""
Vercel Serverless Function Handler
Imports FastAPI app from api.py
"""

import sys
from pathlib import Path

# Add parent directory to path to import api.py
sys.path.insert(0, str(Path(__file__).parent.parent))

from api import app

# Export app for Vercel
__all__ = ["app"]
