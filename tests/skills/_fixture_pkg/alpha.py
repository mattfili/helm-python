"""Alpha submodule with functions."""


def add(a, b):
    """Add two numbers together."""
    return a + b


def multiply(a, b):
    """Multiply two numbers."""
    return a * b


def _private_helper():
    """This should not be discovered."""
    return "secret"
