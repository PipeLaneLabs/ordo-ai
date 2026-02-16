"""
Multi-Tier Agent Ecosystem

A production-ready, LangGraph-native multi-agent system designed to automate
the full software development lifecycle using a tiered architecture (Tier 0-5).
"""

import os


# --- FIX: Read version from Docker build arg/env if available ---
# If running locally without Docker, it defaults to "0.0.0"
__version__ = os.getenv("POETRY_DYNAMIC_VERSIONING_BYPASS", "0.0.0")

__author__ = "Harman"
