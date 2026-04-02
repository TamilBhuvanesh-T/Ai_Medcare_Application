import os
import subprocess


OLLAMA_PATH = os.getenv(
    "OLLAMA_PATH",
    r"C:\Users\Tamil\AppData\Local\Programs\Ollama\ollama.exe",
)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")


def run_llm(prompt: str) -> str:
    """Run the local Ollama model and return plain text output."""

    print("#### LLM CALLED ####")

    try:
        result = subprocess.run(
            [OLLAMA_PATH, "run", OLLAMA_MODEL],
            input=prompt,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="ignore",
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return "AI response timed out."
    except FileNotFoundError:
        return "Local LLM executable was not found."

    output = (result.stdout or "").strip()
    error_output = (result.stderr or "").strip()

    if result.returncode != 0 and error_output:
        return error_output

    if "...done thinking." in output:
        output = output.split("...done thinking.")[-1].strip()

    return output or "No response generated."
