from enum import Enum
from typing import List, Dict, Optional, Union, Any
from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    INSTRUCTION = "instruction"
    CONTEXT = "context"
    EXAMPLE = "example"
    CONSTRAINT = "constraint"
    OUTPUT_FORMAT = "output_format"


class TaskType(str, Enum):
    DEDUCTION = "deduction"
    INDUCTION = "induction"
    ABDUCTION = "abduction"
    COMPARISON = "comparison"
    COUNTERFACTUAL = "counterfactual"


class BehaviorType(str, Enum):
    PRECISION = "precision"
    CREATIVITY = "creativity"
    STEP_BY_STEP = "step_by_step"
    CONCISENESS = "conciseness"
    ERROR_CHECKING = "error_checking"


class OptimizationRequest(BaseModel):
    user_prompt: str = Field(..., description="The original user prompt")
    target_tasks: List[TaskType] = Field(default=[], description="Target reasoning tasks")
    target_behaviors: List[BehaviorType] = Field(default=[], description="Desired output behaviors")
    target_model: str = Field(default="gpt-4", description="Target LLM to optimize for")
    domain: Optional[str] = Field(None, description="Specific domain context")


class PromptComponent(BaseModel):
    type: ComponentType
    content: str
    position: int


class OptimizedPrompt(BaseModel):
    components: List[PromptComponent] = Field(..., description="Ordered prompt components")
    full_prompt: str = Field(..., description="Assembled prompt text")
    rationale: str = Field(..., description="Explanation of optimization choices")
    effectiveness_score: float = Field(..., description="Predicted effectiveness score")
