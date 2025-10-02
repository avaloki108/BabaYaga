"""Native implementations of Securify2 detectors.

These detectors recreate the functionality of Securify2's Datalog-based
analysis without requiring the Securify2 binary. Each detector tracks the
upstream Securify2 version it's based on for easy updates.
"""

from .integer_overflow import IntegerOverflowDetector
from .uninitialized_storage import UninitializedStorageDetector
from .missing_access_control import MissingAccessControlDetector
from .timestamp_dependence import TimestampDependenceDetector
from .unsafe_delegatecall import UnsafeDelegatecallDetector
from .unprotected_selfdestruct import UnprotectedSelfdestructDetector
from .locked_ether import LockedEtherDetector

__all__ = [
    'IntegerOverflowDetector',
    'UninitializedStorageDetector',
    'MissingAccessControlDetector',
    'TimestampDependenceDetector',
    'UnsafeDelegatecallDetector',
    'UnprotectedSelfdestructDetector',
    'LockedEtherDetector',
]
