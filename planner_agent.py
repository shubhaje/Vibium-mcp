"""
Planner Agent
Responsible for creating test plans from user prompts
"""

import json
import re
from typing import List
from models import TestStep, TestPlan
from ollama_client import OllamaClient


class PlannerAgent:
    """Agent responsible for creating test plans"""
    
    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client
        self.system_prompt = """You are an expert UI test planner. Your job is to create detailed, 
        step-by-step test plans for web applications. 
        
        Output your test plan in the following JSON format:
        {
            "objective": "Clear description of what we're testing",
            "steps": [
                {
                    "step_number": 1,
                    "action": "navigate",
                    "target": "https://example.com",
                    "value": "",
                    "expected_result": "what should happen"
                }
            ],
            "success_criteria": ["criterion 1", "criterion 2"]
        }
        
        CRITICAL RULES:
        - ALWAYS use double quotes (") for strings, never single quotes
        - NEVER use trailing commas before closing brackets ] or braces }
        - For 'navigate' actions, ALWAYS use full URLs (https://...)
        - For 'click', 'type', 'verify' actions, use CSS selectors
        - Keep value as empty string "" if not needed, don't omit it
        - Return ONLY valid JSON with no trailing commas
        
        Available actions:
        - navigate: Go to a URL (target must be full URL)
        - click: Click an element (target is CSS selector)
        - type: Type text into element (target is CSS selector, value is text)
        - verify: Check element exists or contains text (target is CSS selector)
        - wait: Wait for time or element (value is seconds or target is selector)
        - scroll: Scroll page (value is pixels or target is selector)"""
    
    def create_plan(self, user_prompt: str, debug: bool = False) -> TestPlan:
        """Create a test plan based on user prompt"""
        prompt = f"""Create a detailed UI test plan for the following requirement:

{user_prompt}

IMPORTANT JSON RULES:
1. Use ONLY double quotes for all strings
2. NO trailing commas before ] or }}
3. For 'navigate' actions, use full URLs (https://...)
4. Always include "value" field (use "" if empty)
5. Return ONLY the JSON object, no markdown, no backticks, no explanations

Test Plan:"""

        response = self.llm.generate(prompt, self.system_prompt, temperature=0.3)
        
        if debug:
            print(f"\n[DEBUG] Raw LLM Response:\n{response}\n")

        try:
            json_str = self._extract_json(response)
            
            if debug:
                print(f"\n[DEBUG] Extracted JSON:\n{json_str}\n")
            
            plan_data = json.loads(json_str)

            # Convert to TestPlan object
            steps = self._parse_steps(plan_data.get('steps', []))

            return TestPlan(
                objective=plan_data.get('objective', user_prompt),
                steps=steps,
                success_criteria=plan_data.get('success_criteria', [])
            )
        except Exception as e:
            print(f"[ERROR] Failed to parse JSON response: {e}")
            if debug:
                print(f"[ERROR] Response was:\n{response}\n")
            
            # Return a basic fallback plan
            return self._create_fallback_plan(user_prompt)

    def _parse_steps(self, steps_data: List[dict]) -> List[TestStep]:
        """Parse steps from JSON data"""
        steps = []
        for idx, step in enumerate(steps_data):
            step_obj = TestStep(
                step_number=int(step.get('step_number', idx + 1)),
                action=str(step.get('action', 'navigate')),
                target=str(step.get('target', '')),
                value=str(step.get('value', '') or ''),
                expected_result=str(step.get('expected_result', '') or '')
            )
            steps.append(step_obj)
        return steps

    def _create_fallback_plan(self, user_prompt: str) -> TestPlan:
        """Create a basic fallback plan if LLM parsing fails"""
        return TestPlan(
            objective=user_prompt,
            steps=[TestStep(
                step_number=1,
                action="navigate",
                target="https://www.google.com",
                value="",
                expected_result="Page loads successfully"
            )],
            success_criteria=["Test completes without errors"]
        )

    def _extract_json(self, text: str) -> str:
        """Extract and clean JSON from LLM response"""
        if not text:
            raise ValueError("Empty response")

        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Find JSON object boundaries
        start = text.find('{')
        end = text.rfind('}')
        
        if start == -1 or end == -1:
            raise ValueError("No JSON object found in response")
        
        json_str = text[start:end+1]
        
        # Process the JSON more carefully
        result = []
        i = 0
        while i < len(json_str):
            char = json_str[i]
            
            if char == '"':
                # We're starting a string, add the quote and preserve everything until closing quote
                result.append('"')
                i += 1
                
                # Collect the entire string value
                while i < len(json_str):
                    char = json_str[i]
                    
                    if char == '\\' and i + 1 < len(json_str):
                        # Escape sequence - preserve it
                        result.append(json_str[i:i+2])
                        i += 2
                    elif char == '"':
                        # End of string
                        result.append('"')
                        i += 1
                        break
                    elif char == '\n':
                        # Newline in string - convert to literal \n
                        result.append('\\n')
                        i += 1
                    elif char == '\r':
                        # Skip carriage returns
                        i += 1
                    elif char == '/':
                        # Check for comment (// or /*)
                        if i + 1 < len(json_str) and json_str[i+1] == '/':
                            # Comment at end of line - skip until next newline
                            while i < len(json_str) and json_str[i] != '\n':
                                i += 1
                        else:
                            result.append(char)
                            i += 1
                    else:
                        result.append(char)
                        i += 1
            else:
                result.append(char)
                i += 1
        
        json_str = ''.join(result)
        
        # Fix quotes (normalize smart quotes)
        json_str = json_str.replace('"', '"').replace('"', '"')
        json_str = json_str.replace(''', '"').replace(''', '"')
        
        # Fix trailing commas
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        
        return json_str
