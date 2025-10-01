"""Unit tests for native detector implementations."""

import pytest
from unittest.mock import Mock

from babayaga.native.base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)
from babayaga.native.detector_registry import DetectorRegistry
from babayaga.native.slither_detectors.reentrancy import ReentrancyDetector
from babayaga.native.slither_detectors.tx_origin import TxOriginDetector
from babayaga.native.slither_detectors.unchecked_call import UncheckedCallDetector


class TestBaseDetector:
    """Test base detector functionality."""
    
    def test_detector_metadata_creation(self):
        """Test creating detector metadata."""
        metadata = DetectorMetadata(
            detector_id="test-detector",
            name="Test Detector",
            description="A test detector",
            source_tool="slither",
            source_version="0.10.0",
            source_detector_id="test",
            severity=Severity.HIGH,
            confidence=0.9,
            category=DetectorCategory.REENTRANCY
        )
        
        assert metadata.detector_id == "test-detector"
        assert metadata.severity == Severity.HIGH
        assert metadata.source_tool == "slither"
        
        metadata_dict = metadata.to_dict()
        assert metadata_dict['severity'] == 'High'
        assert metadata_dict['category'] == 'reentrancy'
    
    def test_detector_finding_creation(self):
        """Test creating detector findings."""
        finding = DetectorFinding(
            detector_id="test-detector",
            title="Test Finding",
            description="Test description",
            severity=Severity.HIGH,
            confidence=0.9,
            file_path="test.sol",
            line_number=10,
            function_name="testFunction"
        )
        
        assert finding.detector_id == "test-detector"
        assert finding.severity == Severity.HIGH
        assert finding.line_number == 10
        
        finding_dict = finding.to_dict()
        assert finding_dict['severity'] == 'High'
        assert finding_dict['file_path'] == "test.sol"


class TestDetectorRegistry:
    """Test detector registry functionality."""
    
    def test_registry_initialization(self):
        """Test registry can be created."""
        registry = DetectorRegistry()
        assert registry is not None
        assert len(registry.get_all_detectors()) == 0
    
    def test_register_detector(self):
        """Test registering a detector."""
        registry = DetectorRegistry()
        registry.register(ReentrancyDetector)
        
        detectors = registry.get_all_detectors()
        assert len(detectors) == 1
        assert detectors[0].detector_id == "native-reentrancy-eth"
    
    def test_get_detector_by_id(self):
        """Test retrieving detector by ID."""
        registry = DetectorRegistry()
        registry.register(ReentrancyDetector)
        
        detector = registry.get_detector("native-reentrancy-eth")
        assert detector is not None
        assert detector.detector_id == "native-reentrancy-eth"
    
    def test_get_detectors_by_tool(self):
        """Test filtering detectors by source tool."""
        registry = DetectorRegistry()
        registry.register(ReentrancyDetector)
        registry.register(TxOriginDetector)
        
        slither_detectors = registry.get_detectors_by_tool('slither')
        assert len(slither_detectors) == 2
    
    def test_get_version_info(self):
        """Test getting version information."""
        registry = DetectorRegistry()
        registry.register(ReentrancyDetector)
        
        version_info = registry.get_version_info()
        assert "native-reentrancy-eth" in version_info
        assert version_info["native-reentrancy-eth"]["source_tool"] == "slither"
        assert version_info["native-reentrancy-eth"]["source_version"] == "0.10.0"


class TestReentrancyDetector:
    """Test reentrancy detector."""
    
    @pytest.mark.asyncio
    async def test_detector_metadata(self):
        """Test reentrancy detector metadata."""
        detector = ReentrancyDetector()
        metadata = detector.get_metadata()
        
        assert metadata.detector_id == "native-reentrancy-eth"
        assert metadata.source_tool == "slither"
        assert metadata.severity == Severity.HIGH
        assert metadata.swc_id == "SWC-107"
    
    @pytest.mark.asyncio
    async def test_detect_reentrancy_pattern(self):
        """Test detecting reentrancy vulnerability."""
        detector = ReentrancyDetector()
        
        # Contract with reentrancy vulnerability
        vulnerable_code = """
        contract Vulnerable {
            mapping(address => uint256) public balances;
            
            function withdraw() public {
                uint256 amount = balances[msg.sender];
                msg.sender.call{value: amount}("");
                balances[msg.sender] = 0;
            }
        }
        """
        
        findings = await detector.analyze(vulnerable_code, "test.sol")
        
        # Should detect the reentrancy issue
        assert len(findings) >= 1
        assert findings[0].severity == Severity.HIGH
        assert "reentrancy" in findings[0].title.lower()
    
    @pytest.mark.asyncio
    async def test_no_false_positive_safe_code(self):
        """Test that safe code doesn't trigger false positives."""
        detector = ReentrancyDetector()
        
        # Safe contract with checks-effects-interactions pattern
        safe_code = """
        contract Safe {
            mapping(address => uint256) public balances;
            
            function withdraw() public {
                uint256 amount = balances[msg.sender];
                balances[msg.sender] = 0;
                msg.sender.call{value: amount}("");
            }
        }
        """
        
        findings = await detector.analyze(safe_code, "test.sol")
        
        # Should not detect issues in safe code
        assert len(findings) == 0


class TestTxOriginDetector:
    """Test tx.origin detector."""
    
    @pytest.mark.asyncio
    async def test_detector_metadata(self):
        """Test tx.origin detector metadata."""
        detector = TxOriginDetector()
        metadata = detector.get_metadata()
        
        assert metadata.detector_id == "native-tx-origin"
        assert metadata.source_tool == "slither"
        assert metadata.swc_id == "SWC-115"
    
    @pytest.mark.asyncio
    async def test_detect_tx_origin_usage(self):
        """Test detecting tx.origin usage."""
        detector = TxOriginDetector()
        
        # Contract using tx.origin for auth
        vulnerable_code = """
        contract Vulnerable {
            address owner;
            
            function restrictedFunction() public {
                require(tx.origin == owner, "Not owner");
                // do something
            }
        }
        """
        
        findings = await detector.analyze(vulnerable_code, "test.sol")
        
        assert len(findings) >= 1
        assert "tx.origin" in findings[0].title.lower()
    
    @pytest.mark.asyncio
    async def test_no_detection_msg_sender(self):
        """Test that msg.sender doesn't trigger detector."""
        detector = TxOriginDetector()
        
        # Safe contract using msg.sender
        safe_code = """
        contract Safe {
            address owner;
            
            function restrictedFunction() public {
                require(msg.sender == owner, "Not owner");
                // do something
            }
        }
        """
        
        findings = await detector.analyze(safe_code, "test.sol")
        
        assert len(findings) == 0


class TestUncheckedCallDetector:
    """Test unchecked call detector."""
    
    @pytest.mark.asyncio
    async def test_detector_metadata(self):
        """Test unchecked call detector metadata."""
        detector = UncheckedCallDetector()
        metadata = detector.get_metadata()
        
        assert metadata.detector_id == "native-unchecked-call"
        assert metadata.source_tool == "slither"
        assert metadata.swc_id == "SWC-104"
    
    @pytest.mark.asyncio
    async def test_detect_unchecked_call(self):
        """Test detecting unchecked external call."""
        detector = UncheckedCallDetector()
        
        # Contract with unchecked call
        vulnerable_code = """
        contract Vulnerable {
            function sendEther(address payable recipient) public {
                recipient.call{value: 1 ether}("");
            }
        }
        """
        
        findings = await detector.analyze(vulnerable_code, "test.sol")
        
        assert len(findings) >= 1
        assert "unchecked" in findings[0].title.lower()
    
    @pytest.mark.asyncio
    async def test_no_detection_checked_call(self):
        """Test that checked calls don't trigger detector."""
        detector = UncheckedCallDetector()
        
        # Safe contract checking call result
        safe_code = """
        contract Safe {
            function sendEther(address payable recipient) public {
                (bool success, ) = recipient.call{value: 1 ether}("");
                require(success, "Transfer failed");
            }
        }
        """
        
        findings = await detector.analyze(safe_code, "test.sol")
        
        assert len(findings) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
