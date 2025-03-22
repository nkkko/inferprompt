import pytest
from unittest.mock import patch, MagicMock, call
import datetime
from app.services.prompt_optimizer import PromptOptimizer, optimization_cache
from app.models.prompt import (
    OptimizationRequest, OptimizedPrompt, PromptComponent,
    ComponentType, TaskType, BehaviorType
)

class TestPromptOptimizer:
    """Tests for PromptOptimizer class."""
    
    def test_init(self, mock_meta_llm, asp_engine):
        """Test initialization."""
        optimizer = PromptOptimizer(api_key="test-key")
        
        assert optimizer.meta_llm.api_key == "test-key"
        assert optimizer.asp_engine is not None
    
    def test_generate_cache_key(self):
        """Test cache key generation."""
        optimizer = PromptOptimizer()
        
        # Test basic key generation
        key = optimizer._generate_cache_key(
            target_tasks=[TaskType.DEDUCTION],
            target_behaviors=[BehaviorType.PRECISION],
            target_model="gpt-4",
            domain="education"
        )
        
        assert "deduction" in key
        assert "precision" in key
        assert "gpt-4" in key
        assert "education" in key
        
        # Test with multiple values and sorting
        key = optimizer._generate_cache_key(
            target_tasks=[TaskType.COMPARISON, TaskType.DEDUCTION],
            target_behaviors=[BehaviorType.STEP_BY_STEP, BehaviorType.PRECISION],
            target_model="gpt-4",
            domain=None
        )
        
        assert "comparison,deduction" in key or "deduction,comparison" in key
        assert "precision,step_by_step" in key or "step_by_step,precision" in key
        assert "none" in key.lower()
    
    def test_optimize_success(self, mocker, optimizer, sample_prompt_data):
        """Test successful optimization."""
        # Mock meta_llm methods
        task_analysis = {
            "detected_tasks": [TaskType.DEDUCTION],
            "detected_behaviors": [BehaviorType.PRECISION],
            "domain_hint": None
        }
        optimizer.meta_llm.analyze_task = mocker.MagicMock(return_value=task_analysis)
        optimizer.meta_llm.generate_component_content = mocker.MagicMock(return_value="Test content")
        optimizer.meta_llm.assemble_prompt = mocker.MagicMock(return_value="Full prompt text")
        optimizer.meta_llm.generate_rationale = mocker.MagicMock(return_value="Optimization rationale")
        
        # Mock asp_engine
        components = [
            PromptComponent(type=ComponentType.INSTRUCTION, content="", position=1),
            PromptComponent(type=ComponentType.EXAMPLE, content="", position=2)
        ]
        optimizer.asp_engine.solve = mocker.MagicMock(return_value=(components, 85.5))
        
        # Mock _save_to_db
        optimizer._save_to_db = mocker.MagicMock(return_value=1)
        
        # Create request
        request = OptimizationRequest(**sample_prompt_data)
        
        # Test optimize method
        result = optimizer.optimize(request)
        
        # Verify result
        assert isinstance(result, OptimizedPrompt)
        assert len(result.components) == 2
        assert result.full_prompt == "Full prompt text"
        assert result.rationale == "Optimization rationale"
        assert result.effectiveness_score == 85.5
        
        # Verify method calls
        optimizer.meta_llm.analyze_task.assert_called_once_with(request.user_prompt)
        optimizer.asp_engine.solve.assert_called_once()
        optimizer.meta_llm.generate_component_content.call_count == 2
        optimizer.meta_llm.assemble_prompt.assert_called_once()
        optimizer.meta_llm.generate_rationale.assert_called_once()
        optimizer._save_to_db.assert_called_once()
    
    def test_optimize_with_cache(self, mocker, optimizer, sample_prompt_data):
        """Test optimization with cache hit."""
        # Mock meta_llm methods
        task_analysis = {
            "detected_tasks": [TaskType.DEDUCTION],
            "detected_behaviors": [BehaviorType.PRECISION],
            "domain_hint": None
        }
        optimizer.meta_llm.analyze_task = mocker.MagicMock(return_value=task_analysis)
        optimizer.meta_llm.generate_component_content = mocker.MagicMock(return_value="Test content")
        optimizer.meta_llm.assemble_prompt = mocker.MagicMock(return_value="Full prompt text")
        optimizer.meta_llm.generate_rationale = mocker.MagicMock(return_value="Optimization rationale")
        
        # Mock _save_to_db
        optimizer._save_to_db = mocker.MagicMock(return_value=1)
        
        # Create request
        request = OptimizationRequest(**sample_prompt_data)
        
        # Add to cache
        cache_key = optimizer._generate_cache_key(
            request.target_tasks,
            request.target_behaviors,
            request.target_model,
            request.domain
        )
        
        cached_components = [
            PromptComponent(type=ComponentType.INSTRUCTION, content="", position=1),
            PromptComponent(type=ComponentType.EXAMPLE, content="", position=2)
        ]
        optimization_cache[cache_key] = (cached_components, 85.5)
        
        # Test optimize method
        result = optimizer.optimize(request)
        
        # Verify result
        assert isinstance(result, OptimizedPrompt)
        assert len(result.components) == 2
        
        # Verify method calls
        optimizer.meta_llm.analyze_task.assert_called_once_with(request.user_prompt)
        optimizer.asp_engine.solve.assert_not_called()
        optimizer.meta_llm.generate_component_content.call_count == 2
        
        # Clean up cache
        optimization_cache.clear()
    
    def test_optimize_exception(self, mocker, optimizer, sample_prompt_data):
        """Test optimization with exception."""
        # Mock meta_llm to raise exception
        optimizer.meta_llm.analyze_task = mocker.MagicMock(side_effect=Exception("Test exception"))
        
        # Create request
        request = OptimizationRequest(**sample_prompt_data)
        
        # Test optimize method
        result = optimizer.optimize(request)
        
        # Verify fallback result
        assert isinstance(result, OptimizedPrompt)
        assert len(result.components) == 1
        assert result.components[0].type == ComponentType.INSTRUCTION
        assert request.user_prompt in result.components[0].content
        assert "Fallback" in result.rationale
        assert result.effectiveness_score == 50.0
    
    @patch('app.models.database.SessionLocal')
    def test_save_to_db(self, mock_session_local, optimizer):
        """Test saving to database."""
        # Setup mock
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.flush = MagicMock()
        mock_db_prompt = MagicMock()
        mock_db_prompt.id = 1
        mock_db.add = MagicMock(return_value=None)
        
        # Test method with patched datetime
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.datetime(2023, 1, 1, 12, 0, 0)
            
            # Setup objects to save
            components = [
                PromptComponent(type=ComponentType.INSTRUCTION, content="Test", position=1),
                PromptComponent(type=ComponentType.EXAMPLE, content="Test", position=2)
            ]
            
            # Patch the database add method to set the id of the prompt
            def side_effect(obj):
                if hasattr(obj, 'id') and obj.id is None:
                    obj.id = 1
            
            mock_db.add.side_effect = side_effect
            
            # Call the method
            result = optimizer._save_to_db(
                user_prompt="Test prompt",
                optimized_prompt="Optimized test prompt",
                components=components,
                target_model="gpt-4",
                effectiveness_score=85.5,
                rationale="Test rationale"
            )
            
            # Verify result
            assert result == 1
            
            # Verify db calls
            assert mock_db.add.call_count == 3  # 1 prompt + 2 components
            mock_db.flush.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.close.assert_called_once()
    
    @patch('app.models.database.SessionLocal')
    def test_save_to_db_exception(self, mock_session_local, optimizer):
        """Test saving to database with exception."""
        # Setup mock to raise exception
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Make the first add call raise an exception
        # This ensures the exception happens at the right time
        def mock_add_with_exception(obj):
            raise Exception("Test exception")
            
        mock_db.add = MagicMock(side_effect=mock_add_with_exception)
        
        # Setup objects to save
        components = [
            PromptComponent(type=ComponentType.INSTRUCTION, content="Test", position=1)
        ]
        
        # Call the method
        result = optimizer._save_to_db(
            user_prompt="Test prompt",
            optimized_prompt="Optimized test prompt",
            components=components,
            target_model="gpt-4",
            effectiveness_score=85.5,
            rationale="Test rationale"
        )
        
        # Verify result
        assert result is None
        
        # Verify db calls
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
    
    def test_provide_feedback_success(self, mocker, optimizer):
        """Test successful feedback provision."""
        # Mock asp_engine
        optimizer.asp_engine.update_efficacy = mocker.MagicMock()
        
        # Test method
        component = ComponentType.INSTRUCTION
        behavior = BehaviorType.PRECISION
        effectiveness = 0.9
        
        # Setup cache with test data
        optimization_cache["test"] = ("data", 85.5)
        
        result = optimizer.provide_feedback(component, behavior, effectiveness)
        
        # Verify result
        assert result is True
        
        # Verify calls
        optimizer.asp_engine.update_efficacy.assert_called_once_with(component, behavior, effectiveness)
        
        # Verify cache cleared
        assert len(optimization_cache) == 0
    
    def test_provide_feedback_exception(self, mocker, optimizer):
        """Test feedback provision with exception."""
        # Mock asp_engine to raise exception
        optimizer.asp_engine.update_efficacy = mocker.MagicMock(side_effect=Exception("Test exception"))
        
        # Test method
        component = ComponentType.INSTRUCTION
        behavior = BehaviorType.PRECISION
        effectiveness = 0.9
        
        result = optimizer.provide_feedback(component, behavior, effectiveness)
        
        # Verify result
        assert result is False
        
        # Verify calls
        optimizer.asp_engine.update_efficacy.assert_called_once_with(component, behavior, effectiveness)