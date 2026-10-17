"""
DOT AI - NVIDIA API Client
Specialized for NVIDIA Nemotron 3.5 Super VL 120B with Thinking Support.
Interfaces with NVIDIA NIM (OpenAI-compatible) endpoint.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple
from openai import OpenAI, AsyncOpenAI
import config

logger = logging.getLogger("dot.nvidia")

class NvidiaClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or config.NVIDIA_API_KEY
        self.base_url = base_url or config.NVIDIA_BASE_URL
        self.primary_model = config.TARGET_NEMOTRON_MODEL
        self.total_tokens_used = 0
        self.request_count = 0

        self._sync_client: Optional[OpenAI] = None
        self._async_client: Optional[AsyncOpenAI] = None

    def update_key(self, api_key: str):
        self.api_key = api_key.strip()
        self._sync_client = None
        self._async_client = None

    @property
    def sync_client(self) -> OpenAI:
        if self._sync_client is None:
            self._sync_client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key or "missing_key"
            )
        return self._sync_client

    @property
    def async_client(self) -> AsyncOpenAI:
        if self._async_client is None:
            self._async_client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key or "missing_key"
            )
        return self._async_client

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 5)

    def test_connection(self) -> Dict[str, Any]:
        """Verify API key with Nemotron 3.5 Super VL"""
        if not self.is_configured():
            return {"success": False, "error": "NVIDIA API Key is missing. Please set it in Settings."}

        try:
            extra_body = {"chat_template_kwargs": {"enable_thinking": True}} if config.ENABLE_THINKING else None
            resp = self.sync_client.chat.completions.create(
                model=self.primary_model,
                messages=[{"role": "user", "content": "Respond with 'CONNECTED'"}],
                max_tokens=20,
                temperature=config.MODEL_TEMPERATURE,
                top_p=config.MODEL_TOP_P,
                extra_body=extra_body
            )
            content = resp.choices[0].message.content or "CONNECTED"
            return {
                "success": True,
                "model": self.primary_model,
                "response": content
            }
        except Exception as e:
            logger.error(f"NVIDIA API test failed: {e}")
            return {"success": False, "error": str(e)}

    async def stream_chat(
        self, 
        messages: List[Dict[str, Any]], 
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        enable_thinking: bool = True
    ) -> AsyncGenerator[Tuple[str, str], None]:
        """
        Stream chunks from NVIDIA Nemotron.
        Yields (chunk_type, text), where chunk_type is 'reasoning' or 'content'.
        """
        model = model or self.primary_model
        max_tokens = max_tokens or config.MODEL_MAX_TOKENS
        temperature = temperature if temperature is not None else config.MODEL_TEMPERATURE

        extra_body = {"chat_template_kwargs": {"enable_thinking": True}} if enable_thinking else None

        try:
            stream = await self.async_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=config.MODEL_TOP_P,
                extra_body=extra_body,
                seed=42,
                stream=True
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                
                # Check for Nemotron thinking / reasoning content
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    yield ("reasoning", reasoning)

                # Standard content
                if delta.content is not None:
                    yield ("content", delta.content)

            self.request_count += 1
        except Exception as e:
            yield ("content", f"\n[NVIDIA API Error: {str(e)}]")

    async def structured_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        on_reasoning_callback: Optional[callable] = None
    ) -> str:
        """
        Executes request on Nemotron 3.5 Super VL, capturing both reasoning and final content.
        """
        model = model or self.primary_model
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        full_content = []
        full_reasoning = []

        async for chunk_type, text in self.stream_chat(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            enable_thinking=config.ENABLE_THINKING
        ):
            if chunk_type == "reasoning":
                full_reasoning.append(text)
                if on_reasoning_callback:
                    on_reasoning_callback(text)
            else:
                full_content.append(text)

        result = "".join(full_content)
        return result
