"""
Utilities for loading and managing prompt templates
"""
import os


def load_prompt_template(filename: str, is_from_sii: bool = False) -> str:
    """Load prompt template from prompts directory"""
    file_path = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(file_path, '..', 'prompts', filename)
    if is_from_sii:
        sii_prompt_path = os.path.join(file_path, '..', 'prompts', 'prompts_for_sii', filename)
        if os.path.exists(sii_prompt_path):
            prompt_path = sii_prompt_path
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file {prompt_path} not found")
    except Exception as e:
        raise Exception(f"Error loading prompt {prompt_path}: {e}")