"""
Development settings for core project.
Uses SQLite by default.
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']


EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

CORS_ALLOW_ALL_ORIGINS = True

