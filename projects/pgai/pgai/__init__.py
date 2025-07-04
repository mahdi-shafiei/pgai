__version__ = "0.11.4"

from pgai._install.install import ainstall, install

from .tracing import configure_tracing

configure_tracing()

__all__ = ["ainstall", "install"]
