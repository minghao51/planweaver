import pytest
from unittest.mock import Mock, patch, MagicMock


class TestLLMGateway:
    def test_complete_returns_content(self):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "test response"
        mock_response.usage = Mock()
        mock_response.usage.dict.return_value = {"prompt_tokens": 10, "completion_tokens": 5}

        with patch("src.planweaver.services.llm_gateway.completion", return_value=mock_response):
            from src.planweaver.services.llm_gateway import LLMGateway
            gateway = LLMGateway()
            result = gateway.complete(
                model="test/model",
                messages=[{"role": "user", "content": "hello"}]
            )

            assert result["content"] == "test response"
            assert result["model"] == "test/model"
            assert result["usage"] is not None

    def test_complete_with_json_mode(self):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"key": "value"}'
        mock_response.usage = Mock()
        mock_response.usage.dict.return_value = {"prompt_tokens": 10, "completion_tokens": 5}

        with patch("src.planweaver.services.llm_gateway.completion", return_value=mock_response):
            with patch("src.planweaver.services.llm_gateway.json_repair") as mock_repair:
                mock_repair.repair_json.return_value = '{"key": "value"}'
                
                from src.planweaver.services.llm_gateway import LLMGateway
                gateway = LLMGateway()
                result = gateway.complete(
                    model="test/model",
                    messages=[{"role": "user", "content": "hello"}],
                    json_mode=True
                )

                assert result["content"] == '{"key": "value"}'
                mock_repair.repair_json.assert_called_once()

    def test_get_available_models_returns_list(self):
        from src.planweaver.services.llm_gateway import LLMGateway
        gateway = LLMGateway()
        models = gateway.get_available_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert all("id" in m and "name" in m for m in models)

    def test_get_available_models_contains_gemini(self):
        from src.planweaver.services.llm_gateway import LLMGateway
        gateway = LLMGateway()
        models = gateway.get_available_models()
        model_ids = [m["id"] for m in models]

        assert any("gemini" in mid for mid in model_ids), "Should contain Gemini models"

    def test_get_available_models_contains_google_provider(self):
        from src.planweaver.services.llm_gateway import LLMGateway
        gateway = LLMGateway()
        models = gateway.get_available_models()

        google_models = [m for m in models if m.get("provider") == "google"]
        assert len(google_models) > 0, "Should contain Google provider models"
        assert any("gemini-2.5-flash" in m["id"] for m in google_models), "Should contain Gemini 2.5 Flash"

    @pytest.mark.asyncio
    async def test_acomplete_returns_content(self):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "async response"
        mock_response.usage = Mock()
        mock_response.usage.dict.return_value = {"prompt_tokens": 10, "completion_tokens": 5}

        with patch("src.planweaver.services.llm_gateway.acompletion", return_value=mock_response):
            from src.planweaver.services.llm_gateway import LLMGateway
            gateway = LLMGateway()
            result = await gateway.acomplete(
                model="test/model",
                messages=[{"role": "user", "content": "hello"}]
            )

            assert result["content"] == "async response"

    def test_repair_json_handles_invalid_json(self):
        from src.planweaver.services.llm_gateway import LLMGateway
        gateway = LLMGateway()
        
        result = gateway._repair_json("{invalid json")
        
        assert isinstance(result, str)

    def test_is_gemini_model_with_gemini_prefix(self):
        from src.planweaver.services.llm_gateway import LLMGateway
        gateway = LLMGateway()
        
        assert gateway._is_gemini_model("gemini-2.5-flash") is True
        assert gateway._is_gemini_model("gemini-3-flash") is True
        assert gateway._is_gemini_model("gemini-3-pro") is True

    def test_is_gemini_model_with_models_prefix(self):
        from src.planweaver.services.llm_gateway import LLMGateway
        gateway = LLMGateway()
        
        assert gateway._is_gemini_model("models/gemini-2.5-flash") is True

    def test_is_gemini_model_with_non_gemini(self):
        from src.planweaver.services.llm_gateway import LLMGateway
        gateway = LLMGateway()
        
        assert gateway._is_gemini_model("deepseek/deepseek-chat") is False
        assert gateway._is_gemini_model("anthropic/claude-3-5-sonnet") is False
        assert gateway._is_gemini_model("openai/gpt-4o") is False

    def test_convert_messages_for_gemini(self):
        from src.planweaver.services.llm_gateway import LLMGateway
        gateway = LLMGateway()
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        result = gateway._convert_messages_for_gemini(messages)
        
        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[0]["parts"][0]["text"] == "Hello"
        assert result[1]["role"] == "user"
        assert result[1]["parts"][0]["text"] == "You are helpful"
        assert result[2]["role"] == "model"
        assert result[2]["parts"][0]["text"] == "Hi there!"

    def test_complete_routes_to_gemini_for_gemini_model(self):
        from src.planweaver.services.llm_gateway import LLMGateway
        
        with patch("src.planweaver.services.llm_gateway.genai") as mock_genai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "gemini response"
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client
            
            gateway = LLMGateway()
            with patch.object(gateway, '_get_gemini_client', return_value=mock_client):
                result = gateway.complete(
                    model="gemini-2.5-flash",
                    messages=[{"role": "user", "content": "hello"}]
                )
                
                assert result["content"] == "gemini response"
                mock_client.models.generate_content.assert_called_once()

    def test_complete_fallback_to_litellm_for_non_gemini(self):
        from src.planweaver.services.llm_gateway import LLMGateway
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "litellm response"
        mock_response.usage = Mock()
        mock_response.usage.dict.return_value = {"prompt_tokens": 10, "completion_tokens": 5}
        
        with patch("src.planweaver.services.llm_gateway.completion", return_value=mock_response) as mock_completion:
            gateway = LLMGateway()
            result = gateway.complete(
                model="deepseek/deepseek-chat",
                messages=[{"role": "user", "content": "hello"}]
            )
            
            assert result["content"] == "litellm response"
            mock_completion.assert_called_once()

    def test_complete_gemini_with_json_mode(self):
        from src.planweaver.services.llm_gateway import LLMGateway
        
        with patch("src.planweaver.services.llm_gateway.genai") as mock_genai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = '{"key": "value"}'
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client
            
            gateway = LLMGateway()
            with patch.object(gateway, '_get_gemini_client', return_value=mock_client):
                result = gateway.complete(
                    model="gemini-2.5-flash",
                    messages=[{"role": "user", "content": "hello"}],
                    json_mode=True
                )
                
                assert result["content"] == '{"key": "value"}'
                call_args = mock_client.models.generate_content.call_args
                assert call_args.kwargs["config"].response_mime_type == "application/json"

    @pytest.mark.asyncio
    async def test_acomplete_routes_to_gemini_for_gemini_model(self):
        from src.planweaver.services.llm_gateway import LLMGateway
        
        with patch("src.planweaver.services.llm_gateway.genai") as mock_genai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "gemini async response"
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client
            
            gateway = LLMGateway()
            with patch.object(gateway, '_get_gemini_client', return_value=mock_client):
                result = await gateway.acomplete(
                    model="gemini-3-flash",
                    messages=[{"role": "user", "content": "hello"}]
                )
                
                assert result["content"] == "gemini async response"
