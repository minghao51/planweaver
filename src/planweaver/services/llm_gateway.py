from typing import Optional, AsyncIterator, Dict, Any
import json
from pydantic import BaseModel, ValidationError
from litellm import completion, acompletion
from ..config import get_settings
import json_repair
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None


class LLMGateway:
    def __init__(self):
        self.settings = get_settings()
        self._gemini_client = None

    def _get_gemini_client(self):
        if self._gemini_client is None:
            api_key = self.settings.google_api_key or self.settings.gemini_api_key
            if not api_key:
                raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY is required for Gemini models")
            self._gemini_client = genai.Client(api_key=api_key)
        return self._gemini_client

    def _is_gemini_model(self, model: str) -> bool:
        return model.startswith("gemini-") or model.startswith("models/")

    def _convert_messages_for_gemini(self, messages: list[dict]) -> list[dict]:
        converted = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                role = "user"
            elif role == "assistant":
                role = "model"
            converted.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        return converted

    def complete(
        self,
        model: str,
        messages: list[dict],
        json_mode: bool = False,
        max_tokens: int = 4096
    ) -> dict:
        if self._is_gemini_model(model):
            return self._complete_gemini(model, messages, json_mode, max_tokens)
        
        if json_mode:
            messages.append({
                "role": "system",
                "content": "You must output valid JSON only. No markdown formatting, no code blocks."
            })

        response = completion(
            model=model,
            messages=messages,
            max_tokens=max_tokens
        )

        content = response.choices[0].message.content

        if json_mode:
            content = self._repair_json(content)

        return {
            "content": content,
            "model": model,
            "usage": response.usage.dict() if hasattr(response, "usage") else None
        }

    def _complete_gemini(
        self,
        model: str,
        messages: list[dict],
        json_mode: bool = False,
        max_tokens: int = 4096
    ) -> dict:
        client = self._get_gemini_client()
        
        gemini_messages = self._convert_messages_for_gemini(messages)
        
        generation_config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
        )
        
        if json_mode:
            generation_config = types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                response_mime_type="application/json"
            )

        response = client.models.generate_content(
            model=model,
            contents=gemini_messages,
            config=generation_config
        )

        content = response.text if hasattr(response, "text") else str(response)

        if json_mode:
            content = self._repair_json(content)

        return {
            "content": content,
            "model": model,
            "usage": None
        }

    async def acomplete(
        self,
        model: str,
        messages: list[dict],
        json_mode: bool = False,
        max_tokens: int = 4096
    ) -> dict:
        if self._is_gemini_model(model):
            return self._complete_gemini(model, messages, json_mode, max_tokens)
        
        if json_mode:
            messages.append({
                "role": "system",
                "content": "You must output valid JSON only. No markdown formatting, no code blocks."
            })

        response = await acompletion(
            model=model,
            messages=messages,
            max_tokens=max_tokens
        )

        content = response.choices[0].message.content

        if json_mode:
            content = self._repair_json(content)

        return {
            "content": content,
            "model": model,
            "usage": response.usage.dict() if hasattr(response, "usage") else None
        }

    def stream_complete(
        self,
        model: str,
        messages: list[dict],
        json_mode: bool = False
    ) -> AsyncIterator[dict]:
        if json_mode:
            messages.append({
                "role": "system",
                "content": "You must output valid JSON only. No markdown formatting, no code blocks."
            })

        response = completion(
            model=model,
            messages=messages,
            stream=True
        )

        for chunk in response:
            if chunk.choices[0].delta.content:
                yield {
                    "content": chunk.choices[0].delta.content,
                    "model": model
                }

    def _repair_json(self, content: Optional[str]) -> str:
        if content is None:
            return ""
        try:
            repaired = json_repair.repair_json(content)
            if isinstance(repaired, str):
                return repaired
            import json
            return json.dumps(repaired)
        except Exception as e:
            logger.warning(f"JSON repair failed: {e}")
            return content

    def parse_json_response(self, content: str, schema: Optional[type[BaseModel]] = None) -> Dict[str, Any]:
        content = self._repair_json(content)
        try:
            data = json.loads(content)
            if schema:
                validated = schema.model_validate(data)
                return validated.model_dump()
            return data
        except (ValidationError, json.JSONDecodeError) as e:
            logger.error(f"JSON validation failed: {e}")
            raise

    def get_available_models(self) -> list[dict]:
        return [
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "type": "planner", "provider": "google"},
            {"id": "gemini-2.5-flash-latest", "name": "Gemini 2.5 Flash Latest", "type": "planner", "provider": "google"},
            {"id": "gemini-3-flash", "name": "Gemini 3 Flash", "type": "executor", "provider": "google"},
            {"id": "gemini-3-pro", "name": "Gemini 3 Pro", "type": "executor", "provider": "google"},
            {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat", "type": "planner", "provider": "deepseek"},
            {"id": "anthropic/claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "type": "executor", "provider": "anthropic"},
            {"id": "anthropic/claude-3-opus-20240229", "name": "Claude 3 Opus", "type": "executor", "provider": "anthropic"},
            {"id": "openai/gpt-4o", "name": "GPT-4o", "type": "executor", "provider": "openai"},
            {"id": "ollama/llama2", "name": "Llama 2 (Ollama)", "type": "planner", "provider": "ollama"},
        ]
