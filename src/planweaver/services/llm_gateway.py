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
JSON_ONLY_INSTRUCTION = "You must output valid JSON only. No markdown formatting, no code blocks."


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

    def _prepare_messages(self, messages: list[dict], json_mode: bool) -> list[dict]:
        prepared = list(messages)
        if json_mode:
            prepared.append({"role": "system", "content": JSON_ONLY_INSTRUCTION})
        return prepared

    def _format_response(self, model: str, content: Optional[str], usage: Optional[Dict[str, Any]] = None) -> dict:
        return {
            "content": content or "",
            "model": model,
            "usage": usage,
        }

    def _normalize_content(self, content: Optional[str], json_mode: bool) -> str:
        return self._repair_json(content) if json_mode else (content or "")

    def _extract_usage(self, response: Any) -> Optional[Dict[str, Any]]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None
        return usage.dict() if hasattr(usage, "dict") else usage

    def complete(
        self,
        model: str,
        messages: list[dict],
        json_mode: bool = False,
        max_tokens: int = 4096
    ) -> dict:
        if self._is_gemini_model(model):
            return self._complete_gemini(model, messages, json_mode, max_tokens)

        prepared_messages = self._prepare_messages(messages, json_mode)

        response = completion(
            model=model,
            messages=prepared_messages,
            max_tokens=max_tokens
        )

        content = self._normalize_content(response.choices[0].message.content, json_mode)
        return self._format_response(model, content, self._extract_usage(response))

    def _complete_gemini(
        self,
        model: str,
        messages: list[dict],
        json_mode: bool = False,
        max_tokens: int = 4096
    ) -> dict:
        client = self._get_gemini_client()

        prepared_messages = self._prepare_messages(messages, json_mode)
        gemini_messages = self._convert_messages_for_gemini(prepared_messages)

        config_kwargs = {"max_output_tokens": max_tokens}
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"
        generation_config = types.GenerateContentConfig(**config_kwargs)

        response = client.models.generate_content(
            model=model,
            contents=gemini_messages,
            config=generation_config
        )

        content = response.text if hasattr(response, "text") else str(response)
        return self._format_response(model, self._normalize_content(content, json_mode))

    async def acomplete(
        self,
        model: str,
        messages: list[dict],
        json_mode: bool = False,
        max_tokens: int = 4096
    ) -> dict:
        if self._is_gemini_model(model):
            return self._complete_gemini(model, messages, json_mode, max_tokens)

        prepared_messages = self._prepare_messages(messages, json_mode)

        response = await acompletion(
            model=model,
            messages=prepared_messages,
            max_tokens=max_tokens
        )

        content = self._normalize_content(response.choices[0].message.content, json_mode)
        return self._format_response(model, content, self._extract_usage(response))

    def stream_complete(
        self,
        model: str,
        messages: list[dict],
        json_mode: bool = False
    ) -> AsyncIterator[dict]:
        prepared_messages = self._prepare_messages(messages, json_mode)

        response = completion(
            model=model,
            messages=prepared_messages,
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
        """Get available models from database, with fallback to hard-coded list.

        Returns:
            List of model dictionaries with keys: id, name, type, provider, is_free, pricing_info, context_length
        """
        from ..db.models import AvailableModel
        from ..db.database import get_session

        session = get_session()
        try:
            # Fetch active models from DB
            db_models = session.query(AvailableModel).filter_by(is_active=True).all()

            if db_models:
                # Return models from database
                return [
                    {
                        "id": m.model_id,
                        "name": m.name,
                        "type": m.type,
                        "provider": m.provider,
                        "is_free": m.is_free,
                        "pricing_info": m.pricing_info,
                        "context_length": m.context_length
                    }
                    for m in db_models
                ]
            else:
                # Fallback to hard-coded list if DB is empty
                logger.info("No models in database, using fallback list")
                return self._get_fallback_models()
        except Exception as e:
            logger.warning(f"Error fetching models from database: {e}, using fallback list")
            return self._get_fallback_models()
        finally:
            session.close()

    def _get_fallback_models(self) -> list[dict]:
        """Hard-coded fallback models when database is empty or unavailable.

        Returns:
            List of model dictionaries
        """
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
