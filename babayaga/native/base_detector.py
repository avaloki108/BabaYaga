"""Base detector classes for native security analysis."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class Severity(Enum):
    """Standardized severity levels."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"


class DetectorCategory(Enum):
    """Detector categories."""
    REENTRANCY = "reentrancy"
    ACCESS_CONTROL = "access_control"
    ARITHMETIC = "arithmetic"
    EXTERNAL_CALLS = "external_calls"
    TIMESTAMP = "timestamp"
    RANDOMNESS = "randomness"
    DELEGATECALL = "delegatecall"
    SELFDESTRUCT = "selfdestruct"
    STORAGE = "storage"
    DEPRECATED = "deprecated"
    GAS_OPTIMIZATION = "gas_optimization"
    CODE_QUALITY = "code_quality"
    LOGIC_ERRORS = "logic_errors"


@dataclass
class DetectorMetadata:
    """Metadata about a detector implementation.
    
    This metadata enables easy tracking of which upstream tool version
    a detector is based on, making updates straightforward.
    """
    # Detector identification
    detector_id: str
    name: str
    description: str
    
    # Upstream tool information
    source_tool: str  # e.g., "slither", "mythril", "securify2"
    source_version: str  # Version of the source tool this is based on
    source_detector_id: Optional[str] = None  # ID in the source tool
    
    # Classification
    severity: Severity = Severity.MEDIUM
    confidence: float = 0.7
    category: DetectorCategory = DetectorCategory.CODE_QUALITY
    
    # Documentation
    references: List[str] = field(default_factory=list)
    swc_id: Optional[str] = None
    cwe_id: Optional[str] = None
    
    # Implementation details
    enabled_by_default: bool = True
    last_updated: Optional[str] = None  # ISO date when last synced with upstream
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            'detector_id': self.detector_id,
            'name': self.name,
            'description': self.description,
            'source_tool': self.source_tool,
            'source_version': self.source_version,
            'source_detector_id': self.source_detector_id,
            'severity': self.severity.value,
            'confidence': self.confidence,
            'category': self.category.value,
            'references': self.references,
            'swc_id': self.swc_id,
            'cwe_id': self.cwe_id,
            'enabled_by_default': self.enabled_by_default,
            'last_updated': self.last_updated
        }


@dataclass
class DetectorFinding:
    """A finding from a detector."""
    detector_id: str
    title: str
    description: str
    severity: Severity
    confidence: float
    
    # Location information
    file_path: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    function_name: Optional[str] = None
    contract_name: Optional[str] = None
    
    # Additional details
    code_snippet: Optional[str] = None
    remediation: Optional[str] = None
    references: List[str] = field(default_factory=list)
    
    # Technical details
    swc_id: Optional[str] = None
    cwe_id: Optional[str] = None
    category: Optional[DetectorCategory] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            'detector_id': self.detector_id,
            'title': self.title,
            'description': self.description,
            'severity': self.severity.value,
            'confidence': self.confidence,
            'file_path': self.file_path,
            'line_number': self.line_number,
            'column_number': self.column_number,
            'function_name': self.function_name,
            'contract_name': self.contract_name,
            'code_snippet': self.code_snippet,
            'remediation': self.remediation,
            'references': self.references,
            'swc_id': self.swc_id,
            'cwe_id': self.cwe_id,
            'category': self.category.value if self.category else None
        }


class BaseDetector(ABC):
    """Base class for all native detectors.
    
    Each detector should implement the analyze method and provide
    metadata about its capabilities and upstream tool version.
    """
    
    def __init__(self):
        self._metadata = self.get_metadata()
    
    @abstractmethod
    def get_metadata(self) -> DetectorMetadata:
        """Return metadata about this detector.
        
        This should include information about which upstream tool
        and version this detector is based on.
        """
        pass
    
    @abstractmethod
    async def analyze(self, contract_source: str, file_path: str, 
                     additional_context: Optional[Dict[str, Any]] = None) -> List[DetectorFinding]:
        """Analyze contract source code for vulnerabilities.
        
        Args:
            contract_source: The Solidity source code to analyze
            file_path: Path to the source file
            additional_context: Optional additional context (AST, etc.)
            
        Returns:
            List of findings from this detector
        """
        pass
    
    @property
    def metadata(self) -> DetectorMetadata:
        """Get detector metadata."""
        return self._metadata
    
    @property
    def detector_id(self) -> str:
        """Get detector ID."""
        return self._metadata.detector_id
    
    @property
    def is_enabled(self) -> bool:
        """Check if detector is enabled by default."""
        return self._metadata.enabled_by_default
    
    def _extract_code_snippet(self, source: str, line_number: int, 
                            context_lines: int = 3) -> str:
        """Extract code snippet around a line number.
        
        Args:
            source: Full source code
            line_number: Line number to extract around
            context_lines: Number of lines of context before/after
            
        Returns:
            Code snippet with context
        """
        lines = source.split('\n')
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)
        
        snippet_lines = []
        for i in range(start, end):
            line_num = i + 1
            marker = ">>> " if line_num == line_number else "    "
            snippet_lines.append(f"{marker}{line_num:4d} | {lines[i]}")
        
        return '\n'.join(snippet_lines)
