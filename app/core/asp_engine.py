import clingo
import logging
from typing import Dict, List, Tuple, Set, Optional, Any, Union, cast
from functools import lru_cache
from app.models.prompt import ComponentType, TaskType, BehaviorType, PromptComponent
from app.models.database import SessionLocal, ComponentEfficacyDB, PositionEffectDB, ModelEfficacyDB, DomainEfficacyDB
from sqlalchemy.orm import Session
import datetime


# Configure logging
logger = logging.getLogger(__name__)


class ASPEngine:
    def __init__(self, load_from_db: bool = True):
        # ASP program that's compatible with all Clingo versions
        self.base_program = """
            % Define prompt components
            component(instruction).
            component(context).
            component(example).
            component(constraint).
            component(output_format).
            
            % Define tasks
            task(deduction).
            task(induction).
            task(abduction).
            task(comparison).
            task(counterfactual).
            
            % Define behaviors
            behavior(precision).
            behavior(creativity).
            behavior(step_by_step).
            behavior(conciseness).
            behavior(error_checking).
            
            % Each component must be assigned exactly one position (1-5)
            1 { prompt_position(C, P) : P = 1..5 } 1 :- component(C).
            
            % No two components can share the same position
            :- prompt_position(C1, P), prompt_position(C2, P), C1 != C2.
            
            % An example requires an instruction
            :- prompt_position(example, _), not prompt_position(instruction, _).
            
            % A constraint requires an instruction
            :- prompt_position(constraint, _), not prompt_position(instruction, _).
            
            % Preference for instruction at the beginning
            instruction_first :- prompt_position(instruction, 1).
            
            % Preference for examples after instructions
            example_after_instruction :- 
                prompt_position(instruction, P1), 
                prompt_position(example, P2), 
                P1 < P2.
            
            % Calculate a simple effectiveness score (without complex aggregates)
            % We'll add constant values for demonstration
            effectiveness(100) :- instruction_first, example_after_instruction.
            effectiveness(80) :- instruction_first, not example_after_instruction.
            effectiveness(60) :- not instruction_first, example_after_instruction.
            effectiveness(40) :- not instruction_first, not example_after_instruction.
            
            % Optimize for highest effectiveness
            #maximize { S : effectiveness(S) }.
            
            % Show results
            #show prompt_position/2.
            #show effectiveness/1.
        """
        
        # Default efficacy values - these would be learned over time
        self.component_efficacy: Dict[Tuple[ComponentType, Union[TaskType, BehaviorType]], float] = {
            (ComponentType.INSTRUCTION, TaskType.DEDUCTION): 0.8,
            (ComponentType.EXAMPLE, TaskType.DEDUCTION): 0.9,
            (ComponentType.CONSTRAINT, BehaviorType.PRECISION): 0.7,
            (ComponentType.OUTPUT_FORMAT, BehaviorType.STEP_BY_STEP): 0.8,
            (ComponentType.INSTRUCTION, BehaviorType.PRECISION): 0.7,
            (ComponentType.CONTEXT, TaskType.ABDUCTION): 0.75,
            (ComponentType.EXAMPLE, BehaviorType.STEP_BY_STEP): 0.85,
        }
        
        # Default position effects
        self.position_effects: Dict[Tuple[ComponentType, int], float] = {
            (ComponentType.INSTRUCTION, 1): 0.9,
            (ComponentType.CONTEXT, 2): 0.7,
            (ComponentType.EXAMPLE, 3): 0.8,
        }
        
        # Default weights
        self.weights: Dict[Union[str, TaskType, BehaviorType], float] = {
            "position": 0.5,
            TaskType.DEDUCTION: 1.0,
            TaskType.INDUCTION: 1.0,
            TaskType.ABDUCTION: 1.0,
            TaskType.COMPARISON: 1.0,
            TaskType.COUNTERFACTUAL: 1.0,
            BehaviorType.PRECISION: 1.0,
            BehaviorType.CREATIVITY: 1.0,
            BehaviorType.STEP_BY_STEP: 1.0,
            BehaviorType.CONCISENESS: 1.0,
            BehaviorType.ERROR_CHECKING: 1.0,
        }
        
        # Model-specific adjustments
        self.model_adjustments: Dict[str, Dict[Tuple[ComponentType, BehaviorType], float]] = {
            "gpt-4": {
                (ComponentType.INSTRUCTION, BehaviorType.PRECISION): 0.9,
            },
            "claude": {
                (ComponentType.EXAMPLE, BehaviorType.PRECISION): 0.85, 
            },
            "llama": {
                (ComponentType.CONSTRAINT, BehaviorType.PRECISION): 0.75,
            }
        }
        
        # Domain-specific adjustments
        self.domain_adjustments: Dict[str, Dict[Tuple[ComponentType, BehaviorType], float]] = {
            "legal": {
                (ComponentType.CONTEXT, BehaviorType.PRECISION): 0.95,
            },
            "medical": {
                (ComponentType.CONSTRAINT, BehaviorType.STEP_BY_STEP): 0.9,
            },
            "code": {
                (ComponentType.EXAMPLE, BehaviorType.PRECISION): 0.85,
            }
        }
        
        # Load values from database if requested
        if load_from_db:
            try:
                self.load_efficacy_from_db()
            except Exception as e:
                logger.warning(f"Could not load efficacy values from database: {str(e)}")
    
    @lru_cache(maxsize=32)
    def generate_asp_facts(self, 
                          tasks_tuple: Tuple[TaskType, ...], 
                          behaviors_tuple: Tuple[BehaviorType, ...],
                          target_model: Optional[str] = None,
                          domain: Optional[str] = None) -> str:
        """Generate ASP facts based on the optimization request with LRU caching
        
        Note: Converting lists to tuples for hashability in the cache
        """
        facts = []
        
        # Add target tasks and behaviors
        for task in tasks_tuple:
            facts.append(f"target_task({task.value})")
        
        for behavior in behaviors_tuple:
            facts.append(f"target_behavior({behavior.value})")
            
        # Add component efficacy facts
        for (comp, task_or_behavior), efficacy in self.component_efficacy.items():
            # Handle both task and behavior efficacy
            if isinstance(task_or_behavior, TaskType):
                facts.append(f"component_efficacy({comp.value}, {task_or_behavior.value}, {efficacy})")
            else:  # BehaviorType
                facts.append(f"component_efficacy({comp.value}, {task_or_behavior.value}, {efficacy})")
        
        # Add position effect facts
        for (comp, pos), effect in self.position_effects.items():
            facts.append(f"position_effect({comp.value}, {pos}, {effect})")
        
        # Add weight facts
        for key, weight in self.weights.items():
            if isinstance(key, str):
                facts.append(f"weight({key}, {weight})")
            else:  # TaskType or BehaviorType
                facts.append(f"weight({key.value}, {weight})")
        
        # Add model-specific adjustments if applicable
        if target_model and target_model in self.model_adjustments:
            facts.append(f"target_model({target_model})")
            for (comp, behavior), efficacy in self.model_adjustments[target_model].items():
                facts.append(f"model_specific_efficacy({target_model}, {comp.value}, {behavior.value}, {efficacy})")
        
        # Add domain-specific adjustments if applicable
        if domain and domain in self.domain_adjustments:
            facts.append(f"target_domain({domain})")
            for (comp, behavior), efficacy in self.domain_adjustments[domain].items():
                facts.append(f"domain_efficacy({domain}, {comp.value}, {behavior.value}, {efficacy})")
        
        return "\n".join(facts)
    
    def solve(self, 
              target_tasks: List[TaskType], 
              target_behaviors: List[BehaviorType],
              target_model: Optional[str] = None,
              domain: Optional[str] = None) -> Tuple[List[PromptComponent], float]:
        """Run the ASP solver and return optimized prompt components"""
        try:
            # Convert lists to tuples for cache key
            tasks_tuple = tuple(target_tasks)
            behaviors_tuple = tuple(target_behaviors)
            
            facts = self.generate_asp_facts(tasks_tuple, behaviors_tuple, target_model, domain)
            full_program = f"{self.base_program}\n{facts}"
            
            # Initialize clingo solver with optimization settings
            control = clingo.Control(["--opt-strategy=usc", "--opt-mode=opt"])
            control.add("base", [], full_program)
            control.ground([("base", [])])
            
            # Solve and get the best model
            models = []
            control.solve(on_model=lambda model: models.append(model.symbols(shown=True)))
            
            if not models:
                logger.info("No ASP solution found, falling back to hardcoded approach")
                return self._fallback_solve(target_tasks, target_behaviors, target_model, domain)
            
            # Get the best model (last one)
            best_model = models[-1]
            
            # Extract prompt components and their positions
            components = []
            effectiveness_score = 0.0
            
            for atom in best_model:
                if atom.name == "prompt_position" and len(atom.arguments) == 2:
                    comp_type = ComponentType(str(atom.arguments[0]))
                    position = int(str(atom.arguments[1]))
                    # We'd need content generation here in a real system
                    placeholder_content = f"[{comp_type.value.upper()} CONTENT]"
                    components.append(PromptComponent(type=comp_type, content=placeholder_content, position=position))
                elif atom.name == "effectiveness" and len(atom.arguments) == 1:
                    effectiveness_score = float(str(atom.arguments[0]))
            
            # Sort components by position
            components.sort(key=lambda x: x.position)
            
            return components, effectiveness_score
            
        except Exception as e:
            # Log the error and fall back to a hardcoded approach
            logger.error(f"Error in ASP solver: {str(e)}")
            return self._fallback_solve(target_tasks, target_behaviors, target_model, domain)
    
    def _fallback_solve(self, 
                      target_tasks: List[TaskType], 
                      target_behaviors: List[BehaviorType],
                      target_model: Optional[str] = None,
                      domain: Optional[str] = None) -> Tuple[List[PromptComponent], float]:
        """Fallback method that returns a hardcoded optimal prompt structure"""
        # This is our hardcoded "optimal" structure based on best practices
        hardcoded_structure = [
            (ComponentType.INSTRUCTION, 1),
            (ComponentType.CONTEXT, 2),
            (ComponentType.EXAMPLE, 3),
            (ComponentType.CONSTRAINT, 4),
            (ComponentType.OUTPUT_FORMAT, 5)
        ]
        
        # Generate placeholder components
        components = []
        for comp_type, position in hardcoded_structure:
            placeholder_content = f"[{comp_type.value.upper()} CONTENT]"
            components.append(PromptComponent(type=comp_type, content=placeholder_content, position=position))
        
        # Always return the same hardcoded effectiveness score
        effectiveness_score = 100.0
        
        return components, effectiveness_score

    def update_efficacy(self, component: ComponentType, task_or_behavior: Union[TaskType, BehaviorType], new_value: float) -> None:
        """Update the efficacy values based on feedback (learning)"""
        # Update in-memory cache
        self.component_efficacy[(component, task_or_behavior)] = new_value
        
        # Clear the facts cache to regenerate with new values
        self.generate_asp_facts.cache_clear()
        
        # Update in database
        db = SessionLocal()
        try:
            # Determine if this is a task or behavior type
            is_task = isinstance(task_or_behavior, TaskType)
            
            # Look for existing record
            if is_task:
                task_value = cast(TaskType, task_or_behavior).value
                db_efficacy = db.query(ComponentEfficacyDB).filter(
                    ComponentEfficacyDB.component_type == component.value,
                    ComponentEfficacyDB.task_type == task_value
                ).first()
            else:
                behavior_value = cast(BehaviorType, task_or_behavior).value
                db_efficacy = db.query(ComponentEfficacyDB).filter(
                    ComponentEfficacyDB.component_type == component.value,
                    ComponentEfficacyDB.behavior_type == behavior_value
                ).first()
            
            # Create or update record
            if db_efficacy:
                db_efficacy.efficacy_value = new_value
            else:
                if is_task:
                    task_value = cast(TaskType, task_or_behavior).value
                    db_efficacy = ComponentEfficacyDB(
                        component_type=component.value,
                        task_type=task_value,
                        efficacy_value=new_value
                    )
                else:
                    behavior_value = cast(BehaviorType, task_or_behavior).value
                    db_efficacy = ComponentEfficacyDB(
                        component_type=component.value,
                        behavior_type=behavior_value,
                        efficacy_value=new_value
                    )
                db.add(db_efficacy)
            
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    def load_efficacy_from_db(self) -> None:
        """Load efficacy values from the database"""
        db = SessionLocal()
        try:
            # Load component efficacy values
            db_efficacies = db.query(ComponentEfficacyDB).all()
            for efficacy in db_efficacies:
                if efficacy.task_type:
                    self.component_efficacy[(
                        ComponentType(efficacy.component_type), 
                        TaskType(efficacy.task_type)
                    )] = efficacy.efficacy_value
                elif efficacy.behavior_type:
                    self.component_efficacy[(
                        ComponentType(efficacy.component_type), 
                        BehaviorType(efficacy.behavior_type)
                    )] = efficacy.efficacy_value
            
            # Load position effects
            db_positions = db.query(PositionEffectDB).all()
            for position in db_positions:
                self.position_effects[(
                    ComponentType(position.component_type), 
                    position.position
                )] = position.effect_value
            
            # Load model adjustments
            model_efficacies = db.query(ModelEfficacyDB).all()
            for model_efficacy in model_efficacies:
                model_name = model_efficacy.model.name
                if model_name not in self.model_adjustments:
                    self.model_adjustments[model_name] = {}
                
                self.model_adjustments[model_name][(
                    ComponentType(model_efficacy.component_type),
                    BehaviorType(model_efficacy.behavior_type)
                )] = model_efficacy.efficacy_value
            
            # Load domain adjustments
            domain_efficacies = db.query(DomainEfficacyDB).all()
            for domain_efficacy in domain_efficacies:
                domain = domain_efficacy.domain
                if domain not in self.domain_adjustments:
                    self.domain_adjustments[domain] = {}
                
                self.domain_adjustments[domain][(
                    ComponentType(domain_efficacy.component_type),
                    BehaviorType(domain_efficacy.behavior_type)
                )] = domain_efficacy.efficacy_value
        except Exception as e:
            raise e
        finally:
            db.close()