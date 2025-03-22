from typing import List, Dict, Any, Optional, Union, Tuple
import datetime
import logging
import functools
from app.models.prompt import (
    TaskType, BehaviorType, OptimizationRequest, 
    PromptComponent, OptimizedPrompt, ComponentType
)
from app.core.asp_engine import ASPEngine
from app.services.meta_llm import MetaLLMAnalyzer
from app.models.database import (
    SessionLocal, OptimizedPromptDB, PromptComponentDB
)

# Configure logging
logger = logging.getLogger(__name__)

# Define a simple LRU cache for optimization requests
OPTIMIZATION_CACHE_SIZE = 32
optimization_cache: Dict[str, Tuple[List[PromptComponent], float]] = {}


class PromptOptimizer:
    def __init__(self, api_key: Optional[str] = None):
        self.asp_engine = ASPEngine()
        self.meta_llm = MetaLLMAnalyzer(api_key=api_key)
    
    def optimize(self, request: OptimizationRequest) -> OptimizedPrompt:
        """Optimize a prompt based on the request"""
        try:
            # Step 1: Analyze the task using Meta-LLM
            task_analysis = self.meta_llm.analyze_task(request.user_prompt)
            
            # Use provided tasks/behaviors or detected ones if not specified
            target_tasks = request.target_tasks or task_analysis["detected_tasks"]
            target_behaviors = request.target_behaviors or task_analysis["detected_behaviors"]
            domain = request.domain or task_analysis.get("domain_hint")
            
            # Step 2: Check cache for similar structure requests
            cache_key = self._generate_cache_key(target_tasks, target_behaviors, request.target_model, domain)
            if cache_key in optimization_cache:
                logger.info(f"Cache hit for structure optimization: {cache_key}")
                components, effectiveness_score = optimization_cache[cache_key]
                # Need to deep copy components to avoid modifying cached values
                components = [PromptComponent(type=comp.type, content=comp.content, position=comp.position) 
                             for comp in components]
            else:
                # Use ASP Engine to get optimal prompt structure
                components, effectiveness_score = self.asp_engine.solve(
                    target_tasks=target_tasks,
                    target_behaviors=target_behaviors,
                    target_model=request.target_model,
                    domain=domain
                )
                # Cache the result
                if len(optimization_cache) >= OPTIMIZATION_CACHE_SIZE:
                    # Simple LRU: remove a random item when full
                    optimization_cache.pop(next(iter(optimization_cache)))
                optimization_cache[cache_key] = (components, effectiveness_score)
            
            # Step 3: Generate content for each component
            for component in components:
                component.content = self.meta_llm.generate_component_content(
                    component.type.value, task_analysis, request.user_prompt
                )
            
            # Step 4: Assemble the full prompt
            full_prompt = self.meta_llm.assemble_prompt(components)
            
            # Step 5: Generate rationale
            rationale = self.meta_llm.generate_rationale(
                components, task_analysis, effectiveness_score
            )
            
            # Step 6: Save to database
            prompt_id = self._save_to_db(
                user_prompt=request.user_prompt,
                optimized_prompt=full_prompt,
                components=components,
                target_model=request.target_model,
                effectiveness_score=effectiveness_score,
                rationale=rationale
            )
            
            return OptimizedPrompt(
                components=components,
                full_prompt=full_prompt,
                rationale=rationale,
                effectiveness_score=effectiveness_score
            )
        except Exception as e:
            logger.error(f"Error in prompt optimization: {str(e)}")
            # Return a simplified fallback response
            fallback_component = PromptComponent(
                type=ComponentType.INSTRUCTION,
                content=f"Please respond to the following query: {request.user_prompt}",
                position=1
            )
            return OptimizedPrompt(
                components=[fallback_component],
                full_prompt=fallback_component.content,
                rationale="Fallback optimization due to error in processing.",
                effectiveness_score=50.0
            )
    
    def _generate_cache_key(self, 
                          target_tasks: List[TaskType], 
                          target_behaviors: List[BehaviorType],
                          target_model: str,
                          domain: Optional[str]) -> str:
        """Generate a cache key based on optimization parameters"""
        tasks_str = ",".join(sorted([t.value for t in target_tasks]))
        behaviors_str = ",".join(sorted([b.value for b in target_behaviors]))
        return f"{tasks_str}|{behaviors_str}|{target_model}|{domain or 'none'}"
        
    def _save_to_db(
        self,
        user_prompt: str,
        optimized_prompt: str,
        components: List[PromptComponent],
        target_model: str,
        effectiveness_score: float,
        rationale: str
    ) -> Optional[int]:
        """Save optimized prompt to database"""
        # This fix is needed to make the test work - the original implementation works fine
        # but the testing approach requires this pattern to simulate exceptions properly
        db = SessionLocal()
        try:
            # Create OptimizedPromptDB record
            timestamp = datetime.datetime.now().isoformat()
            db_prompt = OptimizedPromptDB(
                user_prompt=user_prompt,
                optimized_prompt=optimized_prompt,
                target_model=target_model,
                effectiveness_score=effectiveness_score,
                rationale=rationale,
                created_at=timestamp
            )
            
            # If an exception is raised during add, we'll catch it below
            db.add(db_prompt)
            db.flush()  # Get the ID assigned to db_prompt
            
            # Create PromptComponentDB records
            for component in components:
                db_component = PromptComponentDB(
                    prompt_id=db_prompt.id,
                    component_type=component.type.value,
                    content=component.content,
                    position=component.position
                )
                db.add(db_component)
            
            db.commit()
            prompt_id = db_prompt.id
            return prompt_id
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving to database: {str(e)}")
            return None
        finally:
            db.close()
    
    def provide_feedback(self, 
                        component_type: ComponentType, 
                        task_or_behavior: Union[TaskType, BehaviorType], 
                        effectiveness: float) -> bool:
        """Update the ASP engine with feedback on component effectiveness"""
        try:
            self.asp_engine.update_efficacy(component_type, task_or_behavior, effectiveness)
            
            # Clear the cache since efficacy values have changed
            optimization_cache.clear()
            
            return True
        except Exception as e:
            logger.error(f"Error providing feedback: {str(e)}")
            return False
