# UI Testing Agent System - Modular Structure

## 📁 Project Structure

```
ui-testing-agents/
├── models.py              # Data models (TestStep, TestPlan, ExecutionResult)
├── ollama_client.py       # Ollama LLM client
├── planner_agent.py       # Planner Agent (creates test plans)
├── executor_agent.py      # Executor Agent (runs tests with Vibium)
├── validator_agent.py     # Validator Agent (validates results)
├── orchestrator.py        # Orchestrator (coordinates all agents)
├── main.py                # Main entry point
└── requirements.txt       # Python dependencies
```

## 🎯 File Descriptions

### Core Components

#### `models.py`
- Contains all data structures
- `TestStep`: Single test step
- `TestPlan`: Complete test plan with steps
- `ExecutionResult`: Result of executing a step

#### `ollama_client.py`
- Handles communication with Ollama LLM
- Methods: `generate()`, `check_availability()`

#### `planner_agent.py`
- **PlannerAgent**: Creates test plans from natural language
- Takes user prompts and generates structured test plans
- Handles JSON parsing and cleaning
- Key method: `create_plan(user_prompt)`

#### `executor_agent.py`
- **VibiumExecutorAgent**: Executes test steps using Vibium
- Handles browser initialization and control
- Executes actions: navigate, click, type, verify, wait, scroll
- Key method: `execute_step(step)`

#### `validator_agent.py`
- **ValidatorAgent**: Validates test execution results
- Analyzes results and provides insights
- Generates recommendations
- Key method: `validate(test_plan, results)`

#### `orchestrator.py`
- **VibiumUITestingOrchestrator**: Coordinates all three agents
- Manages the complete test workflow
- Key method: `run_test(user_prompt)`

#### `main.py`
- Entry point for running tests
- Example test prompts
- Helper function for custom tests

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install requests vibium
playwright install chromium
```

### 2. Start Ollama

```bash
ollama pull llama3.2:3b
ollama serve
```

### 3. Run Tests

```bash
python main.py
```

## 💡 Usage Examples

### Basic Usage

```python
import asyncio
from orchestrator import VibiumUITestingOrchestrator

async def run_test():
    orchestrator = VibiumUITestingOrchestrator(
        ollama_model="llama3.2:3b",
        headless=False,
        debug=True
    )
    
    prompt = "Navigate to google.com and search for 'Python'"
    result = await orchestrator.run_test(prompt)
    await orchestrator.cleanup()

asyncio.run(run_test())
```

### Using Individual Agents

```python
from ollama_client import OllamaClient
from planner_agent import PlannerAgent

# Create a test plan
llm = OllamaClient(model="llama3.2:3b")
planner = PlannerAgent(llm)

plan = planner.create_plan("Test Google search", debug=True)
print(f"Objective: {plan.objective}")
print(f"Steps: {len(plan.steps)}")
```

### Custom Test with Helper Function

```python
from main import run_custom_test

result = run_custom_test(
    prompt="Test Wikipedia homepage",
    model="llama3.2:3b",
    headless=True
)

print(f"Status: {result['validation']['overall_status']}")
```

## 🔧 Customization

### Adding New Actions

Edit `executor_agent.py` and add new methods:

```python
async def _execute_your_action(self, step: TestStep) -> ExecutionResult:
    """Your custom action"""
    try:
        # Implementation here
        return ExecutionResult(
            step_number=step.step_number,
            action=step.action,
            success=True,
            message="Action completed"
        )
    except Exception as e:
        return ExecutionResult(
            step_number=step.step_number,
            action=step.action,
            success=False,
            message=f"Action failed: {e}"
        )
```

Then update `execute_step()`:

```python
async def execute_step(self, step: TestStep) -> ExecutionResult:
    # ... existing code ...
    elif step.action == "your_action":
        return await self._execute_your_action(step)
```

### Modifying Agent Behavior

Each agent is independent and can be modified separately:

- **Planner**: Edit `planner_agent.py` → `system_prompt`
- **Executor**: Edit `executor_agent.py` → action methods
- **Validator**: Edit `validator_agent.py` → `system_prompt`

## 📊 Data Flow

```
User Prompt
    ↓
PlannerAgent → TestPlan (with TestSteps)
    ↓
ExecutorAgent → List[ExecutionResult]
    ↓
ValidatorAgent → Validation Report
    ↓
Final Results
```

## 🎨 Benefits of Modular Structure

1. **Separation of Concerns**: Each agent has one responsibility
2. **Easy Testing**: Test agents independently
3. **Maintainability**: Changes isolated to specific files
4. **Reusability**: Use agents in different contexts
5. **Extensibility**: Add new agents easily

## 🧪 Testing Individual Components

### Test Planner Only

```python
from ollama_client import OllamaClient
from planner_agent import PlannerAgent

llm = OllamaClient()
planner = PlannerAgent(llm)

plan = planner.create_plan("Test login form")
for step in plan.steps:
    print(f"{step.step_number}. {step.action} -> {step.target}")
```

### Test Executor Only

```python
import asyncio
from ollama_client import OllamaClient
from executor_agent import VibiumExecutorAgent
from models import TestStep

async def test_executor():
    llm = OllamaClient()
    executor = VibiumExecutorAgent(llm, headless=False)
    
    step = TestStep(
        step_number=1,
        action="navigate",
        target="https://google.com",
        value=""
    )
    
    result = await executor.execute_step(step)
    print(f"Result: {result.success} - {result.message}")
    await executor.close_browser()

asyncio.run(test_executor())
```

### Test Validator Only

```python
from ollama_client import OllamaClient
from validator_agent import ValidatorAgent
from models import TestPlan, TestStep, ExecutionResult

llm = OllamaClient()
validator = ValidatorAgent(llm)

# Create mock data
plan = TestPlan(
    objective="Test search",
    steps=[TestStep(1, "navigate", "google.com")],
    success_criteria=["Page loads"]
)

results = [
    ExecutionResult(1, "navigate", True, "Success")
]

validation = validator.validate(plan, results)
validator.print_validation_report(validation)
```

## 📝 Configuration

All configuration is done through the orchestrator:

```python
orchestrator = VibiumUITestingOrchestrator(
    ollama_model="llama3.2:3b",  # Change LLM model
    headless=True,                # Headless browser
    debug=False                   # Debug output
)
```

## 🐛 Debugging

Enable debug mode to see detailed output:

```python
orchestrator = VibiumUITestingOrchestrator(debug=True)
```

This shows:
- Raw LLM responses
- Extracted JSON
- Step-by-step execution details

## 🔄 Integration with Other Tools

### Use with Pytest

```python
import pytest
import asyncio
from orchestrator import VibiumUITestingOrchestrator

@pytest.mark.asyncio
async def test_google_search():
    orchestrator = VibiumUITestingOrchestrator(headless=True)
    result = await orchestrator.run_test("Test Google search")
    await orchestrator.cleanup()
    
    assert result['validation']['overall_status'] == 'PASS'
```

### Use in CI/CD

```python
import os
from main import main

if __name__ == "__main__":
    if os.environ.get('CI'):
        print("Skipping UI tests in CI")
    else:
        asyncio.run(main())
```

## 📚 Dependencies

```
requests>=2.31.0
vibium>=0.1.0
playwright>=1.40.0
```

## 🎯 Next Steps

1. ✅ Install dependencies
2. ✅ Start Ollama
3. ✅ Run `python main.py`
4. ✅ Customize agents for your needs
5. ✅ Add new actions or modify existing ones

## 💡 Tips

- Start with `debug=True` to understand the flow
- Test agents independently before full integration
- Use headless mode for faster execution
- Customize system prompts for better results
- Add your own actions for specific use cases

Happy Testing! 🚀
