import pytest
from unittest.mock import patch, MagicMock
import json
import os
from app.services.meta_llm import MetaLLMAnalyzer, ANALYSIS_PROMPT, COMPONENT_GENERATION_PROMPTS, RATIONALE_PROMPT
from app.models.prompt import TaskType, BehaviorType, PromptComponent, ComponentType

class TestMetaLLMAnalyzer:
    """Tests for MetaLLMAnalyzer class."""
    
    def test_init_no_api_key(self):
        """Test initialization with no API key."""
        analyzer = MetaLLMAnalyzer(api_key=None)
        
        assert analyzer.api_key is None
        assert analyzer.use_mock is True
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "LLM_MODEL": "test-model"})
    def test_init_with_env_vars(self):
        """Test initialization with environment variables."""
        with patch('openai.OpenAI') as mock_openai:
            analyzer = MetaLLMAnalyzer()
            
            assert analyzer.api_key == "test-key"
            assert analyzer.model == "test-model"
            assert analyzer.use_mock is False
            mock_openai.assert_called_once_with(api_key="test-key")
    
    @patch('openai.OpenAI')
    def test_init_exception(self, mock_openai):
        """Test initialization with exception."""
        mock_openai.side_effect = Exception("Test exception")
        
        analyzer = MetaLLMAnalyzer(api_key="test-key")
        
        assert analyzer.api_key == "test-key"
        assert analyzer.use_mock is True  # Fallback to mock mode
    
    def test_analyze_task_mock(self):
        """Test analyze_task with mock responses."""
        analyzer = MetaLLMAnalyzer(api_key=None)
        result = analyzer.analyze_task("Explain quantum computing")
        
        assert "detected_tasks" in result
        assert "detected_behaviors" in result
        assert "domain_hint" in result
        assert isinstance(result["detected_tasks"][0], TaskType)
        assert isinstance(result["detected_behaviors"][0], BehaviorType)
    
    @patch('openai.OpenAI')
    def test_analyze_task_api(self, mock_openai):
        """Test analyze_task with API call."""
        # Setup mock response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_content = json.dumps({
            "reasoning_tasks": ["deduction", "comparison"],
            "output_behaviors": ["precision", "step_by_step"],
            "domain": "physics"
        })
        mock_response.choices = [MagicMock(message=MagicMock(content=mock_content))]
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test the method
        analyzer = MetaLLMAnalyzer(api_key="test-key")
        result = analyzer.analyze_task("Explain quantum computing")
        
        # Verify results
        assert TaskType.DEDUCTION in result["detected_tasks"]
        assert TaskType.COMPARISON in result["detected_tasks"]
        assert BehaviorType.PRECISION in result["detected_behaviors"]
        assert BehaviorType.STEP_BY_STEP in result["detected_behaviors"]
        assert result["domain_hint"] == "physics"
        
        # Verify API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["model"] == analyzer.model
        assert call_args["response_format"] == {"type": "json_object"}
        assert call_args["temperature"] == 0.1
        assert len(call_args["messages"]) == 2
        assert call_args["messages"][0]["role"] == "system"
        assert call_args["messages"][0]["content"] == ANALYSIS_PROMPT
    
    @patch('openai.OpenAI')
    def test_analyze_task_api_error(self, mock_openai):
        """Test analyze_task with API error."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Test exception")
        
        # Test the method
        analyzer = MetaLLMAnalyzer(api_key="test-key")
        result = analyzer.analyze_task("Explain quantum computing")
        
        # Verify fallback results returned
        assert len(result["detected_tasks"]) > 0
        assert len(result["detected_behaviors"]) > 0
        assert "domain_hint" in result
    
    def test_generate_component_content_mock(self):
        """Test generate_component_content with mock responses."""
        analyzer = MetaLLMAnalyzer(api_key=None)
        
        task_analysis = {
            "detected_tasks": [TaskType.DEDUCTION],
            "detected_behaviors": [BehaviorType.PRECISION]
        }
        
        result = analyzer.generate_component_content(
            "instruction", task_analysis, "Explain quantum computing"
        )
        
        assert "Explain quantum computing" in result
        
        # Test each component type
        for component_type in ["context", "example", "constraint", "output_format"]:
            content = analyzer.generate_component_content(
                component_type, task_analysis, "Explain quantum computing"
            )
            assert isinstance(content, str)
            assert len(content) > 0
    
    @patch('openai.OpenAI')
    def test_generate_component_content_api(self, mock_openai):
        """Test generate_component_content with API call."""
        # Setup mock response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Generated content"))]
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test the method
        analyzer = MetaLLMAnalyzer(api_key="test-key")
        task_analysis = {
            "detected_tasks": [TaskType.DEDUCTION],
            "detected_behaviors": [BehaviorType.PRECISION]
        }
        
        result = analyzer.generate_component_content(
            "instruction", task_analysis, "Explain quantum computing"
        )
        
        assert result == "Generated content"
        
        # Verify API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["model"] == analyzer.model
        assert call_args["temperature"] == 0.7
        assert len(call_args["messages"]) == 2
        assert call_args["messages"][0]["role"] == "system"
        assert call_args["messages"][0]["content"] == COMPONENT_GENERATION_PROMPTS["instruction"]
    
    @patch('openai.OpenAI')
    def test_generate_component_content_api_error(self, mock_openai):
        """Test generate_component_content with API error."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Test exception")
        
        # Test the method
        analyzer = MetaLLMAnalyzer(api_key="test-key")
        task_analysis = {
            "detected_tasks": [TaskType.DEDUCTION],
            "detected_behaviors": [BehaviorType.PRECISION]
        }
        
        result = analyzer.generate_component_content(
            "instruction", task_analysis, "Explain quantum computing"
        )
        
        # Verify fallback content returned
        assert "CONTENT FOR: Explain quantum computing" in result
    
    def test_generate_rationale_mock(self):
        """Test generate_rationale with mock responses."""
        analyzer = MetaLLMAnalyzer(api_key=None)
        
        components = [
            PromptComponent(type=ComponentType.INSTRUCTION, content="Test", position=1),
            PromptComponent(type=ComponentType.EXAMPLE, content="Test", position=2)
        ]
        
        task_analysis = {
            "detected_tasks": [TaskType.DEDUCTION],
            "detected_behaviors": [BehaviorType.PRECISION]
        }
        
        result = analyzer.generate_rationale(components, task_analysis, 85.5)
        
        assert "instruction, example" in result
        assert "85.5" in result
    
    @patch('openai.OpenAI')
    def test_generate_rationale_api(self, mock_openai):
        """Test generate_rationale with API call."""
        # Setup mock response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Generated rationale"))]
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test the method
        analyzer = MetaLLMAnalyzer(api_key="test-key")
        components = [
            PromptComponent(type=ComponentType.INSTRUCTION, content="Test", position=1),
            PromptComponent(type=ComponentType.EXAMPLE, content="Test", position=2)
        ]
        
        task_analysis = {
            "detected_tasks": [TaskType.DEDUCTION],
            "detected_behaviors": [BehaviorType.PRECISION]
        }
        
        result = analyzer.generate_rationale(components, task_analysis, 85.5)
        
        assert result == "Generated rationale"
        
        # Verify API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["model"] == analyzer.model
        assert call_args["temperature"] == 0.3
        assert len(call_args["messages"]) == 2
        assert call_args["messages"][0]["role"] == "system"
        assert call_args["messages"][0]["content"] == RATIONALE_PROMPT
    
    @patch('openai.OpenAI')
    def test_generate_rationale_api_error(self, mock_openai):
        """Test generate_rationale with API error."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Test exception")
        
        # Test the method
        analyzer = MetaLLMAnalyzer(api_key="test-key")
        components = [
            PromptComponent(type=ComponentType.INSTRUCTION, content="Test", position=1),
            PromptComponent(type=ComponentType.EXAMPLE, content="Test", position=2)
        ]
        
        task_analysis = {
            "detected_tasks": [TaskType.DEDUCTION],
            "detected_behaviors": [BehaviorType.PRECISION]
        }
        
        result = analyzer.generate_rationale(components, task_analysis, 85.5)
        
        # Verify fallback rationale returned
        assert "instruction, example" in result
        assert "85.5" in result
    
    def test_assemble_prompt(self):
        """Test assemble_prompt method."""
        analyzer = MetaLLMAnalyzer(api_key=None)
        
        # Test with ordered components
        components = [
            PromptComponent(type=ComponentType.INSTRUCTION, content="First", position=1),
            PromptComponent(type=ComponentType.EXAMPLE, content="Second", position=2)
        ]
        
        result = analyzer.assemble_prompt(components)
        assert result == "First\n\nSecond"
        
        # Test with unordered components
        components = [
            PromptComponent(type=ComponentType.EXAMPLE, content="Should be second", position=2),
            PromptComponent(type=ComponentType.INSTRUCTION, content="Should be first", position=1)
        ]
        
        result = analyzer.assemble_prompt(components)
        assert result == "Should be first\n\nShould be second"