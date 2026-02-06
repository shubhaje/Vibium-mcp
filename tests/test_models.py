import sys
import os

# Add parent directory to path so we can import models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import TestStep, TestPlan


def test_teststep_and_testplan_dataclasses():
    step = TestStep(action='navigate', target='https://example.com', value='', expected_result='', step_number=1)
    assert step.action == 'navigate'
    assert step.target.startswith('https://')

    plan = TestPlan(objective='Demo', steps=[step], success_criteria=['loads'])
    assert plan.objective == 'Demo'
    assert len(plan.steps) == 1
