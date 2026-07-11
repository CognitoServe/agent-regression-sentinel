import httpx
import json
import time
from typing import Tuple, Dict, Any

class ResearchAgentAdapter:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")
        
    def execute(self, prompt: str) -> Tuple[str, int, str]:
        """
        Executes a prompt against the research agent over HTTP.
        Returns (raw_output_json, latency_ms, error_string)
        """
        start_time = time.time()
        error_msg = ""
        raw_output = ""
        
        try:
            response = httpx.post(
                f"{self.base_url}/research",
                json={"prompt": prompt},
                timeout=120.0
            )
            
            if response.status_code == 200:
                raw_output = response.text
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                raw_output = response.text
                
        except httpx.RequestError as e:
            error_msg = f"Connection error: {str(e)}"
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            
        latency_ms = int((time.time() - start_time) * 1000)
        
        return raw_output, latency_ms, error_msg
