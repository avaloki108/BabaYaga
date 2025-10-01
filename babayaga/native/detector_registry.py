"""Detector registry for managing native detectors."""

import logging
from typing import Dict, List, Optional, Type
from pathlib import Path
import json

from .base_detector import BaseDetector, DetectorFinding, DetectorMetadata


logger = logging.getLogger(__name__)


class DetectorRegistry:
    """Registry for native security detectors.
    
    This registry manages all available detectors and provides
    mechanisms to track upstream tool versions for easy updates.
    """
    
    def __init__(self):
        self._detectors: Dict[str, BaseDetector] = {}
        self._metadata_cache: Dict[str, DetectorMetadata] = {}
        
    def register(self, detector_class: Type[BaseDetector]) -> None:
        """Register a detector class.
        
        Args:
            detector_class: Detector class to register
        """
        try:
            detector = detector_class()
            detector_id = detector.detector_id
            
            if detector_id in self._detectors:
                logger.warning(f"Detector {detector_id} already registered, overwriting")
            
            self._detectors[detector_id] = detector
            self._metadata_cache[detector_id] = detector.metadata
            
            logger.info(f"Registered detector: {detector_id} "
                       f"(from {detector.metadata.source_tool} "
                       f"v{detector.metadata.source_version})")
            
        except Exception as e:
            logger.error(f"Failed to register detector {detector_class.__name__}: {e}")
    
    def get_detector(self, detector_id: str) -> Optional[BaseDetector]:
        """Get a detector by ID.
        
        Args:
            detector_id: ID of the detector to retrieve
            
        Returns:
            Detector instance or None if not found
        """
        return self._detectors.get(detector_id)
    
    def get_all_detectors(self) -> List[BaseDetector]:
        """Get all registered detectors.
        
        Returns:
            List of all detector instances
        """
        return list(self._detectors.values())
    
    def get_enabled_detectors(self) -> List[BaseDetector]:
        """Get all enabled detectors.
        
        Returns:
            List of enabled detector instances
        """
        return [d for d in self._detectors.values() if d.is_enabled]
    
    def get_detectors_by_tool(self, tool_name: str) -> List[BaseDetector]:
        """Get all detectors from a specific upstream tool.
        
        Args:
            tool_name: Name of the upstream tool (e.g., "slither", "mythril")
            
        Returns:
            List of detectors from that tool
        """
        return [d for d in self._detectors.values() 
                if d.metadata.source_tool == tool_name]
    
    def get_detectors_by_category(self, category: str) -> List[BaseDetector]:
        """Get all detectors for a specific category.
        
        Args:
            category: Category name
            
        Returns:
            List of detectors in that category
        """
        return [d for d in self._detectors.values() 
                if d.metadata.category.value == category]
    
    async def run_detector(self, detector_id: str, contract_source: str, 
                          file_path: str, **kwargs) -> List[DetectorFinding]:
        """Run a specific detector.
        
        Args:
            detector_id: ID of detector to run
            contract_source: Source code to analyze
            file_path: Path to source file
            **kwargs: Additional arguments for the detector
            
        Returns:
            List of findings
        """
        detector = self.get_detector(detector_id)
        if not detector:
            logger.warning(f"Detector {detector_id} not found")
            return []
        
        try:
            findings = await detector.analyze(contract_source, file_path, kwargs)
            logger.info(f"Detector {detector_id} found {len(findings)} issues")
            return findings
        except Exception as e:
            logger.error(f"Error running detector {detector_id}: {e}")
            return []
    
    async def run_all_detectors(self, contract_source: str, file_path: str, 
                               only_enabled: bool = True, **kwargs) -> List[DetectorFinding]:
        """Run all detectors on the given contract.
        
        Args:
            contract_source: Source code to analyze
            file_path: Path to source file
            only_enabled: Only run enabled detectors
            **kwargs: Additional arguments for detectors
            
        Returns:
            Aggregated list of all findings
        """
        detectors = self.get_enabled_detectors() if only_enabled else self.get_all_detectors()
        all_findings = []
        
        for detector in detectors:
            try:
                findings = await detector.analyze(contract_source, file_path, kwargs)
                all_findings.extend(findings)
                logger.debug(f"Detector {detector.detector_id}: {len(findings)} findings")
            except Exception as e:
                logger.error(f"Error in detector {detector.detector_id}: {e}")
        
        logger.info(f"Total findings from {len(detectors)} detectors: {len(all_findings)}")
        return all_findings
    
    def get_version_info(self) -> Dict[str, Dict[str, str]]:
        """Get version information for all registered detectors.
        
        This is useful for tracking which upstream tool versions
        the native detectors are based on.
        
        Returns:
            Dictionary mapping detector IDs to version info
        """
        version_info = {}
        
        for detector_id, metadata in self._metadata_cache.items():
            version_info[detector_id] = {
                'source_tool': metadata.source_tool,
                'source_version': metadata.source_version,
                'source_detector_id': metadata.source_detector_id or 'N/A',
                'last_updated': metadata.last_updated or 'Unknown'
            }
        
        return version_info
    
    def export_version_manifest(self, output_path: Path) -> None:
        """Export version manifest to a JSON file.
        
        This file can be used to track which upstream versions
        each detector is based on, making it easy to identify
        which detectors need updating.
        
        Args:
            output_path: Path to write manifest file
        """
        manifest = {
            'detectors': {},
            'summary': {
                'total_detectors': len(self._detectors),
                'by_tool': {}
            }
        }
        
        # Build detector info
        for detector_id, metadata in self._metadata_cache.items():
            manifest['detectors'][detector_id] = {
                'name': metadata.name,
                'source_tool': metadata.source_tool,
                'source_version': metadata.source_version,
                'source_detector_id': metadata.source_detector_id,
                'last_updated': metadata.last_updated,
                'enabled': metadata.enabled_by_default
            }
            
            # Update summary
            tool = metadata.source_tool
            if tool not in manifest['summary']['by_tool']:
                manifest['summary']['by_tool'][tool] = {
                    'count': 0,
                    'version': metadata.source_version
                }
            manifest['summary']['by_tool'][tool]['count'] += 1
        
        # Write manifest
        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Exported version manifest to {output_path}")
    
    def get_detector_status(self) -> Dict[str, Any]:
        """Get status of all registered detectors.
        
        Returns:
            Dictionary with detector statistics
        """
        enabled_count = len(self.get_enabled_detectors())
        total_count = len(self._detectors)
        
        by_tool = {}
        for detector in self._detectors.values():
            tool = detector.metadata.source_tool
            by_tool[tool] = by_tool.get(tool, 0) + 1
        
        return {
            'total_detectors': total_count,
            'enabled_detectors': enabled_count,
            'disabled_detectors': total_count - enabled_count,
            'by_tool': by_tool
        }


# Global registry instance
_global_registry = DetectorRegistry()


def get_registry() -> DetectorRegistry:
    """Get the global detector registry.
    
    Returns:
        Global DetectorRegistry instance
    """
    return _global_registry


def register_detector(detector_class: Type[BaseDetector]) -> None:
    """Register a detector with the global registry.
    
    Args:
        detector_class: Detector class to register
    """
    _global_registry.register(detector_class)
