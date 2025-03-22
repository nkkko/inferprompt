import pytest
from pydantic import ValidationError
from app.models.prompt import (
    ComponentType, TaskType, BehaviorType, 
    OptimizationRequest, PromptComponent, OptimizedPrompt
)

class TestComponentType:
    """Tests for ComponentType enum."""
    
    def test_enum_values(self):
        """Verify the enum values match expected strings."""
        assert ComponentType.INSTRUCTION.value == "instruction"
        assert ComponentType.CONTEXT.value == "context"
        assert ComponentType.EXAMPLE.value == "example"
        assert ComponentType.CONSTRAINT.value == "constraint"
        assert ComponentType.OUTPUT_FORMAT.value == "output_format"
    
    def test_enum_conversion(self):
        """Test conversion between string and enum."""
        assert ComponentType("instruction") == ComponentType.INSTRUCTION
        assert ComponentType.CONTEXT.value == "context"
        
        with pytest.raises(ValueError):
            ComponentType("invalid_type")

class TestTaskType:
    """Tests for TaskType enum."""
    
    def test_enum_values(self):
        """Verify the enum values match expected strings."""
        assert TaskType.DEDUCTION.value == "deduction"
        assert TaskType.INDUCTION.value == "induction"
        assert TaskType.ABDUCTION.value == "abduction"
        assert TaskType.COMPARISON.value == "comparison"
        assert TaskType.COUNTERFACTUAL.value == "counterfactual"
    
    def test_enum_conversion(self):
        """Test conversion between string and enum."""
        assert TaskType("deduction") == TaskType.DEDUCTION
        assert TaskType.INDUCTION.value == "induction"
        
        with pytest.raises(ValueError):
            TaskType("invalid_task")

class TestBehaviorType:
    """Tests for BehaviorType enum."""
    
    def test_enum_values(self):
        """Verify the enum values match expected strings."""
        assert BehaviorType.PRECISION.value == "precision"
        assert BehaviorType.CREATIVITY.value == "creativity"
        assert BehaviorType.STEP_BY_STEP.value == "step_by_step"
        assert BehaviorType.CONCISENESS.value == "conciseness"
        assert BehaviorType.ERROR_CHECKING.value == "error_checking"
    
    def test_enum_conversion(self):
        """Test conversion between string and enum."""
        assert BehaviorType("precision") == BehaviorType.PRECISION
        assert BehaviorType.STEP_BY_STEP.value == "step_by_step"
        
        with pytest.raises(ValueError):
            BehaviorType("invalid_behavior")

class TestOptimizationRequest:
    """Tests for OptimizationRequest model."""
    
    def test_valid_request(self):
        """Test creating a valid optimization request."""
        request = OptimizationRequest(
            user_prompt="Explain quantum computing",
            target_tasks=[TaskType.DEDUCTION],
            target_behaviors=[BehaviorType.PRECISION],
            target_model="gpt-4",
            domain="education"
        )
        
        assert request.user_prompt == "Explain quantum computing"
        assert request.target_tasks == [TaskType.DEDUCTION]
        assert request.target_behaviors == [BehaviorType.PRECISION]
        assert request.target_model == "gpt-4"
        assert request.domain == "education"
    
    def test_request_defaults(self):
        """Test default values in optimization request."""
        request = OptimizationRequest(user_prompt="Explain quantum computing")
        
        assert request.user_prompt == "Explain quantum computing"
        assert request.target_tasks == []
        assert request.target_behaviors == []
        assert request.target_model == "gpt-4"
        assert request.domain is None
    
    def test_invalid_request(self):
        """Test validation for invalid requests."""
        # Missing required field
        with pytest.raises(ValidationError):
            OptimizationRequest()
            
        # Invalid task type
        with pytest.raises(ValidationError):
            OptimizationRequest(
                user_prompt="Test",
                target_tasks=["invalid_task"]
            )
            
        # Invalid behavior type
        with pytest.raises(ValidationError):
            OptimizationRequest(
                user_prompt="Test",
                target_behaviors=["invalid_behavior"]
            )

class TestPromptComponent:
    """Tests for PromptComponent model."""
    
    def test_valid_component(self):
        """Test creating a valid prompt component."""
        component = PromptComponent(
            type=ComponentType.INSTRUCTION,
            content="Follow these instructions",
            position=1
        )
        
        assert component.type == ComponentType.INSTRUCTION
        assert component.content == "Follow these instructions"
        assert component.position == 1
    
    def test_invalid_component(self):
        """Test validation for invalid components."""
        # Missing required fields
        with pytest.raises(ValidationError):
            PromptComponent()
            
        with pytest.raises(ValidationError):
            PromptComponent(
                type=ComponentType.INSTRUCTION,
                content="Test"
            )
            
        with pytest.raises(ValidationError):
            PromptComponent(
                type=ComponentType.INSTRUCTION,
                position=1
            )
            
        with pytest.raises(ValidationError):
            PromptComponent(
                content="Test",
                position=1
            )

class TestOptimizedPrompt:
    """Tests for OptimizedPrompt model."""
    
    def test_valid_optimized_prompt(self):
        """Test creating a valid optimized prompt."""
        components = [
            PromptComponent(
                type=ComponentType.INSTRUCTION,
                content="Follow these instructions",
                position=1
            ),
            PromptComponent(
                type=ComponentType.EXAMPLE,
                content="Here's an example",
                position=2
            )
        ]
        
        prompt = OptimizedPrompt(
            components=components,
            full_prompt="Follow these instructions\n\nHere's an example",
            rationale="This structure is optimal",
            effectiveness_score=85.5
        )
        
        assert prompt.components == components
        assert prompt.full_prompt == "Follow these instructions\n\nHere's an example"
        assert prompt.rationale == "This structure is optimal"
        assert prompt.effectiveness_score == 85.5
    
    def test_invalid_optimized_prompt(self):
        """Test validation for invalid optimized prompts."""
        components = [
            PromptComponent(
                type=ComponentType.INSTRUCTION,
                content="Follow these instructions",
                position=1
            )
        ]
        
        # Missing required fields
        with pytest.raises(ValidationError):
            OptimizedPrompt()
            
        with pytest.raises(ValidationError):
            OptimizedPrompt(
                components=components,
                full_prompt="Test",
                rationale="Test"
            )
            
        with pytest.raises(ValidationError):
            OptimizedPrompt(
                components=components,
                full_prompt="Test",
                effectiveness_score=85.5
            )
            
        with pytest.raises(ValidationError):
            OptimizedPrompt(
                components=components,
                rationale="Test",
                effectiveness_score=85.5
            )