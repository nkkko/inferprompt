from typing import List, Dict, Any, Optional, cast
import logging
import os
import json
from openai import OpenAI, OpenAIError
from app.models.prompt import TaskType, BehaviorType, OptimizationRequest, PromptComponent, OptimizedPrompt

# Configure logging
logger = logging.getLogger(__name__)

# Define system prompts for each task
ANALYSIS_PROMPT = """Analyze the following user prompt to identify:
1. The primary reasoning tasks required (deduction, induction, abduction, comparison, counterfactual)
2. The desired output behaviors (precision, creativity, step_by_step, conciseness, error_checking)
3. The domain context if apparent (e.g., legal, medical, education, code, etc.)

Respond with a JSON object containing these fields."""

COMPONENT_GENERATION_PROMPTS = {
    "instruction": """Generate clear instructions for the LLM based on the user's prompt.
Focus on what the LLM should do, not how it should do it.
The instructions should be clear, concise, and focused on the task at hand.""",
    
    "context": """Generate relevant context information that would help the LLM respond correctly.
This should provide background information, definitions, or key concepts that the LLM needs to know.""",
    
    "example": """Generate an example that demonstrates the type of output desired.
The example should illustrate the expected format, style, depth, and approach.""",
    
    "constraint": """Generate constraints that the LLM should follow when responding.
These should include limitations, rules, or guidelines that shape the response.""",
    
    "output_format": """Generate a specific output format structure for the LLM to follow.
This should detail how the response should be organized, what sections to include, etc."""
}

RATIONALE_PROMPT = """Explain why the chosen prompt structure is optimal for the given task.
Reference the specific reasoning tasks, behaviors, and domain context.
Explain how each component contributes to the overall effectiveness."""


class MetaLLMAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI or other LLM provider"""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        self.use_mock = not self.api_key  # Use mock responses if no API key
        
        # Initialize OpenAI client if API key is available
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"Initialized OpenAI client with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                self.use_mock = True
        else:
            logger.warning("No API key provided, using mock responses")
            self.use_mock = True
    
    def analyze_task(self, user_prompt: str) -> Dict[str, Any]:
        """Analyze the user's task to determine optimal reasoning approach"""
        if self.use_mock:
            # Return mock analysis for demo/testing
            return {
                "detected_tasks": [TaskType.DEDUCTION],
                "detected_behaviors": [BehaviorType.PRECISION, BehaviorType.STEP_BY_STEP],
                "domain_hint": None,
            }
        
        try:
            # Call the LLM API to analyze the task
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ANALYSIS_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            # Parse the response
            analysis_text = response.choices[0].message.content
            analysis = json.loads(analysis_text)
            
            # Convert string lists to enum lists
            detected_tasks = [TaskType(task) for task in analysis.get("reasoning_tasks", [])]
            detected_behaviors = [BehaviorType(behavior) for behavior in analysis.get("output_behaviors", [])]
            
            return {
                "detected_tasks": detected_tasks or [TaskType.DEDUCTION],  # Default if empty
                "detected_behaviors": detected_behaviors or [BehaviorType.PRECISION],  # Default if empty
                "domain_hint": analysis.get("domain"),
            }
            
        except (OpenAIError, json.JSONDecodeError, ValueError) as e:
            # Log and return defaults on error
            logger.error(f"Error analyzing task: {str(e)}")
            return {
                "detected_tasks": [TaskType.DEDUCTION],
                "detected_behaviors": [BehaviorType.PRECISION, BehaviorType.STEP_BY_STEP],
                "domain_hint": None,
            }
    
    def generate_component_content(self, component_type: str, task_analysis: Dict[str, Any], 
                                 original_prompt: str) -> str:
        """Generate content for a specific prompt component"""
        if self.use_mock:
            # Return mock content for demo/testing
            if component_type == "instruction":
                return f"Follow these instructions carefully to answer the query: {original_prompt}"
            elif component_type == "context":
                return "Consider all relevant information and constraints before responding."
            elif component_type == "example":
                return "Here's an example of a good response: [Example response that demonstrates desired qualities]"
            elif component_type == "constraint":
                return "Important: Your response must be factual, precise, and include step-by-step reasoning."
            elif component_type == "output_format":
                return "Format your response as follows: 1) Initial analysis, 2) Step-by-step reasoning, 3) Final answer"
            else:
                return "[Content for this component type]"
        
        try:
            # Construct a system prompt for the specific component type
            system_prompt = COMPONENT_GENERATION_PROMPTS.get(component_type, 
                                                          "Generate appropriate content for this prompt component.")
            
            # Format task information for the component
            task_info = {
                "reasoning_tasks": [t.value for t in task_analysis["detected_tasks"]],
                "behaviors": [b.value for b in task_analysis["detected_behaviors"]],
                "domain": task_analysis.get("domain_hint", "general")
            }
            
            # Call the LLM API to generate component content
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Original prompt: {original_prompt}\n\nTask analysis: {json.dumps(task_info)}"}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except OpenAIError as e:
            # Log and return fallback content on error
            logger.error(f"Error generating {component_type} content: {str(e)}")
            return f"[{component_type.upper()} CONTENT FOR: {original_prompt}]"

    def generate_rationale(self, components: List[PromptComponent], 
                          task_analysis: Dict[str, Any], 
                          effectiveness_score: float) -> str:
        """Generate an explanation for why this prompt structure was chosen"""
        if self.use_mock:
            # Return mock rationale for demo/testing
            ordered_types = [comp.type.value for comp in components]
            return (
                f"This prompt structure (ordering: {', '.join(ordered_types)}) was chosen because it optimizes for "
                f"the detected reasoning tasks and desired behaviors. The effectiveness score is {effectiveness_score:.2f}."
            )
            
        try:
            # Prepare component information
            components_info = [{"type": comp.type.value, "position": comp.position} for comp in components]
            
            # Format task information
            task_info = {
                "reasoning_tasks": [t.value for t in task_analysis["detected_tasks"]],
                "behaviors": [b.value for b in task_analysis["detected_behaviors"]],
                "domain": task_analysis.get("domain_hint", "general"),
                "effectiveness_score": effectiveness_score
            }
            
            # Call the LLM API to generate rationale
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": RATIONALE_PROMPT},
                    {"role": "user", "content": f"Components: {json.dumps(components_info)}\n\nTask analysis: {json.dumps(task_info)}"}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except OpenAIError as e:
            # Log and return fallback rationale on error
            logger.error(f"Error generating rationale: {str(e)}")
            ordered_types = [comp.type.value for comp in components]
            return (
                f"This prompt structure (ordering: {', '.join(ordered_types)}) was chosen to optimize for "
                f"the detected reasoning tasks and behaviors. Effectiveness score: {effectiveness_score:.2f}."
            )

    def assemble_prompt(self, components: List[PromptComponent]) -> str:
        """Assemble the full prompt from components"""
        # Sort components by position to ensure correct order
        sorted_components = sorted(components, key=lambda x: x.position)
        
        # Join with double newlines for clear separation
        return "\n\n".join([comp.content for comp in sorted_components])
