"""Base exceptions for ODInfo application."""


class ODInfoException(Exception):
    """Base exception for ODInfo application."""
    
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}