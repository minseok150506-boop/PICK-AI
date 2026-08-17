from __future__ import annotations
import os

from pick_engine.client import generate as native_generate, health as native_health

MODE = os.environ.get("PICK_AI_PROVIDER", "native_first").strip().lower()

def native_available():
    return bool(native_health().get("ok"))

def choose_provider():
    """
    native_first: PICK own engine first, Ollama fallback
    native_only: PICK own engine only
    ollama_first: Ollama first
    """
    return MODE

def generate_native(prompt: str):
    return native_generate(prompt, max_new_tokens=384, temperature=0.75, top_p=0.92)
