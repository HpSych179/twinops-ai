"""
TwinOps AI - Base Agent
========================
Abstract base class for all TwinOps agents.
Provides common Gemini LLM integration, JSON parsing, and error handling.

Architecture Decision:
    We use google-genai (the newer unified SDK) for direct Gemini calls
    rather than ADK's high-level abstractions, giving us full control over
    prompts and structured outputs while still demonstrating Gemini integration.
    The ADK patterns (tool calling, agent delegation) are implemented in
    the Supervisor which coordinates the pipeline.
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from loguru import logger

try:
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    genai_types = None
    GENAI_AVAILABLE = False
    logger.warning("google-genai not installed — agents will use mock mode")

from models.digital_twin import DigitalTwin


class BaseAgent(ABC):
    """
    Abstract base for all TwinOps AI agents.

    Each subclass implements `run()` to process the Digital Twin
    and return an enriched version of it.
    """

    # Subclasses set these
    agent_name: str = "BaseAgent"
    system_prompt: str = ""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.model_name = model or os.getenv("AGENT_MODEL", "gemini-2.0-flash")
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self._client = None

        if GENAI_AVAILABLE and self._api_key:
            self._client = genai.Client(api_key=self._api_key)
            logger.debug(f"[{self.agent_name}] Gemini client initialized: {self.model_name}")
        else:
            logger.warning(
                f"[{self.agent_name}] Running in MOCK mode "
                "(no API key or google-genai not installed)"
            )

    @abstractmethod
    def run(self, twin: DigitalTwin) -> DigitalTwin:
        """
        Execute this agent's analysis on the Digital Twin.

        Args:
            twin: Current Digital Twin state (may be partially populated)

        Returns:
            Enriched Digital Twin with this agent's section filled in
        """
        ...

    # -----------------------------------------------------------------------
    # Shared LLM utilities
    # -----------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        """
        Send a prompt to Gemini and return the raw text response.
        Falls back to mock response if client is unavailable.
        Retries on rate-limit (429) with exponential backoff.
        """
        if self._client is None:
            logger.warning(f"[{self.agent_name}] LLM unavailable — returning mock response")
            return self._mock_response()

        import time
        last_exc = None
        for attempt in range(1, 4):  # up to 3 attempts
            try:
                logger.debug(f"[{self.agent_name}] Calling Gemini ({self.model_name}), attempt {attempt}...")
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=self.system_prompt,
                        temperature=0.2,
                        top_p=0.8,
                        max_output_tokens=2048,
                    ),
                )
                result = response.text
                logger.debug(f"[{self.agent_name}] Response received ({len(result)} chars)")
                return result
            except Exception as e:
                last_exc = e
                err_str = str(e)
                # Rate limit or server overload — wait and retry
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "503" in err_str or "UNAVAILABLE" in err_str:
                    wait = 15 * attempt  # 15s, 30s, 45s
                    logger.warning(f"[{self.agent_name}] Transient error (attempt {attempt}). Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                # Any other error — fail immediately
                logger.error(f"[{self.agent_name}] LLM call failed: {e}")
                raise

        # All retries exhausted — fall back to mock
        logger.warning(f"[{self.agent_name}] All retries exhausted after rate limit. Using fallback.")
        return self._mock_response()

    def _extract_json(self, text: str) -> dict[str, Any]:
        """
        Extract a JSON object from LLM response text.
        Handles markdown code blocks, thinking tokens, and raw JSON.
        Gemini 2.5 may emit thinking text before the JSON block.
        """
        # Strip any <think>...</think> or similar reasoning blocks
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

        # Try to extract from markdown code block first
        patterns = [
            r"```json\s*([\s\S]+?)\s*```",
            r"```\s*(\{[\s\S]+?\})\s*```",
            r"(\{[\s\S]+\})",  # bare JSON object — last resort
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                candidate = match.group(1).strip()
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue

        # Last resort: try parsing the whole stripped text
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"[{self.agent_name}] Failed to parse JSON from LLM response: {e}")
            logger.debug(f"Raw response was: {text[:500]}")
            raise ValueError(f"LLM response was not valid JSON: {e}") from e

    def _safe_run(self, twin: DigitalTwin, operation_name: str) -> tuple[DigitalTwin, bool]:
        """
        Wrapper that logs agent start/complete and handles errors gracefully.
        Returns (twin, success_bool).
        """
        twin.log_agent(self.agent_name, "started", f"Starting {operation_name}")
        try:
            result = self.run(twin)
            result.log_agent(self.agent_name, "completed", f"Completed {operation_name}")
            return result, True
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error during {operation_name}: {e}")
            twin.log_agent(
                self.agent_name,
                "error",
                f"Error in {operation_name}: {str(e)[:200]}",
            )
            return twin, False

    def _mock_response(self) -> str:
        """Override in subclasses to provide meaningful mock data for testing."""
        return json.dumps({"agent_summary": f"Mock response from {self.agent_name}", "mock": True})
