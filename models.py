"""
Data Models for UI Testing Agent System
Shared data structures used across all agents
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TestStep:
    """Represents a single test step"""
    __test__ = False
    action: str
    target: str
    value: Optional[str] = None
    expected_result: Optional[str] = None
    step_number: int = 0


@dataclass
class TestPlan:
    """Represents a complete test plan"""
    __test__ = False
    objective: str
    steps: List[TestStep]
    success_criteria: List[str]


@dataclass
class ExecutionResult:
    """Results from executing a test step"""
    __test__ = False
    step_number: int
    action: str
    success: bool
    message: str
    screenshot_path: Optional[str] = None
    actual_result: Optional[str] = None
