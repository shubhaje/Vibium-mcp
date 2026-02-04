from models import TestStep, TestPlan


def test_teststep_and_testplan_dataclasses():
    step = TestStep(action='navigate', target='https://example.com', value='', expected_result='', step_number=1)
    assert step.action == 'navigate'
    assert step.target.startswith('https://')

    plan = TestPlan(objective='Demo', steps=[step], success_criteria=['loads'])
    assert plan.objective == 'Demo'
    assert len(plan.steps) == 1
