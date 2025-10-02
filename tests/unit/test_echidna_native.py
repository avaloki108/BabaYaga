"""Unit tests for the native Echidna fuzzer implementation."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from rich.console import Console

from babayaga.modules.echidna_test import (
    EchidnaFuzzer,
    FuzzingConfig,
    ContractAnalyzer,
    InputGenerator,
    PropertyChecker,
    PropertyStatus,
    Transaction,
    PropertyTest,
)


class TestContractAnalyzer:
    """Test cases for ContractAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a ContractAnalyzer instance."""
        return ContractAnalyzer()
    
    def test_extract_properties_with_echidna_prefix(self, analyzer):
        """Test extracting properties with echidna_ prefix."""
        contract_code = """
        contract Test {
            function echidna_balance_check() public view returns (bool) {
                return true;
            }
            
            function echidna_owner_check() public view returns (bool) {
                return true;
            }
        }
        """
        
        properties, _ = analyzer.analyze_contract(contract_code)
        
        assert len(properties) >= 2
        assert 'echidna_balance_check' in properties
        assert 'echidna_owner_check' in properties
    
    def test_extract_properties_with_invariant_prefix(self, analyzer):
        """Test extracting properties with invariant_ prefix."""
        contract_code = """
        contract Test {
            function invariant_total_supply() public view returns (bool) {
                return true;
            }
        }
        """
        
        properties, _ = analyzer.analyze_contract(contract_code)
        
        assert 'invariant_total_supply' in properties
    
    def test_generate_default_properties_for_balance(self, analyzer):
        """Test generating default properties for balance patterns."""
        contract_code = """
        contract Token {
            mapping(address => uint256) public balanceOf;
            
            function transfer(address to, uint256 amount) public {
                balanceOf[msg.sender] -= amount;
                balanceOf[to] += amount;
            }
        }
        """
        
        properties, _ = analyzer.analyze_contract(contract_code)
        
        # Should generate default properties
        assert len(properties) > 0
        assert any('balance' in p.lower() for p in properties)
    
    def test_extract_functions(self, analyzer):
        """Test extracting callable functions."""
        contract_code = """
        contract Test {
            function transfer(address to, uint256 amount) public {
            }
            
            function approve(address spender, uint256 amount) external {
            }
            
            function echidna_check() public view returns (bool) {
                return true;
            }
        }
        """
        
        _, functions = analyzer.analyze_contract(contract_code)
        
        assert len(functions) >= 2
        
        # Check that property functions are excluded
        func_names = [f['name'] for f in functions]
        assert 'transfer' in func_names
        assert 'approve' in func_names
        assert 'echidna_check' not in func_names
    
    def test_parse_parameters(self, analyzer):
        """Test parameter parsing."""
        params = analyzer._parse_parameters('address to, uint256 amount')
        
        assert len(params) == 2
        assert params[0]['type'] == 'address'
        assert params[0]['name'] == 'to'
        assert params[1]['type'] == 'uint256'
        assert params[1]['name'] == 'amount'
    
    def test_parse_empty_parameters(self, analyzer):
        """Test parsing empty parameters."""
        params = analyzer._parse_parameters('')
        
        assert len(params) == 0


class TestInputGenerator:
    """Test cases for InputGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create an InputGenerator instance with fixed seed."""
        return InputGenerator(seed=42)
    
    def test_generate_address(self, generator):
        """Test address generation."""
        addresses = ['0xaaa', '0xbbb', '0xccc']
        address = generator.generate_address(addresses)
        
        assert address in addresses
    
    def test_generate_uint_value(self, generator):
        """Test uint value generation."""
        value = generator.generate_value('uint256')
        
        assert isinstance(value, int)
        assert value >= 0
    
    def test_generate_int_value(self, generator):
        """Test int value generation."""
        value = generator.generate_value('int256')
        
        assert isinstance(value, int)
    
    def test_generate_address_value(self, generator):
        """Test address value generation."""
        value = generator.generate_value('address')
        
        assert isinstance(value, str)
        assert value.startswith('0x')
    
    def test_generate_bool_value(self, generator):
        """Test bool value generation."""
        value = generator.generate_value('bool')
        
        assert isinstance(value, bool)
    
    def test_generate_bytes_value(self, generator):
        """Test bytes value generation."""
        value = generator.generate_value('bytes32')
        
        assert isinstance(value, str)
        assert value.startswith('0x')
    
    def test_generate_string_value(self, generator):
        """Test string value generation."""
        value = generator.generate_value('string')
        
        assert isinstance(value, str)
    
    def test_generate_transaction(self, generator):
        """Test transaction generation."""
        functions = [
            {
                'name': 'transfer',
                'parameters': [
                    {'type': 'address', 'name': 'to'},
                    {'type': 'uint256', 'name': 'amount'}
                ],
                'visibility': 'public'
            }
        ]
        
        sender_addresses = ['0x123', '0x456']
        
        tx = generator.generate_transaction(functions, sender_addresses)
        
        assert tx.sender in sender_addresses
        assert tx.function == 'transfer'
        assert len(tx.arguments) == 2
    
    def test_generate_transaction_no_functions(self, generator):
        """Test transaction generation with no functions."""
        sender_addresses = ['0x123']
        
        tx = generator.generate_transaction([], sender_addresses)
        
        assert tx.function == 'fallback'
        assert len(tx.arguments) == 0


class TestPropertyChecker:
    """Test cases for PropertyChecker class."""
    
    @pytest.fixture
    def checker(self):
        """Create a PropertyChecker instance."""
        return PropertyChecker()
    
    def test_check_property_basic(self, checker):
        """Test basic property checking."""
        transactions = [
            Transaction(
                sender='0x123',
                function='transfer',
                arguments=['0x456', 100],
                value=0,
                gas_used=21000
            )
        ]
        
        contract_code = "contract Test {}"
        
        status, counterexample = checker.check_property(
            'echidna_test',
            transactions,
            contract_code
        )
        
        assert status in [PropertyStatus.PASSED, PropertyStatus.FAILED]
    
    def test_update_coverage(self, checker):
        """Test coverage tracking."""
        transactions = [
            Transaction(
                sender='0x123',
                function='transfer',
                arguments=[],
                value=0,
                gas_used=21000
            ),
            Transaction(
                sender='0x456',
                function='approve',
                arguments=[],
                value=0,
                gas_used=21000
            )
        ]
        
        checker.update_coverage("contract Test {}", transactions)
        
        assert 'transfer' in checker.coverage
        assert 'approve' in checker.coverage


class TestEchidnaFuzzer:
    """Test cases for EchidnaFuzzer class."""
    
    @pytest.fixture
    def console(self):
        """Create a mock console."""
        return Mock(spec=Console)
    
    @pytest.fixture
    def fuzzer(self, console):
        """Create an EchidnaFuzzer instance."""
        config = FuzzingConfig(
            test_limit=100,
            timeout=5,
            shrink_limit=10,
            sequence_length=5
        )
        return EchidnaFuzzer(console, config)
    
    def test_fuzzer_initialization(self, console):
        """Test fuzzer initialization."""
        fuzzer = EchidnaFuzzer(console)
        
        assert fuzzer.console == console
        assert fuzzer.config is not None
        assert fuzzer.analyzer is not None
        assert fuzzer.generator is not None
        assert fuzzer.checker is not None
    
    def test_fuzz_contract_with_properties(self, fuzzer):
        """Test fuzzing a contract with properties."""
        # Create a temporary contract file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sol', delete=False) as f:
            f.write("""
            contract Token {
                mapping(address => uint256) public balanceOf;
                
                function transfer(address to, uint256 amount) public {
                    balanceOf[msg.sender] -= amount;
                    balanceOf[to] += amount;
                }
                
                function echidna_balance_check() public view returns (bool) {
                    return true;
                }
            }
            """)
            contract_path = f.name
        
        try:
            result = fuzzer.fuzz_contract(contract_path)
            
            assert result is not None
            assert isinstance(result.properties, list)
            assert result.execution_time >= 0
            assert result.total_executions >= 0
            assert 'percentage' in result.coverage
        finally:
            Path(contract_path).unlink()
    
    def test_fuzz_contract_no_file(self, fuzzer):
        """Test fuzzing with non-existent file."""
        result = fuzzer.fuzz_contract('/nonexistent/contract.sol')
        
        assert result.total_executions == 0
        # Should have an error property
        assert len(result.properties) >= 1
        if len(result.properties) > 0:
            assert result.properties[0].status == PropertyStatus.ERROR
    
    def test_fuzz_contract_with_config_overrides(self, fuzzer):
        """Test fuzzing with configuration overrides."""
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
            config_overrides = {
                'testLimit': 50,
                'timeout': 2
            }
            
            result = fuzzer.fuzz_contract(contract_path, config_overrides)
            
            assert result is not None
            assert fuzzer.config.test_limit == 50
            assert fuzzer.config.timeout == 2
        finally:
            Path(contract_path).unlink()
    
    def test_shrink_counterexample(self, fuzzer):
        """Test shrinking a counterexample."""
        transactions = [
            Transaction('0x123', 'func1', [], 0, 21000),
            Transaction('0x456', 'func2', [], 0, 21000),
            Transaction('0x789', 'func3', [], 0, 21000)
        ]
        
        # Shrink should return a smaller or equal sequence
        result = fuzzer._shrink_counterexample(
            'echidna_test',
            transactions,
            'contract Test {}'
        )
        
        assert len(result) <= len(transactions)
    
    def test_calculate_coverage(self, fuzzer):
        """Test coverage calculation."""
        functions = [
            {'name': 'func1', 'parameters': [], 'visibility': 'public'},
            {'name': 'func2', 'parameters': [], 'visibility': 'public'}
        ]
        
        # Add some coverage
        fuzzer.checker.coverage['func1'] = {1, 2, 3}
        
        coverage = fuzzer._calculate_coverage(functions)
        
        assert 'percentage' in coverage
        assert coverage['percentage'] >= 0
        assert coverage['percentage'] <= 100
    
    def test_calculate_gas_statistics(self, fuzzer):
        """Test gas statistics calculation."""
        properties = [
            PropertyTest(
                name='prop1',
                description='test',
                status=PropertyStatus.PASSED,
                gas_used=50000,
                executions=10
            ),
            PropertyTest(
                name='prop2',
                description='test',
                status=PropertyStatus.PASSED,
                gas_used=100000,
                executions=20
            )
        ]
        
        stats = fuzzer._calculate_gas_statistics(properties)
        
        assert 'min' in stats
        assert 'max' in stats
        assert 'avg' in stats
        assert stats['min'] == 50000
        assert stats['max'] == 100000
    
    def test_empty_result(self, fuzzer):
        """Test empty result generation."""
        result = fuzzer._empty_result()
        
        assert len(result.properties) == 0
        assert result.coverage['percentage'] == 0.0
        assert result.total_executions == 0


class TestFuzzingConfig:
    """Test cases for FuzzingConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = FuzzingConfig()
        
        assert config.test_limit == 50000
        assert config.timeout == 300
        assert config.shrink_limit == 5000
        assert config.sequence_length == 100
        assert config.corpus_dir == 'corpus'
        assert config.coverage_enabled is True
        assert len(config.sender_addresses) > 0
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = FuzzingConfig(
            test_limit=1000,
            timeout=60,
            sender_addresses=['0xabc']
        )
        
        assert config.test_limit == 1000
        assert config.timeout == 60
        assert config.sender_addresses == ['0xabc']


class TestTransaction:
    """Test cases for Transaction dataclass."""
    
    def test_transaction_creation(self):
        """Test transaction creation."""
        tx = Transaction(
            sender='0x123',
            function='transfer',
            arguments=['0x456', 100],
            value=10,
            gas_used=21000
        )
        
        assert tx.sender == '0x123'
        assert tx.function == 'transfer'
        assert len(tx.arguments) == 2
        assert tx.value == 10
        assert tx.gas_used == 21000
    
    def test_transaction_to_dict(self):
        """Test transaction serialization."""
        tx = Transaction(
            sender='0x123',
            function='test',
            arguments=[1, 2, 3]
        )
        
        tx_dict = tx.to_dict()
        
        assert tx_dict['sender'] == '0x123'
        assert tx_dict['function'] == 'test'
        assert tx_dict['arguments'] == [1, 2, 3]


class TestPropertyTest:
    """Test cases for PropertyTest dataclass."""
    
    def test_property_test_creation(self):
        """Test property test creation."""
        prop = PropertyTest(
            name='echidna_test',
            description='Test property',
            status=PropertyStatus.PASSED
        )
        
        assert prop.name == 'echidna_test'
        assert prop.description == 'Test property'
        assert prop.status == PropertyStatus.PASSED
    
    def test_property_test_to_dict(self):
        """Test property test serialization."""
        tx = Transaction('0x123', 'func', [])
        prop = PropertyTest(
            name='test',
            description='desc',
            status=PropertyStatus.FAILED,
            counterexample=[tx]
        )
        
        prop_dict = prop.to_dict()
        
        assert prop_dict['name'] == 'test'
        assert prop_dict['status'] == 'failed'
        assert len(prop_dict['counterexample']) == 1
