"""Environment configuration loader.

Loads environment variables from .env file into os.environ.
"""
import os
from dotenv import load_dotenv

load_dotenv()
