from sqlalchemy import create_engine, Column, Integer, String, Float, Enum, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from enum import Enum as PyEnum

# Get database URL from environment or use SQLite by default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./inferprompt.db")

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for declarative models
Base = declarative_base()


# Database dependency injection
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Model definitions
class ComponentTypeEnum(str, PyEnum):
    INSTRUCTION = "instruction"
    CONTEXT = "context"
    EXAMPLE = "example"
    CONSTRAINT = "constraint"
    OUTPUT_FORMAT = "output_format"


class TaskTypeEnum(str, PyEnum):
    DEDUCTION = "deduction"
    INDUCTION = "induction"
    ABDUCTION = "abduction"
    COMPARISON = "comparison"
    COUNTERFACTUAL = "counterfactual"


class BehaviorTypeEnum(str, PyEnum):
    PRECISION = "precision"
    CREATIVITY = "creativity"
    STEP_BY_STEP = "step_by_step"
    CONCISENESS = "conciseness"
    ERROR_CHECKING = "error_checking"


class ModelDB(Base):
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    
    efficacy_values = relationship("ModelEfficacyDB", back_populates="model")


class ComponentEfficacyDB(Base):
    __tablename__ = "component_efficacy"
    
    id = Column(Integer, primary_key=True, index=True)
    component_type = Column(Enum(ComponentTypeEnum), index=True)
    task_type = Column(Enum(TaskTypeEnum), nullable=True, index=True)
    behavior_type = Column(Enum(BehaviorTypeEnum), nullable=True, index=True)
    efficacy_value = Column(Float, default=0.5)
    
    # Ensure either task_type or behavior_type is set, but not both
    # This would be handled in application logic


class PositionEffectDB(Base):
    __tablename__ = "position_effects"
    
    id = Column(Integer, primary_key=True, index=True)
    component_type = Column(Enum(ComponentTypeEnum), index=True)
    position = Column(Integer)
    effect_value = Column(Float, default=0.5)


class ModelEfficacyDB(Base):
    __tablename__ = "model_efficacy"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("models.id"))
    component_type = Column(Enum(ComponentTypeEnum), index=True)
    behavior_type = Column(Enum(BehaviorTypeEnum), index=True)
    efficacy_value = Column(Float, default=0.5)
    
    model = relationship("ModelDB", back_populates="efficacy_values")


class DomainEfficacyDB(Base):
    __tablename__ = "domain_efficacy"
    
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, index=True)
    component_type = Column(Enum(ComponentTypeEnum), index=True)
    behavior_type = Column(Enum(BehaviorTypeEnum), index=True)
    efficacy_value = Column(Float, default=0.5)


class OptimizedPromptDB(Base):
    __tablename__ = "optimized_prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_prompt = Column(Text)
    optimized_prompt = Column(Text)
    target_model = Column(String, index=True)
    effectiveness_score = Column(Float)
    rationale = Column(Text, nullable=True)
    created_at = Column(String)  # Store ISO timestamp
    
    components = relationship("PromptComponentDB", back_populates="prompt")


class PromptComponentDB(Base):
    __tablename__ = "prompt_components"
    
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("optimized_prompts.id"))
    component_type = Column(Enum(ComponentTypeEnum))
    content = Column(Text)
    position = Column(Integer)
    
    prompt = relationship("OptimizedPromptDB", back_populates="components")
