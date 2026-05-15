from chromadb.utils.embedding_functions import ollama_embedding_function
import os
from dotenv import load_dotenv

load_dotenv()
ef = ollama_embedding_function.OllamaEmbeddingFunction(
    url="http://localhost:11434/api/embeddings",
    model_name=os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
)
try:
    print(ef(["test"]))
except Exception as e:
    print("Error:", e)
