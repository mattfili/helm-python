"""Beta submodule with classes."""

from abc import ABC, abstractmethod


class Widget:
    """A simple widget with a name and size."""

    def __init__(self, name, size=10):
        self.name = name
        self.size = size

    def describe(self):
        return f"{self.name} (size={self.size})"


class AbstractBase(ABC):
    """Abstract base that should be skipped."""

    @abstractmethod
    def do_thing(self):
        ...
