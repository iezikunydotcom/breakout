"""WSGI entry point for production hosts (PythonAnywhere, gunicorn, etc.)."""

from app import app as application

app = application
