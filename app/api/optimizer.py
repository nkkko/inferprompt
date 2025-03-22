from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.models.prompt import OptimizationRequest, OptimizedPrompt, ComponentType, TaskType, BehaviorType
from app.services.prompt_optimizer import PromptOptimizer
from app.models.database import get_db, SessionLocal, OptimizedPromptDB, Base, engine
from typing import Dict, List, Any, Optional, Union
from sqlalchemy.orm import Session
import os
import datetime
import logging
import time
import json

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

# Create database tables
Base.metadata.create_all(bind=engine)

# In production, you would use proper dependency injection
def get_optimizer():
    api_key = os.getenv("OPENAI_API_KEY", None)  # Or your preferred LLM provider
    return PromptOptimizer(api_key=api_key)


@router.post("/optimize", response_model=OptimizedPrompt)
async def optimize_prompt(request: OptimizationRequest, req: Request, optimizer: PromptOptimizer = Depends(get_optimizer)):
    """Optimize a prompt based on the request parameters"""
    start_time = time.time()
    request_id = f"req_{int(start_time * 1000)}"
    
    # Log request details
    logger.info(f"[{request_id}] Optimization request received: model={request.target_model}, tasks={len(request.target_tasks)}, behaviors={len(request.target_behaviors)}")
    
    try:
        # Process the request
        result = optimizer.optimize(request)
        
        # Log success
        processing_time = time.time() - start_time
        logger.info(f"[{request_id}] Optimization completed in {processing_time:.2f}s with score: {result.effectiveness_score:.2f}")
        
        return result
    except Exception as e:
        # Log error details
        logger.error(f"[{request_id}] Optimization failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.post("/analyze")
async def analyze_prompt(prompt: Dict[str, str], req: Request, optimizer: PromptOptimizer = Depends(get_optimizer)):
    """Analyze a prompt without fully optimizing it"""
    start_time = time.time()
    request_id = f"req_{int(start_time * 1000)}"
    
    # Input validation
    if not prompt.get("text"):
        raise HTTPException(status_code=400, detail="Text field is required")
    
    logger.info(f"[{request_id}] Analysis request received: prompt_length={len(prompt.get('text', ''))}")
    
    try:
        # Analyze the prompt
        analysis = optimizer.meta_llm.analyze_task(prompt.get("text", ""))
        
        # Format the response
        response = {
            "analysis": analysis,
            "detected_tasks": [task.value for task in analysis["detected_tasks"]],
            "detected_behaviors": [behavior.value for behavior in analysis["detected_behaviors"]],
            "domain": analysis.get("domain_hint"),
            "processing_time": f"{time.time() - start_time:.2f}s"
        }
        
        logger.info(f"[{request_id}] Analysis completed in {time.time() - start_time:.2f}s")
        return response
    except Exception as e:
        logger.error(f"[{request_id}] Analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/feedback")
async def provide_feedback(feedback: Dict[str, Any], req: Request, optimizer: PromptOptimizer = Depends(get_optimizer)):
    """Provide feedback on component effectiveness to improve future optimizations"""
    request_id = f"req_{int(time.time() * 1000)}"
    
    # Validate required fields
    required_fields = ["component_type", "effectiveness"]
    missing_fields = [field for field in required_fields if field not in feedback]
    
    if missing_fields:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing_fields)}")
    
    # Validate that either task_type or behavior_type is present
    if "task_type" not in feedback and "behavior_type" not in feedback:
        raise HTTPException(status_code=400, detail="Either task_type or behavior_type must be provided")
    
    try:
        # Parse and validate input
        component_type = ComponentType(feedback.get("component_type"))
        
        # Handle both task and behavior feedback
        if feedback.get("task_type"):
            task_or_behavior = TaskType(feedback.get("task_type"))
            logger.info(f"[{request_id}] Feedback received for component={component_type.value}, task={task_or_behavior.value}")
        else:
            task_or_behavior = BehaviorType(feedback.get("behavior_type"))
            logger.info(f"[{request_id}] Feedback received for component={component_type.value}, behavior={task_or_behavior.value}")
            
        effectiveness = float(feedback.get("effectiveness", 0.0))
        
        # Update with feedback
        if optimizer.provide_feedback(component_type, task_or_behavior, effectiveness):
            return {
                "status": "success", 
                "message": "Feedback recorded successfully",
                "component_type": component_type.value,
                "effectiveness": effectiveness
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to process feedback")
            
    except ValueError as e:
        # Handle validation errors
        logger.error(f"[{request_id}] Invalid feedback data: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        # Handle other errors
        logger.error(f"[{request_id}] Feedback processing failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process feedback: {str(e)}")


@router.get("/history")
async def get_history(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    model: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get the history of optimized prompts"""
    try:
        # Build query with filters
        query = db.query(OptimizedPromptDB)
        
        if model:
            query = query.filter(OptimizedPromptDB.target_model == model)
            
        # Get total count for pagination
        total = query.count()
        
        # Get paginated results
        prompts = query.order_by(OptimizedPromptDB.created_at.desc()).offset(offset).limit(limit).all()
        
        # Format the response
        result = []
        for prompt in prompts:
            # Truncate long prompts in list view
            user_prompt_preview = prompt.user_prompt[:100] + "..." if len(prompt.user_prompt) > 100 else prompt.user_prompt
            
            result.append({
                "id": prompt.id,
                "user_prompt": user_prompt_preview,
                "target_model": prompt.target_model,
                "effectiveness_score": prompt.effectiveness_score,
                "created_at": prompt.created_at
            })
            
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": result
        }
    except Exception as e:
        logger.error(f"Error retrieving history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")


@router.get("/history/{prompt_id}")
async def get_prompt_by_id(prompt_id: int, db: Session = Depends(get_db)):
    """Get a specific optimized prompt by ID, including all components"""
    try:
        # Query the specific prompt
        prompt = db.query(OptimizedPromptDB).filter(OptimizedPromptDB.id == prompt_id).first()
        
        if not prompt:
            logger.warning(f"Prompt not found: id={prompt_id}")
            raise HTTPException(status_code=404, detail=f"Prompt with ID {prompt_id} not found")
            
        # Format the components
        components = []
        for comp in prompt.components:
            components.append({
                "type": comp.component_type,
                "content": comp.content,
                "position": comp.position
            })
            
        # Return the complete prompt details
        return {
            "id": prompt.id,
            "user_prompt": prompt.user_prompt,
            "optimized_prompt": prompt.optimized_prompt,
            "target_model": prompt.target_model,
            "effectiveness_score": prompt.effectiveness_score,
            "rationale": prompt.rationale,
            "created_at": prompt.created_at,
            "components": sorted(components, key=lambda x: x["position"])
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving prompt {prompt_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve prompt: {str(e)}")
        
        
@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.datetime.now().isoformat()
    }
