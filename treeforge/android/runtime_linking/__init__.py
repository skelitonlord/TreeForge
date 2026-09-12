"""
Android Runtime Linking namespace.

Runtime Linking sits immediately downstream of Android Device Universe.

This package intentionally performs no eager imports. Runtime Linking models
and stages consume canonical Universe identities, while temporary Universe
compatibility surfaces may import Runtime Linking implementation modules
during the controlled stage extraction.

Keeping the package root inert prevents package-initialization cycles during
that transition.
"""
