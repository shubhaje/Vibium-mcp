"""
Ollama LLM Client
Handles communication with Ollama server
"""

import requests


class OllamaClient:
    """Client for interacting with Ollama LLM"""
    
    def __init__(self, model: str = "llama3.2:3b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
    
    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> str:
        """Generate response from Ollama"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "temperature": temperature,
            "stream": False
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return ""
    
    def check_availability(self) -> bool:
        """Check if Ollama server is available"""
        try:
            response = requests.get(self.base_url, timeout=2)
            return response.status_code == 200
        except Exception:
            return False
