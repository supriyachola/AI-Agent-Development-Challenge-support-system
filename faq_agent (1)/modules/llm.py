
import subprocess
import json

def llm_fallback(prompt: str) -> str:
    try:
        result = subprocess.run(
            ["ollama", "run", "mistral"],
            input=prompt.encode(),
            stdout=subprocess.PIPE
        )
        return result.stdout.decode().strip()
    except:
        return "LLM fallback unavailable. Please check Ollama."
