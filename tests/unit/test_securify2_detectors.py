"""Unit tests for Securify2-inspired native detector implementations."""

import pytest
from unittest.mock import Mock

from babayaga.native.base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)
from babayaga.native.detector_registry import DetectorRegistry
from babayaga.native.securify2_detectors.integer_overflow import IntegerOverflowDetector
from babayaga.native.securify2_detectors.uninitialized_storage import UninitializedStorageDetector
from babayaga.native.securify2_detectors.missing_access_control import MissingAccessControlDetector
from babayaga.native.securify2_detectors.timestamp_dependence import TimestampDependenceDetector
from babayaga.native.securify2_detectors.unsafe_delegatecall import UnsafeDelegatecallDetector
from babayaga.native.securify2_detectors.unprotected_selfdestruct import UnprotectedSelfdestructDetector
from babayaga.native.securify2_detectors.locked_ether import LockedEtherDetector


class TestIntegerOverflowDetector:
    """Test integer overflow detector."""
    
    def test_detector_metadata(self):
        """Test detector has correct metadata."""
        detector = IntegerOverflowDetector()
        metadata = detector.metadata
        
        assert metadata.detector_id == "native-securify2-integer-overflow"
        assert metadata.source_tool == "securify2"
        assert metadata.severity == Severity.HIGH
        assert metadata.category == DetectorCategory.ARITHMETIC
        assert metadata.swc_id == "SWC-101"
    
    @pytest.mark.asyncio
    async def test_detect_overflow_pre_0_8(self):
        """Test detecting overflow in pre-0.8.0 Solidity."""
        detector = IntegerOverflowDetector()
        
        vulnerable_code = """
        pragma solidity ^0.7.0;
        contract Vulnerable {
            uint256 public balance;
            
            function add(uint256 amount) public {
                balance = balance + amount;
            }
        }
        """
        
        findings = await detector.analyze(vulnerable_code, "test.sol")
        
        # Should detect potential overflow
        assert len(findings) >= 1
        assert any('overflow' in f.description.lower() for f in findings)
    
    @pytest.mark.asyncio
    async def test_no_detection_with_safemath(self):
        """Test no detection when using SafeMath."""
        detector = IntegerOverflowDetector()
        
        safe_code = """
        pragma solidity ^0.7.0;
        import "@openzeppelin/contracts/math/SafeMath.sol";
        
        contract Safe {
            using SafeMath for uint256;
            uint256 public balance;
            
            function add(uint256 amount) public {
                balance = balance.add(amount);
            }
        }
        """
        
        findings = await detector.analyze(safe_code, "test.sol")
        
        # Should not detect issues with SafeMath
        assert len(findings) == 0
    
    @pytest.mark.asyncio
    async def test_no_detection_solidity_0_8(self):
        """Test no detection in Solidity 0.8.0+ (built-in checks)."""
        detector = IntegerOverflowDetector()
        
        safe_code = """
        pragma solidity ^0.8.0;
        contract Safe {
            uint256 public balance;
            
            function add(uint256 amount) public {
                balance = balance + amount;
            }
        }
        """
        
        findings = await detector.analyze(safe_code, "test.sol")
        
        # Should not detect in 0.8.0+
        assert len(findings) == 0


class TestUninitializedStorageDetector:
    """Test uninitialized storage pointer detector."""
    
    def test_detector_metadata(self):
        """Test detector has correct metadata."""
        detector = UninitializedStorageDetector()
        metadata = detector.metadata
        
        assert metadata.detector_id == "native-securify2-uninitialized-storage"
        assert metadata.source_tool == "securify2"
        assert metadata.severity == Severity.HIGH
        assert metadata.swc_id == "SWC-109"
    
    @pytest.mark.asyncio
    async def test_detect_uninitialized_storage(self):
        """Test detecting uninitialized storage pointer."""
        detector = UninitializedStorageDetector()
        
        vulnerable_code = """
        contract Vulnerable {
            struct Data {
                uint256 value;
            }
            
            function test() public {
                Data storage data;
                data.value = 100;
            }
        }
        """
        
        findings = await detector.analyze(vulnerable_code, "test.sol")
        
        # Should detect uninitialized storage
        assert len(findings) >= 1
        assert any('not initialized' in f.description.lower() or 'uninitialized' in f.description.lower() for f in findings)


class TestMissingAccessControlDetector:
    """Test missing access control detector."""
    
    def test_detector_metadata(self):
        """Test detector has correct metadata."""
        detector = MissingAccessControlDetector()
        metadata = detector.metadata
        
        assert metadata.detector_id == "native-securify2-missing-access-control"
        assert metadata.source_tool == "securify2"
        assert metadata.severity == Severity.CRITICAL
        assert metadata.swc_id == "SWC-105"
    
    @pytest.mark.asyncio
    async def test_detect_missing_access_control(self):
        """Test detecting missing access control."""
        detector = MissingAccessControlDetector()
        
        vulnerable_code = """
        contract Vulnerable {
            address public owner;
            uint256 public value;
            
            function setValue(uint256 newValue) public {
                value = newValue;
            }
        }
        """
        
        findings = await detector.analyze(vulnerable_code, "test.sol")
        
        # Should detect missing access control
        assert len(findings) >= 1
        assert any('access control' in f.description.lower() for f in findings)
    
    @pytest.mark.asyncio
    async def test_no_detection_with_access_control(self):
        """Test no detection when access control exists."""
        detector = MissingAccessControlDetector()
        
        safe_code = """
        contract Safe {
            address public owner;
            uint256 public value;
            
            modifier onlyOwner() {
                require(msg.sender == owner);
                _;
            }
            
            function setValue(uint256 newValue) public onlyOwner {
                value = newValue;
            }
        }
        """
        
        findings = await detector.analyze(safe_code, "test.sol")
        
        # Should not detect issues
        assert len(findings) == 0


class TestTimestampDependenceDetector:
    """Test timestamp dependence detector."""
    
    def test_detector_metadata(self):
        """Test detector has correct metadata."""
        detector = TimestampDependenceDetector()
        metadata = detector.metadata
        
        assert metadata.detector_id == "native-securify2-timestamp-dependence"
        assert metadata.source_tool == "securify2"
        assert metadata.severity == Severity.MEDIUM
        assert metadata.swc_id == "SWC-116"
    
    @pytest.mark.asyncio
    async def test_detect_timestamp_usage(self):
        """Test detecting timestamp dependence."""
        detector = TimestampDependenceDetector()
        
        vulnerable_code = """
        contract Vulnerable {
            function test() public view returns (bool) {
                if (block.timestamp > 1000) {
                    return true;
                }
                return false;
            }
        }
        """
        
        findings = await detector.analyze(vulnerable_code, "test.sol")
        
        # Should detect timestamp usage
        assert len(findings) >= 1
        assert any('timestamp' in f.description.lower() for f in findings)


class TestUnsafeDelegatecallDetector:
    """Test unsafe delegatecall detector."""
    
    def test_detector_metadata(self):
        """Test detector has correct metadata."""
        detector = UnsafeDelegatecallDetector()
        metadata = detector.metadata
        
        assert metadata.detector_id == "native-securify2-unsafe-delegatecall"
        assert metadata.source_tool == "securify2"
        assert metadata.severity == Severity.HIGH
        assert metadata.swc_id == "SWC-112"
    
    @pytest.mark.asyncio
    async def test_detect_unsafe_delegatecall(self):
        """Test detecting unsafe delegatecall."""
        detector = UnsafeDelegatecallDetector()
        
        vulnerable_code = """
        contract Vulnerable {
            function execute(address target, bytes memory data) public {
                target.delegatecall(data);
            }
        }
        """
        
        findings = await detector.analyze(vulnerable_code, "test.sol")
        
        # Should detect unsafe delegatecall
        assert len(findings) >= 1
        assert any('delegatecall' in f.description.lower() for f in findings)


class TestUnprotectedSelfdestructDetector:
    """Test unprotected selfdestruct detector."""
    
    def test_detector_metadata(self):
        """Test detector has correct metadata."""
        detector = UnprotectedSelfdestructDetector()
        metadata = detector.metadata
        
        assert metadata.detector_id == "native-securify2-unprotected-selfdestruct"
        assert metadata.source_tool == "securify2"
        assert metadata.severity == Severity.CRITICAL
        assert metadata.swc_id == "SWC-106"
    
    @pytest.mark.asyncio
    async def test_detect_unprotected_selfdestruct(self):
        """Test detecting unprotected selfdestruct."""
        detector = UnprotectedSelfdestructDetector()
        
        vulnerable_code = """
        contract Vulnerable {
            function destroy(address payable recipient) public {
                selfdestruct(recipient);
            }
        }
        """
        
        findings = await detector.analyze(vulnerable_code, "test.sol")
        
        # Should detect unprotected selfdestruct
        assert len(findings) >= 1
        assert any('selfdestruct' in f.description.lower() for f in findings)
    
    @pytest.mark.asyncio
    async def test_no_detection_with_protection(self):
        """Test no detection when selfdestruct is protected."""
        detector = UnprotectedSelfdestructDetector()
        
        safe_code = """
        contract Safe {
            address public owner;
            
            modifier onlyOwner() {
                require(msg.sender == owner);
                _;
            }
            
            function destroy(address payable recipient) public onlyOwner {
                selfdestruct(recipient);
            }
        }
        """
        
        findings = await detector.analyze(safe_code, "test.sol")
        
        # Should not detect issues
        assert len(findings) == 0


class TestLockedEtherDetector:
    """Test locked ether detector."""
    
    def test_detector_metadata(self):
        """Test detector has correct metadata."""
        detector = LockedEtherDetector()
        metadata = detector.metadata
        
        assert metadata.detector_id == "native-securify2-locked-ether"
        assert metadata.source_tool == "securify2"
        assert metadata.severity == Severity.MEDIUM
        assert metadata.swc_id == "SWC-132"
    
    @pytest.mark.asyncio
    async def test_detect_locked_ether(self):
        """Test detecting locked ether."""
        detector = LockedEtherDetector()
        
        vulnerable_code = """
        contract Vulnerable {
            function deposit() public payable {
                // Can receive but not withdraw
            }
        }
        """
        
        findings = await detector.analyze(vulnerable_code, "test.sol")
        
        # Should detect locked ether
        assert len(findings) >= 1
        assert any('locked' in f.description.lower() or 'ether' in f.description.lower() for f in findings)
    
    @pytest.mark.asyncio
    async def test_no_detection_with_withdrawal(self):
        """Test no detection when withdrawal mechanism exists."""
        detector = LockedEtherDetector()
        
        safe_code = """
        contract Safe {
            address public owner;
            
            function deposit() public payable {
                // Can receive ether
            }
            
            function withdraw() public {
                payable(owner).transfer(address(this).balance);
            }
        }
        """
        
        findings = await detector.analyze(safe_code, "test.sol")
        
        # Should not detect issues
        assert len(findings) == 0


class TestSecurify2Registry:
    """Test Securify2 detectors in registry."""
    
    def test_register_all_securify2_detectors(self):
        """Test all Securify2 detectors can be registered."""
        registry = DetectorRegistry()
        
        # Register all Securify2 detectors
        registry.register(IntegerOverflowDetector)
        registry.register(UninitializedStorageDetector)
        registry.register(MissingAccessControlDetector)
        registry.register(TimestampDependenceDetector)
        registry.register(UnsafeDelegatecallDetector)
        registry.register(UnprotectedSelfdestructDetector)
        registry.register(LockedEtherDetector)
        
        # Verify all are registered
        all_detectors = registry.get_all_detectors()
        assert len(all_detectors) == 7
        
        # Verify they're from securify2
        securify2_detectors = registry.get_detectors_by_tool('securify2')
        assert len(securify2_detectors) == 7
