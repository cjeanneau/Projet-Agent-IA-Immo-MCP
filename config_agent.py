from dotenv import load_dotenv
import os
from langchain_mistralai import ChatMistralAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import ToolMessage

load_dotenv(override=True)

from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception
import httpx

def _is_llm_retryable(exc):
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 502, 503, 504)
    return isinstance(exc, (httpx.ConnectError, httpx.TimeoutException))

_llm_retry = retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential_jitter(initial=2, max=30, jitter=2),
    retry=retry_if_exception(_is_llm_retryable),
    reraise=True,
)

class MistralMCPCompat(ChatMistralAI):
    def _fix(self, messages):
        fixed = []
        for msg in messages:
            if isinstance(msg, ToolMessage) and isinstance(msg.content, list):
                text = "\n".join(
                    b["text"] for b in msg.content
                    if isinstance(b, dict) and "text" in b
                )
                msg = msg.model_copy(update={"content": text})
            fixed.append(msg)
        return fixed

    @_llm_retry
    async def agenerate(self, messages, *args, **kwargs):
        return await super().agenerate([self._fix(m) for m in messages], *args, **kwargs)

    @_llm_retry
    def generate(self, messages, *args, **kwargs):
        return super().generate([self._fix(m) for m in messages], *args, **kwargs)


api_key_mistral = os.getenv("MISTRAL_API_KEY")
if not api_key_mistral: 
    raise ValueError("Clé API Mistral manquante. Veuillez définir la variable d'environnement MISTRAL_API_KEY.")

api_key_gemini = os.getenv("GEMINI_API_KEY")
if not api_key_gemini:
    raise ValueError("Clé API Gemini manquante. Veuillez définir la variable d'environnement GEMINI_API_KEY.")

#llm_mistral = ChatMistralAI(model="mistral-small-2503", api_key=api_key_mistral, temperature=0)

llm_mistral = MistralMCPCompat(model="mistral-small-2503", api_key=api_key_mistral, temperature=0)

llm_gemini = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key_gemini, temperature=0)

MCP_URL = os.getenv('MCP_URL', "http://localhost:8100/mcp")