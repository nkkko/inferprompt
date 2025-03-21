from fastapi import APIRouter, Depends, HTTPException, Query
from app.models.prompt import OptimizationRequest, OptimizedPrompt, ComponentType, TaskType, BehaviorType
from app.services.prompt_optimizer import PromptOptimizer
from app.models.database import get_db, SessionLocal, OptimizedPromptDB, Base, engine
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
import os
import datetime

router = APIRouter(prefix="/api/v1")

# Create database tables
Base.metadata.create_all(bind=engine)

# In production, you would use proper dependency injection
def get_optimizer():
    api_key = os.getenv("OPENAI_API_KEY", None)  # Or your preferred LLM provider
    return PromptOptimizer(api_key=api_key)


@router.post("/optimize", response_model=OptimizedPrompt)
async def optimize_prompt(request: OptimizationRequest, optimizer: PromptOptimizer = Depends(get_optimizer)):
    """Optimize a prompt based on the request parameters"""
    try:
        return optimizer.optimize(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_prompt(prompt: Dict[str, str], optimizer: PromptOptimizer = Depends(get_optimizer)):
    """Analyze a prompt without fully optimizing it"""
    try:
        analysis = optimizer.meta_llm.analyze_task(prompt.get("text", ""))
        return {
            "analysis": analysis,
            "detected_tasks": [task.value for task in analysis["detected_tasks"]],
            "detected_behaviors": [behavior.value for behavior in analysis["detected_behaviors"]],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def provide_feedback(feedback: Dict[str, Any], optimizer: PromptOptimizer = Depends(get_optimizer)):
    """Provide feedback on component effectiveness to improve future optimizations"""
    try:
        component_type = ComponentType(feedback.get("component_type"))
        # Handle both task and behavior feedback
        if feedback.get("task_type"):
            task_or_behavior = TaskType(feedback.get("task_type"))
        else:
            task_or_behavior = BehaviorType(feedback.get("behavior_type"))
            
        effectiveness = float(feedback.get("effectiveness", 0.0))
        optimizer.provide_feedback(component_type, task_or_behavior, effectiveness)
        return {"status": "success", "message": "Feedback recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    model: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get the history of optimized prompts"""
    try:
        query = db.query(OptimizedPromptDB)
        
        if model:
            query = query.filter(OptimizedPromptDB.target_model == model)
            
        total = query.count()
        prompts = query.order_by(OptimizedPromptDB.created_at.desc()).offset(offset).limit(limit).all()
        
        result = []
        for prompt in prompts:
            result.append({
                "id": prompt.id,
                "user_prompt": prompt.user_prompt,
                "optimized_prompt": prompt.optimized_prompt,
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{prompt_id}")
async def get_prompt_by_id(prompt_id: int, db: Session = Depends(get_db)):
    """Get a specific optimized prompt by ID, including all components"""
    try:
        prompt = db.query(OptimizedPromptDB).filter(OptimizedPromptDB.id == prompt_id).first()
        
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")
            
        components = []
        for comp in prompt.components:
            components.append({
                "type": comp.component_type,
                "content": comp.content,
                "position": comp.position
            })
            
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
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
