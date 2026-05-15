import os
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()

# --- GLOBAL OLLAMA OVERRIDE ---
# CrewAI's memory analyzer and tools often blindly default to OpenAI.
# We set dummy OpenAI variables that point directly to Ollama's OpenAI-compatible API to intercept them!
# We cover OPENAI_API_BASE, OPENAI_BASE_URL, and LITELLM_API_BASE because different internal tools use different clients.
base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") + "/v1"
os.environ["OPENAI_API_BASE"] = base_url
os.environ["OPENAI_BASE_URL"] = base_url
os.environ["LITELLM_API_BASE"] = base_url
os.environ["OPENAI_API_KEY"] = "NA"
# Force any stray OpenAI calls to ask for the local Ollama model instead of 'gpt-4'
os.environ["OPENAI_MODEL_NAME"] = os.getenv("OLLAMA_MODEL_NAME", "gemma4:e2b")


def get_default_llm():
    """
    Returns the default LLM configuration for the CrewAI agents using Ollama.
    """
    temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
    model_name = os.getenv("OLLAMA_MODEL_NAME", "gemma4:e2b")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # CrewAI/LiteLLM requires the 'ollama/' prefix
    if not model_name.startswith("ollama/"):
        model_name = f"ollama/{model_name}"
        
    return LLM(
        model=model_name,
        temperature=temperature,
        base_url=base_url
    )

def get_embedder_config():
    """
    Returns the embedder configuration for CrewAI memory using Ollama.
    """
    return {
        "provider": "ollama",
        "config": {
            "model": os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large"),
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        }
    }
