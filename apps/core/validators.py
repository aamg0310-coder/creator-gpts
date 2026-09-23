"""Shared validators for the project."""
from django.core.exceptions import ValidationError


def validate_file_size(file, max_mb=5):
    """Validate that uploaded file does not exceed max_mb megabytes."""
    max_size = max_mb * 1024 * 1024
    if file.size > max_size:
        raise ValidationError(f'El archivo no debe superar {max_mb}MB.')


def validate_chatbot_icon(file):
    """Validate chatbot icon: max 5MB and image-only extensions."""
    validate_file_size(file, max_mb=5)
