"""
Android application-service namespace.

Application capabilities are owned and imported from their concrete modules.
This package intentionally performs no eager cross-application imports.

Keeping this boundary inert allows standalone production workflows such as
Discovery, Extraction, and Parsing to run without initializing unrelated
Reconstruction or later downstream services.
"""
