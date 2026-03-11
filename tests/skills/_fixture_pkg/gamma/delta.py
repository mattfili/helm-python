"""Delta submodule — has name collision with alpha.add."""


def add(x, y):
    """Add values (collides with alpha.add)."""
    return x + y


class Processor:
    """A data processor with a mode setting."""

    def __init__(self, mode="default"):
        self.mode = mode

    def run(self):
        return f"processing in {self.mode} mode"
