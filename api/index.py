#!/usr/bin/env python3
"""
Vercel serverless function entry point
"""

from ..server import app

# This is required for Vercel
def handler(request, response):
    return app(request, response)