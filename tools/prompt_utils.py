from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"

def load_prompt(name: str) -> str:
    """Return the text of a prompt file."""
    path = PROMPTS_DIR / f"{name}.txt"
    return path.read_text()
