"""Walking skeleton for the NEXT substrate body.

This package is a composition demonstrator. Its deterministic behavior is
authored and is never evidence about language-model memory.
"""

from .runtime import BodyRuntime, DeterministicModelStub, Environment, Task

__all__ = ["BodyRuntime", "DeterministicModelStub", "Environment", "Task"]
