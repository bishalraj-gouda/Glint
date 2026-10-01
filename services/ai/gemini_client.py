"""
Gemini Client Wrapper for Campus-Link AI Career Intelligence Platform.
Powered by Google GenAI SDK (google-genai) with robust error handling
and deterministic fallback generation when API key is unconfigured or unreachable.
"""
import os
import json
import logging
from typing import Any, Callable, Dict, Optional
from flask import current_app

logger = logging.getLogger("campus_link.ai.gemini")

# Try importing the official google-genai SDK
try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-genai package is not installed. GeminiClient will run in fallback mode.")


class GeminiClient:
    """Wrapper around Google GenAI client with enterprise-grade resilience."""

    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL)
        self._client = None
        self._init_client()

    def _init_client(self):
        """Initializes the GenAI client if credentials are present."""
        # Try retrieving key from Flask current_app context if not found in env
        if not self.api_key:
            try:
                if current_app and current_app.config.get("GEMINI_API_KEY"):
                    self.api_key = current_app.config.get("GEMINI_API_KEY", "")
            except RuntimeError:
                pass

        if self.api_key and GENAI_AVAILABLE:
            try:
                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"GeminiClient initialized successfully with model {self.model}.")
            except Exception as e:
                logger.error(f"Failed to initialize GenAI client: {e}")
                self._client = None
        else:
            self._client = None

    def is_configured(self) -> bool:
        """Returns True if a valid client connection is ready."""
        if not self._client and self.api_key and GENAI_AVAILABLE:
            self._init_client()
        return self._client is not None

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        fallback_text: Optional[str] = None
    ) -> str:
        """Generates standard unstructured text response with fallback."""
        if self.is_configured():
            try:
                config = types.GenerateContentConfig(
                    temperature=temperature,
                    system_instruction=system_instruction
                ) if system_instruction else types.GenerateContentConfig(temperature=temperature)

                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Gemini API call failed: {e}. Falling back to default response.")

        return fallback_text or "AI response is currently operating in offline mode. Please configure GEMINI_API_KEY for live generative insights."

    def generate_structured(
        self,
        prompt: str,
        response_schema: Optional[Any] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        fallback_fn: Optional[Callable[[], Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generates structured JSON response guaranteed to match application schemas.
        If API fails or key is missing, executes `fallback_fn` to provide realistic, deterministic data.
        """
        if self.is_configured():
            try:
                config_args = {
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                }
                if system_instruction:
                    config_args["system_instruction"] = system_instruction
                if response_schema:
                    config_args["response_schema"] = response_schema

                config = types.GenerateContentConfig(**config_args)

                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config
                )

                if response and response.text:
                    text_content = response.text.strip()
                    # Strip any potential markdown triple backticks if the model enclosed it
                    if text_content.startswith("```json"):
                        text_content = text_content[7:]
                    elif text_content.startswith("```"):
                        text_content = text_content[3:]
                    if text_content.endswith("```"):
                        text_content = text_content[:-3]
                    text_content = text_content.strip()

                    parsed = json.loads(text_content)
                    return parsed
            except Exception as e:
                logger.warning(f"Structured Gemini API call failed: {e}. Executing fallback generator.")

        if fallback_fn:
            try:
                return fallback_fn()
            except Exception as fe:
                logger.error(f"Fallback generator failed: {fe}")

        return {"status": "fallback", "message": "Standard deterministic intelligence baseline generated."}


# Singleton accessor
_gemini_client_instance = None

def get_gemini_client() -> GeminiClient:
    """Gets or initializes the global GeminiClient singleton."""
    global _gemini_client_instance
    if _gemini_client_instance is None:
        _gemini_client_instance = GeminiClient()
    return _gemini_client_instance
