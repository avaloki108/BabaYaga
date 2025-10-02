"""Unit tests for native Mythril symbolic execution detectors."""

import pytest
from unittest.mock import Mock

from babayaga.native.base_detector import (
    BaseDetector, DetectorMetadata, DetectorFinding,
    Severity, DetectorCategory
)
from babayaga.native.mythril_detectors.integer_overflow import IntegerOverflowDetector
from babayaga.native.mythril_detectors.reentrancy import ReentrancySymbolicDetector
from babayaga.native.mythril_detectors.unchecked_call import UncheckedCallSymbolicDetector
from babayaga.native.mythril_detectors.unprotected_ether import UnprotectedEtherDetector
from babayaga.native.mythril_detectors.unprotected_selfdestruct import UnprotectedSelfdestructDetector
from babayaga.native.mythril_detectors.tx_origin import TxOriginSymbolicDetector
from babayaga.native.mythril_detectors.symbolic_engine import SimplifiedSymbolicEngine


class TestSymbolicEngine:
    """Test symbolic execution engine."""
    
    def test_engine_initialization(self):
        """Test symbolic engine can be created."""
        engine = SimplifiedSymbolicEngine()
        assert engine is not None
    
    def test_analyze_function_basic(self):
        """Test basic function analysis."""
        engine = SimplifiedSymbolicEngine()
        
        func_code = """
        function test() public {
            uint256 x = 10;
            x = x + 5;
        }
        """
        
        states = engine.analyze_function(func_code, "test")
        assert len(states) > 0
    
    def test_detect_external_call(self):
        """Test detection of external calls."""
        engine = SimplifiedSymbolicEngine()
        
        func_code = """
        function withdraw() public {
            msg.sender.call{value: amount}("");
        }
        """
        
        states = engine.analyze_function(func_code, "withdraw")
        assert any(len(state.calls_made) > 0 for state in states)


class TestIntegerOverflowDetector:
    """Test integer overflow detector."""
    
    @pytest.mark.asyncio
    async def test_detector_metadata(self):
        """Test integer overflow detector metadata."""
        detector = IntegerOverflowDetector()
        metadata = detector.get_metadata()
        
        assert metadata.detector_id == "native-mythril-integer-overflow"
        assert metadata.source_tool == "mythril"
        assert metadata.severity == Severity.HIGH
        assert metadata.swc_id == "SWC-101"
    
    @pytest.mark.asyncio
    async def test_detect_overflow_old_solidity(self):
        """Test detecting overflow in old Solidity version."""
        detector = IntegerOverflowDetector()
        
        vulnerable_code = """
        pragma solidity ^0.7.0;
        
        contract Vulnerable {
            uint256 public total;
            
            function add(uint256 amount) public {
                total = total + amount;
            }
        }
        """
        
        findings = await detector.analyze(vulnerable_code, "test.sol")
        
        # Should detect potential overflow
        assert len(findings) >= 1
        assert "overflow" in findings[0].title.lower()
    
    @pytest.mark.asyncio
    async def test_safe_solidity_version(self):
        """Test that Solidity 0.8+ is considered safe."""
        detector = IntegerOverflowDetector()
        
        safe_code = """
        pragma solidity ^0.8.0;
        
        contract Safe {
            uint256 public total;
            
            function add(uint256 amount) public {
                total = total + amount;
            }
        }
        """
        
        findings = await detector.analyze(safe_code, "test.sol")
        
        # Should not detect issues in 0.8+
        assert len(findings) == 0
    
    @pytest.mark.asyncio
    async def test_safemath_usage(self):
        """Test that SafeMath usage is recognized."""
        detector = IntegerOverflowDetector()
        
        safe_code = """
        pragma solidity ^0.7.0;
        
        import "@openzeppelin/contracts/math/SafeMath.sol";
        
        contract Safe {
            using SafeMath for uint256;
            uint256 public total;
            
            function add(uint256 amount) public {
                total = total.add(amount);
            }
        }
        """
        
        findings = await detector.analyze(safe_code, "test.sol")
        
        # Should not detect issues when SafeMath is used
        assert len(findings) == 0


class TestReentrancySymbolicDetector:
    """Test reentrancy detector with symbolic execution."""
    
    @pytest.mark.asyncio
    async def test_detector_metadata(self):
        """Test reentrancy detector metadata."""
        detector = ReentrancySymbolicDetector()
        metadata = detector.get_metadata()
        
        assert metadata.detector_id == "native-mythril-reentrancy"
        assert metadata.source_tool == "mythril"
        assert metadata.swc_id == "SWC-107"
    
    @pytest.mark.asyncio
    async def test_detect_reentrancy(self):
        """Test detecting reentrancy vulnerability."""
        detector = ReentrancySymbolicDetector()
        
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
        
        assert len(findings) >= 1
        assert "reentrancy" in findings[0].title.lower()
    
    @pytest.mark.asyncio
    async def test_safe_pattern(self):
        """Test that checks-effects-interactions pattern is safe."""
        detector = ReentrancySymbolicDetector()
        
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
        
        # Should not detect issues with proper pattern
        assert len(findings) == 0
    
    @pytest.mark.asyncio
    async def test_reentrancy_guard(self):
        """Test that reentrancy guards are recognized."""
        detector = ReentrancySymbolicDetector()
        
        safe_code = """
        contract Safe {
            mapping(address => uint256) public balances;
            
            function withdraw() public nonReentrant {
                uint256 amount = balances[msg.sender];
                msg.sender.call{value: amount}("");
                balances[msg.sender] = 0;
            }
        }
        """
        
        findings = await detector.analyze(safe_code, "test.sol")
        
        # Should not detect issues with reentrancy guard
        assert len(findings) == 0


class TestUncheckedCallSymbolicDetector:
    """Test unchecked call detector."""
    
    @pytest.mark.asyncio
    async def test_detector_metadata(self):
        """Test unchecked call detector metadata."""
        detector = UncheckedCallSymbolicDetector()
        metadata = detector.get_metadata()
        
        assert metadata.detector_id == "native-mythril-unchecked-call"
        assert metadata.source_tool == "mythril"
        assert metadata.swc_id == "SWC-104"
    
    @pytest.mark.asyncio
    async def test_detect_unchecked_call(self):
        """Test detecting unchecked external call."""
        detector = UncheckedCallSymbolicDetector()
        
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
    async def test_checked_call(self):
        """Test that checked calls are safe."""
        detector = UncheckedCallSymbolicDetector()
        
        safe_code = """
        contract Safe {
            function sendEther(address payable recipient) public {
                (bool success, ) = recipient.call{value: 1 ether}("");
                require(success, "Transfer failed");
            }
        }
        """
        
        findings = await detector.analyze(safe_code, "test.sol")
        
        # Should not detect issues when return value is checked
        assert len(findings) == 0


class TestUnprotectedEtherDetector:
    """Test unprotected ether withdrawal detector."""
    
    @pytest.mark.asyncio
    async def test_detector_metadata(self):
        """Test unprotected ether detector metadata."""
        detector = UnprotectedEtherDetector()
        metadata = detector.get_metadata()
        
        assert metadata.detector_id == "native-mythril-unprotected-ether"
        assert metadata.source_tool == "mythril"
        assert metadata.swc_id == "SWC-105"
    
    @pytest.mark.asyncio
    async def test_detect_unprotected_withdrawal(self):
        """Test detecting unprotected ether withdrawal."""
        detector = UnprotectedEtherDetector()
        
        vulnerable_code = """
        contract Vulnerable {
            function withdraw(address payable recipient, uint256 amount) public {
                recipient.call{value: amount}("");
            }
        }
        """
        
        findings = await detector.analyze(vulnerable_code, "test.sol")
        
        assert len(findings) >= 1
        assert "unprotected" in findings[0].title.lower()
    
    @pytest.mark.asyncio
    async def test_protected_withdrawal(self):
        """Test that access-controlled withdrawal is safe."""
        detector = UnprotectedEtherDetector()
        
        safe_code = """
        contract Safe {
            address owner;
            
            function withdraw(address payable recipient, uint256 amount) public {
                require(msg.sender == owner, "Not owner");
                recipient.call{value: amount}("");
            }
        }
        """
        
        findings = await detector.analyze(safe_code, "test.sol")
        
        # Should not detect issues with access control
        assert len(findings) == 0


class TestUnprotectedSelfdestructDetector:
    """Test unprotected selfdestruct detector."""
    
    @pytest.mark.asyncio
    async def test_detector_metadata(self):
        """Test unprotected selfdestruct detector metadata."""
        detector = UnprotectedSelfdestructDetector()
        metadata = detector.get_metadata()
        
        assert metadata.detector_id == "native-mythril-unprotected-selfdestruct"
        assert metadata.source_tool == "mythril"
        assert metadata.severity == Severity.CRITICAL
        assert metadata.swc_id == "SWC-106"
    
    @pytest.mark.asyncio
    async def test_detect_unprotected_selfdestruct(self):
        """Test detecting unprotected selfdestruct."""
        detector = UnprotectedSelfdestructDetector()
        
        vulnerable_code = """
        contract Vulnerable {
            function kill() public {
                selfdestruct(payable(msg.sender));
            }
        }
        """
        
        findings = await detector.analyze(vulnerable_code, "test.sol")
        
        assert len(findings) >= 1
        assert "selfdestruct" in findings[0].title.lower()
    
    @pytest.mark.asyncio
    async def test_protected_selfdestruct(self):
        """Test that access-controlled selfdestruct is safe."""
        detector = UnprotectedSelfdestructDetector()
        
        safe_code = """
        contract Safe {
            address owner;
            
            function kill() public {
                require(msg.sender == owner, "Not owner");
                selfdestruct(payable(msg.sender));
            }
        }
        """
        
        findings = await detector.analyze(safe_code, "test.sol")
        
        # Should not detect issues with access control
        assert len(findings) == 0


class TestTxOriginSymbolicDetector:
    """Test tx.origin detector."""
    
    @pytest.mark.asyncio
    async def test_detector_metadata(self):
        """Test tx.origin detector metadata."""
        detector = TxOriginSymbolicDetector()
        metadata = detector.get_metadata()
        
        assert metadata.detector_id == "native-mythril-tx-origin"
        assert metadata.source_tool == "mythril"
        assert metadata.swc_id == "SWC-115"
    
    @pytest.mark.asyncio
    async def test_detect_tx_origin_usage(self):
        """Test detecting tx.origin for authentication."""
        detector = TxOriginSymbolicDetector()
        
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
    async def test_msg_sender_safe(self):
        """Test that msg.sender is safe."""
        detector = TxOriginSymbolicDetector()
        
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
        
        # Should not detect issues with msg.sender
        assert len(findings) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
