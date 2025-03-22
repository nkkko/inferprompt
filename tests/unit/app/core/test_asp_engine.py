import pytest
from unittest.mock import patch, MagicMock
from app.core.asp_engine import ASPEngine
from app.models.prompt import ComponentType, TaskType, BehaviorType, PromptComponent

class TestASPEngine:
    """Tests for ASPEngine class."""
    
    def test_init(self):
        """Test initialization of ASP engine."""
        engine = ASPEngine(load_from_db=False)
        
        # Verify default values
        assert isinstance(engine.base_program, str)
        assert len(engine.component_efficacy) > 0
        assert len(engine.position_effects) > 0
        assert len(engine.weights) > 0
        assert len(engine.model_adjustments) > 0
        assert len(engine.domain_adjustments) > 0
    
    def test_generate_asp_facts(self):
        """Test generation of ASP facts."""
        engine = ASPEngine(load_from_db=False)
        
        # Test with minimal inputs
        tasks = (TaskType.DEDUCTION,)
        behaviors = (BehaviorType.PRECISION,)
        
        facts = engine.generate_asp_facts(tasks, behaviors)
        
        # Basic verification
        assert "target_task(deduction)" in facts
        assert "target_behavior(precision)" in facts
        assert "component_efficacy" in facts
        assert "position_effect" in facts
        assert "weight" in facts
        
        # Test with model and domain
        facts_with_model = engine.generate_asp_facts(
            tasks, behaviors, target_model="gpt-4", domain="legal"
        )
        
        # Additional verification
        assert "target_model(gpt-4)" in facts_with_model
        assert "target_domain(legal)" in facts_with_model
        assert "model_specific_efficacy" in facts_with_model
        assert "domain_efficacy" in facts_with_model
    
    @patch('clingo.Control')
    def test_solve_success(self, mock_control):
        """Test successful solving."""
        # Setup mock
        mock_model = MagicMock()
        mock_symbol1 = MagicMock()
        mock_symbol1.name = "prompt_position"
        mock_symbol1.arguments = [MagicMock(), MagicMock()]
        mock_symbol1.arguments[0].__str__.return_value = "instruction"
        mock_symbol1.arguments[1].__str__.return_value = "1"
        
        mock_symbol2 = MagicMock()
        mock_symbol2.name = "effectiveness"
        mock_symbol2.arguments = [MagicMock()]
        mock_symbol2.arguments[0].__str__.return_value = "100"
        
        mock_model.symbols.return_value = [mock_symbol1, mock_symbol2]
        
        mock_control_instance = MagicMock()
        mock_control.return_value = mock_control_instance
        mock_control_instance.solve.side_effect = lambda on_model: on_model(mock_model)
        
        # Test solve method
        engine = ASPEngine(load_from_db=False)
        components, score = engine.solve(
            target_tasks=[TaskType.DEDUCTION],
            target_behaviors=[BehaviorType.PRECISION]
        )
        
        # Verify results
        assert len(components) == 1
        assert components[0].type == ComponentType.INSTRUCTION
        assert components[0].position == 1
        assert score == 100.0
        
        # Verify clingo was called correctly
        mock_control.assert_called_once()
        mock_control_instance.add.assert_called_once()
        mock_control_instance.ground.assert_called_once()
        mock_control_instance.solve.assert_called_once()
    
    @patch('clingo.Control')
    def test_solve_no_models(self, mock_control):
        """Test solving with no models found."""
        # Setup mock to return no models
        mock_control_instance = MagicMock()
        mock_control.return_value = mock_control_instance
        mock_control_instance.solve.return_value = None
        
        # Test solve method
        engine = ASPEngine(load_from_db=False)
        components, score = engine.solve(
            target_tasks=[TaskType.DEDUCTION],
            target_behaviors=[BehaviorType.PRECISION]
        )
        
        # Verify fallback was used
        assert len(components) == 5  # All component types
        assert score == 100.0  # Hardcoded score
        
        # Verify positions are correct
        positions = {comp.type: comp.position for comp in components}
        assert positions[ComponentType.INSTRUCTION] == 1
        assert positions[ComponentType.CONTEXT] == 2
        assert positions[ComponentType.EXAMPLE] == 3
        assert positions[ComponentType.CONSTRAINT] == 4
        assert positions[ComponentType.OUTPUT_FORMAT] == 5
    
    @patch('clingo.Control')
    def test_solve_exception(self, mock_control):
        """Test solving with exception."""
        # Setup mock to raise exception
        mock_control.side_effect = Exception("Test exception")
        
        # Test solve method
        engine = ASPEngine(load_from_db=False)
        components, score = engine.solve(
            target_tasks=[TaskType.DEDUCTION],
            target_behaviors=[BehaviorType.PRECISION]
        )
        
        # Verify fallback was used
        assert len(components) == 5  # All component types
        assert score == 100.0  # Hardcoded score
    
    def test_fallback_solve(self):
        """Test the fallback solve method."""
        engine = ASPEngine(load_from_db=False)
        components, score = engine._fallback_solve(
            target_tasks=[TaskType.DEDUCTION],
            target_behaviors=[BehaviorType.PRECISION]
        )
        
        # Verify results
        assert len(components) == 5
        assert score == 100.0
        
        # Verify each component type is included once
        component_types = [comp.type for comp in components]
        assert ComponentType.INSTRUCTION in component_types
        assert ComponentType.CONTEXT in component_types
        assert ComponentType.EXAMPLE in component_types
        assert ComponentType.CONSTRAINT in component_types
        assert ComponentType.OUTPUT_FORMAT in component_types
    
    @patch('app.models.database.SessionLocal')
    def test_update_efficacy(self, mock_session_local):
        """Test updating efficacy values."""
        # Setup mock
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Test update method
        engine = ASPEngine(load_from_db=False)
        engine.generate_asp_facts.cache_clear = MagicMock()  # Mock cache clear
        
        # Test with task type
        component = ComponentType.INSTRUCTION
        task = TaskType.DEDUCTION
        new_value = 0.95
        
        engine.update_efficacy(component, task, new_value)
        
        # Verify in-memory update
        assert engine.component_efficacy[(component, task)] == new_value
        
        # Verify cache cleared
        engine.generate_asp_facts.cache_clear.assert_called_once()
        
        # Verify DB update
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Test with behavior type
        mock_db.reset_mock()
        engine.generate_asp_facts.cache_clear.reset_mock()
        
        behavior = BehaviorType.PRECISION
        engine.update_efficacy(component, behavior, new_value)
        
        # Verify calls
        assert engine.component_efficacy[(component, behavior)] == new_value
        engine.generate_asp_facts.cache_clear.assert_called_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @patch('app.models.database.SessionLocal')
    def test_update_efficacy_existing(self, mock_session_local):
        """Test updating existing efficacy values."""
        # Setup mock for existing record
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_existing = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_existing
        
        # Test update method
        engine = ASPEngine(load_from_db=False)
        engine.generate_asp_facts.cache_clear = MagicMock()  # Mock cache clear
        
        component = ComponentType.INSTRUCTION
        task = TaskType.DEDUCTION
        new_value = 0.95
        
        engine.update_efficacy(component, task, new_value)
        
        # Verify existing record updated
        assert mock_existing.efficacy_value == new_value
        
        # Verify commit called but not add
        mock_db.commit.assert_called_once()
        mock_db.add.assert_not_called()
    
    @patch('app.models.database.SessionLocal')
    def test_load_efficacy_from_db(self, mock_session_local):
        """Test loading efficacy values from database."""
        # Setup mock DB results
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Component efficacy
        mock_comp_efficacy1 = MagicMock()
        mock_comp_efficacy1.component_type = "instruction"
        mock_comp_efficacy1.task_type = "deduction"
        mock_comp_efficacy1.behavior_type = None
        mock_comp_efficacy1.efficacy_value = 0.9
        
        mock_comp_efficacy2 = MagicMock()
        mock_comp_efficacy2.component_type = "example"
        mock_comp_efficacy2.task_type = None
        mock_comp_efficacy2.behavior_type = "precision"
        mock_comp_efficacy2.efficacy_value = 0.8
        
        # Position effects
        mock_position = MagicMock()
        mock_position.component_type = "instruction"
        mock_position.position = 1
        mock_position.effect_value = 0.95
        
        # Model efficacy
        mock_model_efficacy = MagicMock()
        mock_model_efficacy.model.name = "test-model"
        mock_model_efficacy.component_type = "instruction"
        mock_model_efficacy.behavior_type = "precision"
        mock_model_efficacy.efficacy_value = 0.85
        
        # Domain efficacy
        mock_domain_efficacy = MagicMock()
        mock_domain_efficacy.domain = "test-domain"
        mock_domain_efficacy.component_type = "instruction"
        mock_domain_efficacy.behavior_type = "precision"
        mock_domain_efficacy.efficacy_value = 0.75
        
        # Setup query results
        mock_db.query.return_value.all.side_effect = [
            [mock_comp_efficacy1, mock_comp_efficacy2],  # ComponentEfficacyDB
            [mock_position],                             # PositionEffectDB
            [mock_model_efficacy],                       # ModelEfficacyDB
            [mock_domain_efficacy]                       # DomainEfficacyDB
        ]
        
        # Test load method
        engine = ASPEngine(load_from_db=False)
        engine.load_efficacy_from_db()
        
        # Verify values loaded
        assert engine.component_efficacy[(ComponentType.INSTRUCTION, TaskType.DEDUCTION)] == 0.9
        assert engine.component_efficacy[(ComponentType.EXAMPLE, BehaviorType.PRECISION)] == 0.8
        assert engine.position_effects[(ComponentType.INSTRUCTION, 1)] == 0.95
        assert engine.model_adjustments["test-model"][(ComponentType.INSTRUCTION, BehaviorType.PRECISION)] == 0.85
        assert engine.domain_adjustments["test-domain"][(ComponentType.INSTRUCTION, BehaviorType.PRECISION)] == 0.75
        
        # Verify DB was closed
        mock_db.close.assert_called_once()