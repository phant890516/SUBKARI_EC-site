# ==========================================================
# Filename      : config.py
# Descriptions  : Configuration
# ==========================================================
import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'subkari_default_secret_key_2025'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=240)
