from abc import ABC, abstractmethod
from typing import Any, Dict
from rich.console import Console
from pathlib import Path

# We'll need to import this to pass it in the context
from babayaga.project.detector import ProjectType

class AgentContext:
    """
    A data class to hold the shared context for an agent's run.
    This allows us to pass around a consistent set of data to all agents,
    making it easy to access run-specific information.
    """
    def __init__(self,
                 run_id: str,
                 target_dir: Path,
                 artifacts_dir: Path,
                 project_type: ProjectType,
                 config: Dict[str, Any]):
        self.run_id = run_id
        self.target_dir = target_dir
        self.artifacts_dir = artifacts_dir
        self.project_type = project_type
        self.config = config

class BaseAgent(ABC):
    """
    Abstract base class for all agents in the BabaYaga system.
    It defines the common interface and properties that all agents share.
    """
    def __init__(self, console: Console):
        self.console = console
        self.name = self.__class__.__name__

    @abstractmethod
    async def run(self, context: AgentContext, **kwargs) -> Any:
        """
        The main entry point for an agent's execution. This must be implemented
        by all concrete agent classes.

        Args:
            context: The shared context for the current audit run.
            **kwargs: Agent-specific arguments, allowing for flexibility.

        Returns:
            The results of the agent's analysis. The format can vary by agent.
        """
        self.console.print(f"[{self.get_color()}]▶️  Running {self.name}...[/{self.get_color()}]")
        pass

    def get_color(self) -> str:
        """Returns a color for console output based on agent type for better readability."""
        return "white"

class ReconAgent(BaseAgent):
    """
    Base class for agents in Phase 1: Reconnaissance.
    These agents are responsible for gathering information about the target,
    such as contract architecture, dependencies, and entry points.
    """
    def get_color(self) -> str:
        return "cyan"

class HunterAgent(BaseAgent):
    """
    Base class for agents in Phase 2: Vulnerability Hunting.
    These agents actively search for specific vulnerabilities using the
    data gathered during the reconnaissance phase.
    """
    def get_color(self) -> str:
        return "yellow"

class AdversaryAgent(BaseAgent):
    """
    Base class for agents in Phase 3: Adversarial Validation.
    These agents take the findings from the Hunter phase and attempt to
    disprove them, reducing false positives and confirming exploitability.
    """
    def get_color(self) -> str:
        return "magenta"

class ValidatorAgent(BaseAgent):
    """
    Base class for agents in Phase 4: Validation & Scoring.
    These agents perform final validation on confirmed findings and assign
    a score based on impact, exploitability, and novelty.
    """
    def get_color(self) -> str:
        return "blue"