"""Native implementations of Slither detectors.

These detectors recreate the functionality of Slither's detectors
without requiring the Slither binary. Each detector tracks the
upstream Slither version it's based on for easy updates.
"""

from .reentrancy import ReentrancyDetector
from .tx_origin import TxOriginDetector
from .unchecked_call import UncheckedCallDetector
from .integer_overflow import IntegerOverflowDetector
from .timestamp_dependence import TimestampDependenceDetector
from .block_hash_usage import BlockHashUsageDetector
from .access_control import AccessControlDetector

__all__ = [
    'ReentrancyDetector',
    'TxOriginDetector',
    'UncheckedCallDetector',
    'IntegerOverflowDetector',
    'TimestampDependenceDetector',
    'BlockHashUsageDetector',
    'AccessControlDetector',
]
