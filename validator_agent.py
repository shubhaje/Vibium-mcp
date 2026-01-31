"""
Validator Agent
Responsible for validating test execution results
"""

import json
import re
from typing import List, Dict, Any
from models import TestPlan, ExecutionResult
from ollama_client import OllamaClient


class ValidatorAgent:
    """Agent responsible for validating test execution"""
    
    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client
        self.system_prompt = """You are an expert QA validator. Your job is to analyze test execution 
        results and determine if the test passed or failed.
        
        Return your analysis in JSON format with NO trailing commas:
        {
            "overall_status": "PASS",
            "passed_steps": 5,
            "failed_steps": 0,
            "issues": [],
            "recommendations": [],
            "summary": "Brief summary"
        }
        
        Analyze the results carefully and provide actionable insights."""
    
    def validate(self, test_plan: TestPlan, results: List[ExecutionResult]) -> Dict[str, Any]:
        """Validate test execution results"""
        
        # Prepare results summary for LLM
        results_summary = "\n".join([
            f"Step {r.step_number} ({r.action}): {'SUCCESS' if r.success else 'FAILED'} - {r.message}"
            for r in results
        ])
        
        prompt = f"""Analyze this test execution:

Test Objective: {test_plan.objective}

Success Criteria:
{chr(10).join(f"- {c}" for c in test_plan.success_criteria)}

Execution Results:
{results_summary}

Provide JSON with NO trailing commas:"""

        response = self.llm.generate(prompt, self.system_prompt, temperature=0.2)
        
        try:
            validation = self._parse_validation_response(response)
            return validation
        except json.JSONDecodeError as e:
            print(f"[WARNING] Failed to parse validator response: {e}")
            # Fallback validation based on simple analysis
            return self._create_fallback_validation(results)
    
    def _parse_validation_response(self, response: str) -> Dict[str, Any]:
        """Parse validation response from LLM"""
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = response[json_start:json_end]
            # Fix trailing commas
            json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
            return json.loads(json_str)
        else:
            return json.loads(response)
    
    def _create_fallback_validation(self, results: List[ExecutionResult]) -> Dict[str, Any]:
        """Create fallback validation when LLM parsing fails"""
        passed = sum(1 for r in results if r.success)
        failed = len(results) - passed
        
        return {
            "overall_status": "PASS" if failed == 0 else "FAIL",
            "passed_steps": passed,
            "failed_steps": failed,
            "issues": [r.message for r in results if not r.success],
            "recommendations": ["Review failed steps"] if failed > 0 else [],
            "summary": f"{passed}/{len(results)} steps passed"
        }
    
    def print_validation_report(self, validation: Dict[str, Any]):
        """Print a formatted validation report"""
        print(f"\n{'='*60}")
        print("VALIDATION REPORT")
        print(f"{'='*60}")
        
        print(f"\nOverall Status: {validation['overall_status']}")
        print(f"Passed Steps: {validation['passed_steps']}")
        print(f"Failed Steps: {validation['failed_steps']}")
        
        if validation.get('issues'):
            print("\nIssues Found:")
            for issue in validation['issues']:
                print(f"  ❌ {issue}")
        
        if validation.get('recommendations'):
            print("\nRecommendations:")
            for rec in validation['recommendations']:
                print(f"  💡 {rec}")
        
        if validation.get('summary'):
            print(f"\nSummary: {validation['summary']}")
        
        print(f"{'='*60}\n")
