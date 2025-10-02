"""Integration tests for Medusa detectors in the analysis pipeline."""

import pytest
import tempfile
import os
from pathlib import Path
from rich.console import Console

from babayaga.native.native_engine import NativeAnalysisEngine


class TestMedusaIntegration:
    """Integration tests for Medusa detectors with native analysis engine."""
    
    @pytest.mark.asyncio
    async def test_analyze_vulnerable_contract_with_medusa_detectors(self):
        """Test analyzing a vulnerable contract with all Medusa detectors."""
        
        # Create a temporary file with vulnerable contract
        vulnerable_contract = """
        pragma solidity ^0.8.0;
        
        contract VulnerableToken {
            uint256 public totalSupply;
            mapping(address => uint256) public balances;
            address public owner;
            
            constructor() {
                owner = msg.sender;
            }
            
            // Conservation violation: missing totalSupply update
            function mint(address to, uint256 amount) public {
                balances[to] += amount;
                // Missing: totalSupply += amount;
            }
            
            // Permission violation: missing access control
            function setOwner(address newOwner) public {
                owner = newOwner;
            }
            
            // Critical permission violation: unprotected selfdestruct
            function destroy() public {
                selfdestruct(payable(owner));
            }
            
            // Property function that may be violated
            function echidna_supply_matches_balances() public view returns (bool) {
                return totalSupply >= 0;
            }
            
            // Liveness: potential deadlock with multiple requires
            function withdraw() public {
                require(balances[msg.sender] > 0);
                require(owner != address(0));
                require(msg.sender == owner);
                payable(msg.sender).transfer(balances[msg.sender]);
            }
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sol', delete=False) as f:
            f.write(vulnerable_contract)
            temp_file = f.name
        
        try:
            # Create native analysis engine
            console = Console()
            engine = NativeAnalysisEngine(console)
            
            # Analyze the contract
            result = await engine.analyze_file(temp_file)
            
            # Verify results
            assert 'findings' in result
            findings = result['findings']
            
            # Should have multiple findings from different detectors
            assert len(findings) >= 3
            
            # Check that Medusa detectors found issues
            detector_ids = [f['detector_id'] for f in findings]
            
            # Check for conservation detector findings
            conservation_findings = [f for f in findings 
                                    if f['detector_id'] == 'native-medusa-conservation']
            assert len(conservation_findings) >= 1, "Should detect conservation violations"
            
            # Check for permission detector findings
            permission_findings = [f for f in findings 
                                  if f['detector_id'] == 'native-medusa-permissions']
            assert len(permission_findings) >= 1, "Should detect permission violations"
            
            # Verify finding structure
            for finding in findings:
                assert 'detector_id' in finding
                assert 'title' in finding
                assert 'description' in finding
                assert 'severity' in finding
                assert 'confidence' in finding
                assert 'file_path' in finding
            
        finally:
            # Clean up temp file
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_analyze_safe_contract_with_medusa_detectors(self):
        """Test that safe contracts don't trigger false positives."""
        
        safe_contract = """
        pragma solidity ^0.8.0;
        
        contract SafeToken {
            uint256 public totalSupply;
            mapping(address => uint256) public balances;
            address public owner;
            
            constructor() {
                owner = msg.sender;
            }
            
            modifier onlyOwner() {
                require(msg.sender == owner);
                _;
            }
            
            // Proper conservation: both balance and supply updated
            function mint(address to, uint256 amount) public onlyOwner {
                balances[to] += amount;
                totalSupply += amount;
            }
            
            // Proper access control
            function setOwner(address newOwner) public onlyOwner {
                require(newOwner != address(0));
                owner = newOwner;
            }
            
            // Property function that should hold
            function echidna_supply_is_sum_of_balances() public view returns (bool) {
                // Simplified check
                return totalSupply >= 0;
            }
            
            // Safe withdraw with proper checks
            function withdraw() public {
                uint256 balance = balances[msg.sender];
                require(balance > 0);
                
                balances[msg.sender] = 0;
                payable(msg.sender).transfer(balance);
            }
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sol', delete=False) as f:
            f.write(safe_contract)
            temp_file = f.name
        
        try:
            console = Console()
            engine = NativeAnalysisEngine(console)
            
            result = await engine.analyze_file(temp_file)
            
            findings = result['findings']
            
            # Should have minimal high-severity findings
            high_severity = [f for f in findings 
                           if f['severity'] in ['Critical', 'High']]
            
            # May have overflow warnings (valid for symbolic analysis)
            # but should not have supply mismatch or missing access control
            supply_mismatch = [f for f in findings 
                             if 'without' in f.get('description', '').lower() 
                             and 'balance' in f.get('description', '').lower()]
            assert len(supply_mismatch) == 0, "Should not detect false supply mismatches"
            
            missing_access_control = [f for f in findings
                                     if f.get('function_name') and 'setowner' in f.get('function_name', '').lower()
                                     and 'access control' in f.get('description', '').lower()]
            assert len(missing_access_control) == 0, "Should not flag properly protected functions"
            
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_analyze_project_with_medusa_detectors(self):
        """Test analyzing a project directory with multiple contracts."""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple contract files
            contract1 = """
            pragma solidity ^0.8.0;
            contract Token {
                uint256 public totalSupply;
                function mint(uint256 amount) public {
                    totalSupply += amount;
                }
            }
            """
            
            contract2 = """
            pragma solidity ^0.8.0;
            contract Vault {
                address public owner;
                function setOwner(address newOwner) public {
                    owner = newOwner;
                }
            }
            """
            
            # Write contracts to files
            Path(tmpdir).joinpath("Token.sol").write_text(contract1)
            Path(tmpdir).joinpath("Vault.sol").write_text(contract2)
            
            # Analyze project
            console = Console()
            engine = NativeAnalysisEngine(console)
            
            result = await engine.analyze_project(tmpdir)
            
            # Verify results
            assert 'files_analyzed' in result
            assert result['files_analyzed'] == 2
            
            assert 'findings' in result
            findings = result['findings']
            
            # Should have findings from both files
            files_with_findings = set(f['file_path'] for f in findings)
            assert len(files_with_findings) >= 1
            
            # Verify Medusa detectors ran
            medusa_findings = [f for f in findings 
                             if 'medusa' in f['detector_id']]
            assert len(medusa_findings) >= 1, "Medusa detectors should find issues"
    
    @pytest.mark.asyncio
    async def test_detector_metadata_available(self):
        """Test that Medusa detector metadata is available."""
        console = Console()
        engine = NativeAnalysisEngine(console)
        
        # Get detector info
        detector_info = engine._get_detector_info()
        
        assert 'version_info' in detector_info
        version_info = detector_info['version_info']
        
        # Check that Medusa detectors are registered
        # version_info maps detector_id -> info, not tool -> detectors
        medusa_detector_ids = [did for did in version_info.keys() if 'medusa' in did]
        
        # Should have 4 Medusa detectors
        assert len(medusa_detector_ids) >= 4
        
        # Verify specific detector IDs
        assert 'native-medusa-conservation' in medusa_detector_ids
        assert 'native-medusa-permissions' in medusa_detector_ids
        assert 'native-medusa-liveness' in medusa_detector_ids
        assert 'native-medusa-properties' in medusa_detector_ids
        
        # Verify they're all from medusa source tool
        for detector_id in medusa_detector_ids:
            assert version_info[detector_id]['source_tool'] == 'medusa'
