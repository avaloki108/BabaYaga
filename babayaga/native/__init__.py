"""Native security analysis implementations.

This package contains native implementations of security analysis capabilities
from leading tools (Slither, Mythril, Medusa, Securify2) without depending on
their binaries.

The architecture supports easy updates by tracking tool versions and providing
clear mappings to upstream detectors.
"""

from .detector_registry import DetectorRegistry, get_registry, register_detector
from .base_detector import BaseDetector, DetectorMetadata, DetectorFinding, Severity, DetectorCategory
from .native_engine import NativeAnalysisEngine

__all__ = [
    'DetectorRegistry',
    'get_registry', 
    'register_detector',
    'BaseDetector',
    'DetectorMetadata',
    'DetectorFinding',
    'Severity',
    'DetectorCategory',
    'NativeAnalysisEngine',
]
