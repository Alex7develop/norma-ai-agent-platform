"""Shared security primitives.

Authentication and authorization intentionally remain outside this foundation.
Future implementations should depend on abstractions from this module instead
of coupling API handlers directly to a token or identity provider.
"""

from typing import Final

AUTHORIZATION_SCHEME: Final = "Bearer"
