"""Private submodule — public callables here should still be discovered."""


def _secret():
    """Private function, should not be discovered."""
    return "hidden"


def public_from_internal():
    """A public function inside a private submodule."""
    return "visible"
