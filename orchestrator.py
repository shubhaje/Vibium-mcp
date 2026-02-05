"""
UI Testing Orchestrator
Coordinates Planner, Executor, and Validator agents
"""

from typing import Dict, Any
from models import TestPlan
from ollama_client import OllamaClient
from planner_agent import PlannerAgent
from executor_agent import VibiumExecutorAgent
from validator_agent import ValidatorAgent


class VibiumUITestingOrchestrator:
    """Main orchestrator for the multi-agent testing system with Vibium"""
    
    def __init__(self, ollama_model: str = "llama3.2:3b", headless: bool = False, debug: bool = False):
        """
        Initialize the orchestrator with all three agents
        
        Args:
            ollama_model: The Ollama model to use (e.g., "llama3.2:3b")
            headless: Whether to run browser in headless mode
            debug: Enable debug output
        """
        self.llm_client = OllamaClient(model=ollama_model)
        self.planner = PlannerAgent(self.llm_client)
        self.executor = VibiumExecutorAgent(self.llm_client, headless=headless)
        self.validator = ValidatorAgent(self.llm_client)
        self.debug = debug
    
    async def run_test(self, user_prompt: str) -> Dict[str, Any]:
        """
        Run complete test cycle: Plan -> Execute -> Validate
        
        Args:
            user_prompt: Natural language description of the test
            
        Returns:
            Dict containing test_plan, results, and validation
        """
        
        print("=" * 80)
        print("UI TESTING AGENT SYSTEM (Vibium Edition)")
        print("=" * 80)
        
        # Step 1: Planning
        print("\n[PLANNER AGENT] Creating test plan...")
        test_plan = self.planner.create_plan(user_prompt, debug=self.debug)
        
        self._print_test_plan(test_plan)
        
        # Step 2: Execution
        print("\n[EXECUTOR AGENT] Executing test plan with Vibium...")
        results = await self._execute_test_plan(test_plan)
        
        # Step 3: Validation
        print("\n[VALIDATOR AGENT] Validating results...")
        validation = self.validator.validate(test_plan, results)
        
        self._print_validation_summary(validation)
        
        print("\n" + "=" * 80)
        
        return {
            "test_plan": test_plan,
            "results": results,
            "validation": validation
        }
    
    async def _execute_test_plan(self, test_plan: TestPlan) -> list:
        """Execute all steps in the test plan"""
        results = []
        
        try:
            for step in test_plan.steps:
                print(f"\nExecuting Step {step.step_number}: {step.action} -> {step.target}")
                result = await self.executor.execute_step(step)
                results.append(result)
                
                status = "✓" if result.success else "✗"
                print(f"{status} {result.message}")
                
                # Stop on critical failures
                if not result.success and step.action in ["navigate"]:
                    print("⚠️  Critical step failed, stopping execution")
                    break
        finally:
            await self.executor.close_browser()
        
        return results
    
    def _print_test_plan(self, test_plan: TestPlan):
        """Print formatted test plan"""
        print(f"\n📋 Objective: {test_plan.objective}")
        print(f"📊 Total Steps: {len(test_plan.steps)}")
        
        for step in test_plan.steps:
            value_info = f" (value: {step.value})" if step.value else ""
            print(f"  {step.step_number}. {step.action} → {step.target}{value_info}")
    
    def _print_validation_summary(self, validation: Dict[str, Any]):
        """Print validation summary"""
        status_symbol = "✅" if validation['overall_status'] == "PASS" else "❌"
        print(f"\n{status_symbol} Overall Status: {validation['overall_status']}")
        print(f"📊 Passed: {validation['passed_steps']}/{validation['passed_steps'] + validation['failed_steps']}")
        
        if validation.get('issues'):
            print("\n⚠️  Issues Found:")
            for issue in validation['issues']:
                print(f"  • {issue}")
        
        if validation.get('recommendations'):
            print("\n💡 Recommendations:")
            for rec in validation['recommendations']:
                print(f"  • {rec}")
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.executor.close_browser()
    
    def check_ollama_availability(self) -> bool:
        """Check if Ollama is available"""
        return self.llm_client.check_availability()
