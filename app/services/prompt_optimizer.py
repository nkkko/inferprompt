from typing import List, Dict, Any, Optional
import datetime
from app.models.prompt import (
    TaskType, BehaviorType, OptimizationRequest, 
    PromptComponent, OptimizedPrompt, ComponentType
)
from app.core.asp_engine import ASPEngine
from app.services.meta_llm import MetaLLMAnalyzer
from app.models.database import (
    SessionLocal, OptimizedPromptDB, PromptComponentDB
)


class PromptOptimizer:
    def __init__(self, api_key: Optional[str] = None):
        self.asp_engine = ASPEngine()
        self.meta_llm = MetaLLMAnalyzer(api_key=api_key)
    
    def optimize(self, request: OptimizationRequest) -> OptimizedPrompt:
        """Optimize a prompt based on the request"""
        # Step 1: Analyze the task using Meta-LLM
        task_analysis = self.meta_llm.analyze_task(request.user_prompt)
        
        # Use provided tasks/behaviors or detected ones if not specified
        target_tasks = request.target_tasks or task_analysis["detected_tasks"]
        target_behaviors = request.target_behaviors or task_analysis["detected_behaviors"]
        domain = request.domain or task_analysis.get("domain_hint")
        
        # Step 2: Use ASP Engine to get optimal prompt structure
        components, effectiveness_score = self.asp_engine.solve(
            target_tasks=target_tasks,
            target_behaviors=target_behaviors,
            target_model=request.target_model,
            domain=domain
        )
        
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
        self._save_to_db(
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
        
    def _save_to_db(
        self,
        user_prompt: str,
        optimized_prompt: str,
        components: List[PromptComponent],
        target_model: str,
        effectiveness_score: float,
        rationale: str
    ) -> None:
        """Save optimized prompt to database"""
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
        except Exception as e:
            db.rollback()
            print(f"Error saving to database: {str(e)}")
        finally:
            db.close()
    
    def provide_feedback(self, 
                        component_type: ComponentType, 
                        task_or_behavior: TaskType | BehaviorType, 
                        effectiveness: float):
        """Update the ASP engine with feedback on component effectiveness"""
        self.asp_engine.update_efficacy(component_type, task_or_behavior, effectiveness)
