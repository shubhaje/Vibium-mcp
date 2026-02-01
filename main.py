"""
Main Entry Point for UI Testing Agent System
Run this file to execute tests
"""

import asyncio
import os
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from orchestrator import VibiumUITestingOrchestrator


async def main():
    """Main function to run UI tests"""
    
    # Detect if running in CI environment
    is_ci = os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS')
    
    if is_ci:
        print("\n[INFO] Running in CI environment. Skipping UI tests (requires local Ollama).")
        print("[INFO] pytest tests should have already passed.")
        return
    
    # Example test prompts
    example_prompts = [
        "Test Google search: Navigate to https://rahulshettyacademy.com/AutomationPractice/, Select Radio 1 from Radio Button example, and Type to select country India from dropdown",
        "Click on OpenWindow button  from switch window exampe , verify  https://www.qaclickacademy.com/ window appres ",
        "Close the first tab from switch window example and verify the second tab with text 'QA Click Academy | Selenium,Jmeter,SoapUI,Appium,Database testing,QA Training Academy' is present",
        "In the Alerts example, click on 'Click me to see alert' button and accept the alert. Verify that the alert was accepted successfully.",
        "In the Mouse Hover example, hover over the 'Mouse Hover' button and click on the 'Top' option from the displayed menu. Verify that the action was successful."
    ]
    
    # Initialize orchestrator
    orchestrator = VibiumUITestingOrchestrator(
        ollama_model="llama3.2:3b",
        headless=False,  # Set to True for headless mode
        debug=True  # Set to False to hide debug output
    )
    
    # Check if Ollama is available
    if not orchestrator.check_ollama_availability():
        print("\n❌ ERROR: Ollama not available at localhost:11434")
        print("📝 UI tests require Ollama. Please start Ollama and try again.")
        print("💡 To run locally: ollama serve")
        return
    
    try:
        # Select which test to run (default: first one)
        user_prompt = example_prompts[0]
        
        print(f"\n🚀 Running test: {user_prompt}\n")
        
        # Run the test
        result = await orchestrator.run_test(user_prompt)
        
        # Print final result
        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)
        print(f"Final Status: {result['validation']['overall_status']}")
        print(f"Summary: {result['validation'].get('summary', 'No summary available')}")
        print("="*80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during test execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await orchestrator.cleanup()


def run_custom_test(prompt: str, model: str = "llama3.2:3b", headless: bool = False):
    """
    Helper function to run a custom test
    
    Args:
        prompt: Natural language test description
        model: Ollama model to use
        headless: Run browser in headless mode
    """
    async def _run():
        orchestrator = VibiumUITestingOrchestrator(
            ollama_model=model,
            headless=headless,
            debug=False
        )
        
        try:
            result = await orchestrator.run_test(prompt)
            return result
        finally:
            await orchestrator.cleanup()
    
    return asyncio.run(_run())


if __name__ == "__main__":
    asyncio.run(main())
