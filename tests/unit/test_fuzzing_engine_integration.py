"""Integration tests for FuzzingEngine with native Echidna."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from rich.console import Console

from babayaga.engines.fuzzing_engine import FuzzingEngine


class TestFuzzingEngineIntegration:
    """Test cases for FuzzingEngine with native Echidna integration."""
    
    @pytest.fixture
    def console(self):
        """Create a mock console."""
        return Mock(spec=Console)
    
    @pytest.fixture
    def fuzzing_engine(self, console):
        """Create a FuzzingEngine instance."""
        return FuzzingEngine(console)
    
    def test_fuzzing_engine_initialization(self, console):
        """Test FuzzingEngine initialization with native Echidna."""
        engine = FuzzingEngine(console)
        
        assert engine.console == console
        assert engine.native_echidna is not None
        assert engine.tools_available['echidna'] is True
        assert hasattr(engine, 'results')
        assert hasattr(engine, 'generated_tests')
    
    def test_echidna_always_available(self, fuzzing_engine):
        """Test that native Echidna is always available."""
        assert fuzzing_engine._check_echidna() is True
        assert fuzzing_engine.tools_available['echidna'] is True
    
    def test_create_echidna_config(self, fuzzing_engine):
        """Test Echidna configuration creation."""
        config = {
            'echidna_test_limit': 1000,
            'echidna_timeout': 60,
            'echidna_shrink_limit': 100,
            'echidna_sequence_length': 20
        }
        
        echidna_config = fuzzing_engine._create_echidna_config(config)
        
        assert echidna_config['testLimit'] == 1000
        assert echidna_config['timeout'] == 60
        assert echidna_config['shrinkLimit'] == 100
        assert echidna_config['seqLen'] == 20
        assert 'sender' in echidna_config
        assert 'contractAddr' in echidna_config
    
    def test_run_echidna_fuzzing_with_mock_contract(self, fuzzing_engine):
        """Test running native Echidna fuzzing."""
        # Create a temporary contract file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sol', delete=False) as f:
            f.write("""
            pragma solidity ^0.8.0;
            
            contract SimpleToken {
                mapping(address => uint256) public balances;
                
                function transfer(address to, uint256 amount) public {
                    balances[msg.sender] -= amount;
                    balances[to] += amount;
                }
                
                function echidna_balance_check() public view returns (bool) {
                    return balances[msg.sender] >= 0;
                }
            }
            """)
            contract_path = f.name
        
        try:
            # Create mock progress and task_id
            from rich.progress import Progress
            from unittest.mock import MagicMock
            
            progress = MagicMock(spec=Progress)
            task_id = 1
            
            config = {
                'echidna_test_limit': 100,
                'echidna_timeout': 5
            }
            
            work_dir = Path(tempfile.mkdtemp())
            
            result = fuzzing_engine._run_echidna_fuzzing(
                contract_path,
                work_dir,
                config,
                progress,
                task_id
            )
            
            # Verify result structure
            assert result is not None
            assert result.tool == 'echidna'
            assert result.status in ['passed', 'failed', 'error']
            assert result.properties_tested >= 0
            assert result.execution_time >= 0
            
        finally:
            Path(contract_path).unlink()
    
    def test_convert_native_echidna_result(self, fuzzing_engine):
        """Test converting native Echidna result to FuzzingResult."""
        from babayaga.modules.echidna_test import (
            FuzzingResult as NativeResult,
            PropertyTest,
            PropertyStatus,
            Transaction
        )
        
        # Create a native result
        native_result = NativeResult(
            properties=[
                PropertyTest(
                    name='echidna_test1',
                    description='Test 1',
                    status=PropertyStatus.PASSED,
                    executions=100
                ),
                PropertyTest(
                    name='echidna_test2',
                    description='Test 2',
                    status=PropertyStatus.FAILED,
                    counterexample=[
                        Transaction('0x123', 'transfer', ['0x456', 100], 0, 21000)
                    ],
                    executions=50
                )
            ],
            coverage={'percentage': 75.0},
            execution_time=10.5,
            total_executions=150,
            corpus_size=1,
            gas_statistics={'min': 21000, 'max': 50000, 'avg': 35000}
        )
        
        result = fuzzing_engine._convert_native_echidna_result(native_result)
        
        assert result.tool == 'echidna'
        assert result.properties_tested == 2
        assert result.properties_failed == 1
        assert result.status == 'failed'
        assert result.coverage_percentage == 75.0
        assert result.execution_time == 10.5
        assert len(result.failing_sequences) == 1
        assert result.corpus_size == 1
    
    def test_native_echidna_no_external_dependency(self, fuzzing_engine):
        """Test that native Echidna doesn't require external binary."""
        # This test verifies that we don't call subprocess for echidna binary
        with patch('subprocess.run') as mock_run:
            # Create a simple contract
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sol', delete=False) as f:
                f.write("""
                contract Test {
                    function echidna_test() public view returns (bool) {
                        return true;
                    }
                }
                """)
                contract_path = f.name
            
            try:
                from rich.progress import Progress
                from unittest.mock import MagicMock
                
                progress = MagicMock(spec=Progress)
                task_id = 1
                config = {'echidna_timeout': 2, 'echidna_test_limit': 10}
                work_dir = Path(tempfile.mkdtemp())
                
                result = fuzzing_engine._run_echidna_fuzzing(
                    contract_path,
                    work_dir,
                    config,
                    progress,
                    task_id
                )
                
                # Verify that subprocess.run was NOT called with 'echidna' command
                echidna_calls = [
                    call for call in mock_run.call_args_list 
                    if call[0] and 'echidna' in str(call[0][0])
                ]
                assert len(echidna_calls) == 0, "Should not call external echidna binary"
                
            finally:
                Path(contract_path).unlink()
    
    @pytest.mark.asyncio
    async def test_comprehensive_fuzzing_with_native_echidna(self):
        """Test comprehensive fuzzing campaign with native Echidna."""
        # Use real Console for this integration test
        from rich.console import Console
        console = Console()
        fuzzing_engine = FuzzingEngine(console)
        
        # Create a test contract
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sol', delete=False) as f:
            f.write("""
            pragma solidity ^0.8.0;
            
            contract TestContract {
                uint256 public value;
                
                function setValue(uint256 _value) public {
                    value = _value;
                }
                
                function echidna_value_check() public view returns (bool) {
                    return value < 1000000;
                }
            }
            """)
            contract_path = f.name
        
        try:
            config = {
                'echidna_test_limit': 50,
                'echidna_timeout': 3
            }
            
            # Mock medusa and fuzz_utils as unavailable
            fuzzing_engine.tools_available['medusa'] = False
            fuzzing_engine.tools_available['fuzz_utils'] = False
            
            report = await fuzzing_engine.run_comprehensive_fuzzing(
                contract_path,
                config
            )
            
            assert report is not None
            assert 'summary' in report
            assert 'tool_results' in report
            
            # Check that echidna was executed
            echidna_results = [r for r in report['tool_results'] if r['tool'] == 'echidna']
            assert len(echidna_results) > 0
            
        finally:
            Path(contract_path).unlink()


class TestNativeEchidnaErrorHandling:
    """Test error handling in native Echidna integration."""
    
    @pytest.fixture
    def console(self):
        """Create a mock console."""
        return Mock(spec=Console)
    
    @pytest.fixture
    def fuzzing_engine(self, console):
        """Create a FuzzingEngine instance."""
        return FuzzingEngine(console)
    
    def test_run_echidna_with_invalid_file(self):
        """Test running Echidna with invalid file."""
        from rich.console import Console
        from rich.progress import Progress
        
        console = Console()
        fuzzing_engine = FuzzingEngine(console)
        
        # Create a real progress object
        with Progress(console=console) as progress:
            task_id = progress.add_task("Test", total=100)
            config = {}
            work_dir = Path(tempfile.mkdtemp())
            
            result = fuzzing_engine._run_echidna_fuzzing(
                '/nonexistent/file.sol',
                work_dir,
                config,
                progress,
                task_id
            )
            
            assert result.status == 'error'
            # Native implementation returns error status when file doesn't exist
            assert result.properties_tested >= 0
    
    def test_run_echidna_with_exception(self, fuzzing_engine):
        """Test handling exceptions during fuzzing."""
        from rich.progress import Progress
        from unittest.mock import MagicMock
        
        # Mock the native fuzzer to raise an exception
        with patch.object(fuzzing_engine.native_echidna, 'fuzz_contract') as mock_fuzz:
            mock_fuzz.side_effect = Exception("Test exception")
            
            progress = MagicMock(spec=Progress)
            task_id = 1
            config = {}
            work_dir = Path(tempfile.mkdtemp())
            
            # Create a dummy file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sol', delete=False) as f:
                f.write("contract Test {}")
                contract_path = f.name
            
            try:
                result = fuzzing_engine._run_echidna_fuzzing(
                    contract_path,
                    work_dir,
                    config,
                    progress,
                    task_id
                )
                
                assert result.status == 'error'
                assert 'Test exception' in result.error_message
                
            finally:
                Path(contract_path).unlink()
