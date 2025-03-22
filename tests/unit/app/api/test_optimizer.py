import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.api.optimizer import router, get_optimizer
from app.models.prompt import (
    OptimizationRequest, OptimizedPrompt, PromptComponent,
    ComponentType, TaskType, BehaviorType
)

# Create a test client
client = TestClient(app)

class TestOptimizerAPI:
    """Tests for optimizer API endpoints."""
    
    @patch('app.api.optimizer.get_optimizer')
    def test_optimize_prompt_endpoint(self, mock_get_optimizer, sample_prompt_data):
        """Test the optimize prompt endpoint."""
        # Setup mock optimizer
        mock_optimizer = MagicMock()
        mock_get_optimizer.return_value = mock_optimizer
        
        # Mock the optimize method
        mock_components = [
            PromptComponent(type=ComponentType.INSTRUCTION, content="Test content", position=1)
        ]
        mock_result = OptimizedPrompt(
            components=mock_components,
            full_prompt="Test full prompt",
            rationale="Test rationale",
            effectiveness_score=85.5
        )
        mock_optimizer.optimize.return_value = mock_result
        
        # Make request
        response = client.post("/api/v1/optimize", json=sample_prompt_data)
        
        # Verify response
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["full_prompt"] == "Test full prompt"
        assert json_response["rationale"] == "Test rationale"
        assert json_response["effectiveness_score"] == 85.5
        assert len(json_response["components"]) == 1
        
        # Verify optimizer called
        mock_optimizer.optimize.assert_called_once()
        
    @patch('app.api.optimizer.get_optimizer')
    def test_optimize_prompt_error(self, mock_get_optimizer, sample_prompt_data):
        """Test the optimize prompt endpoint with error."""
        # Setup mock optimizer to raise exception
        mock_optimizer = MagicMock()
        mock_get_optimizer.return_value = mock_optimizer
        mock_optimizer.optimize.side_effect = Exception("Test exception")
        
        # Make request
        response = client.post("/api/v1/optimize", json=sample_prompt_data)
        
        # Verify response
        assert response.status_code == 500
        assert "Test exception" in response.json()["detail"]
    
    @patch('app.api.optimizer.get_optimizer')
    def test_analyze_prompt_endpoint(self, mock_get_optimizer):
        """Test the analyze prompt endpoint."""
        # Setup mock optimizer
        mock_optimizer = MagicMock()
        mock_get_optimizer.return_value = mock_optimizer
        
        # Mock the analyze_task method
        mock_analysis = {
            "detected_tasks": [TaskType.DEDUCTION],
            "detected_behaviors": [BehaviorType.PRECISION, BehaviorType.STEP_BY_STEP],
            "domain_hint": "education"
        }
        mock_optimizer.meta_llm.analyze_task.return_value = mock_analysis
        
        # Make request
        response = client.post("/api/v1/analyze", json={"text": "Explain quantum computing"})
        
        # Verify response
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["analysis"] == mock_analysis
        assert "deduction" in json_response["detected_tasks"]
        assert "precision" in json_response["detected_behaviors"]
        assert "step_by_step" in json_response["detected_behaviors"]
        assert "domain" in json_response
        assert "processing_time" in json_response
        
        # Verify optimizer called
        mock_optimizer.meta_llm.analyze_task.assert_called_once_with("Explain quantum computing")
    
    def test_analyze_prompt_validation(self):
        """Test analyze prompt input validation."""
        # Missing text field
        response = client.post("/api/v1/analyze", json={})
        assert response.status_code == 400
        assert "Text field is required" in response.json()["detail"]
    
    @patch('app.api.optimizer.get_optimizer')
    def test_analyze_prompt_error(self, mock_get_optimizer):
        """Test the analyze prompt endpoint with error."""
        # Setup mock optimizer to raise exception
        mock_optimizer = MagicMock()
        mock_get_optimizer.return_value = mock_optimizer
        mock_optimizer.meta_llm.analyze_task.side_effect = Exception("Test exception")
        
        # Make request
        response = client.post("/api/v1/analyze", json={"text": "Test"})
        
        # Verify response
        assert response.status_code == 500
        assert "Test exception" in response.json()["detail"]
    
    @patch('app.api.optimizer.get_optimizer')
    def test_provide_feedback_endpoint(self, mock_get_optimizer):
        """Test the provide feedback endpoint."""
        # Setup mock optimizer
        mock_optimizer = MagicMock()
        mock_get_optimizer.return_value = mock_optimizer
        mock_optimizer.provide_feedback.return_value = True
        
        # Make request
        feedback_data = {
            "component_type": "instruction",
            "behavior_type": "precision",
            "effectiveness": 0.9
        }
        response = client.post("/api/v1/feedback", json=feedback_data)
        
        # Verify response
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "success"
        assert json_response["component_type"] == "instruction"
        assert json_response["effectiveness"] == 0.9
        
        # Verify optimizer called
        mock_optimizer.provide_feedback.assert_called_once()
    
    def test_provide_feedback_validation(self):
        """Test feedback input validation."""
        # Missing required fields
        response = client.post("/api/v1/feedback", json={})
        assert response.status_code == 400
        assert "Missing required fields" in response.json()["detail"]
        
        # Missing task_type or behavior_type
        response = client.post("/api/v1/feedback", json={
            "component_type": "instruction",
            "effectiveness": 0.9
        })
        assert response.status_code == 400
        assert "task_type or behavior_type" in response.json()["detail"]
        
        # Invalid component_type
        response = client.post("/api/v1/feedback", json={
            "component_type": "invalid",
            "behavior_type": "precision",
            "effectiveness": 0.9
        })
        assert response.status_code == 400
        assert "Invalid input" in response.json()["detail"]
    
    @patch('app.api.optimizer.get_optimizer')
    def test_provide_feedback_error(self, mock_get_optimizer):
        """Test the provide feedback endpoint with error."""
        # Setup mock optimizer
        mock_optimizer = MagicMock()
        mock_get_optimizer.return_value = mock_optimizer
        mock_optimizer.provide_feedback.return_value = False
        
        # Make request
        feedback_data = {
            "component_type": "instruction",
            "behavior_type": "precision",
            "effectiveness": 0.9
        }
        response = client.post("/api/v1/feedback", json=feedback_data)
        
        # Verify response
        assert response.status_code == 500
        assert "Failed to process feedback" in response.json()["detail"]
    
    def test_get_history_endpoint(self, test_db):
        """Test the get history endpoint."""
        # Add test data to the database
        from app.models.database import OptimizedPromptDB
        from datetime import datetime
        
        prompt = OptimizedPromptDB(
            user_prompt="Test prompt",
            optimized_prompt="Optimized prompt",
            target_model="gpt-4",
            effectiveness_score=85.5,
            rationale="Test rationale",
            created_at=datetime.now().isoformat()
        )
        test_db.add(prompt)
        test_db.commit()
        
        # Make request
        response = client.get("/api/v1/history")
        
        # Verify response
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["total"] == 1
        assert json_response["offset"] == 0
        assert json_response["limit"] == 10
        assert len(json_response["items"]) == 1
        assert json_response["items"][0]["user_prompt"] == "Test prompt"
    
    def test_get_history_with_filter(self, test_db):
        """Test the get history endpoint with filter."""
        # Add test data to the database
        from app.models.database import OptimizedPromptDB
        from datetime import datetime
        
        prompt1 = OptimizedPromptDB(
            user_prompt="Test prompt 1",
            optimized_prompt="Optimized prompt 1",
            target_model="gpt-4",
            effectiveness_score=85.5,
            rationale="Test rationale",
            created_at=datetime.now().isoformat()
        )
        
        prompt2 = OptimizedPromptDB(
            user_prompt="Test prompt 2",
            optimized_prompt="Optimized prompt 2",
            target_model="claude",
            effectiveness_score=90.0,
            rationale="Test rationale",
            created_at=datetime.now().isoformat()
        )
        
        test_db.add(prompt1)
        test_db.add(prompt2)
        test_db.commit()
        
        # Make request with model filter
        response = client.get("/api/v1/history?model=gpt-4")
        
        # Verify response
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response["items"]) == 1
        assert json_response["items"][0]["target_model"] == "gpt-4"
    
    def test_get_prompt_by_id_endpoint(self, test_db):
        """Test the get prompt by id endpoint."""
        # Add test data to the database
        from app.models.database import OptimizedPromptDB, PromptComponentDB
        from datetime import datetime
        
        prompt = OptimizedPromptDB(
            user_prompt="Test prompt",
            optimized_prompt="Optimized prompt",
            target_model="gpt-4",
            effectiveness_score=85.5,
            rationale="Test rationale",
            created_at=datetime.now().isoformat()
        )
        test_db.add(prompt)
        test_db.flush()
        
        component = PromptComponentDB(
            prompt_id=prompt.id,
            component_type="instruction",
            content="Test content",
            position=1
        )
        test_db.add(component)
        test_db.commit()
        
        # Make request
        response = client.get(f"/api/v1/history/{prompt.id}")
        
        # Verify response
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["user_prompt"] == "Test prompt"
        assert json_response["optimized_prompt"] == "Optimized prompt"
        assert json_response["target_model"] == "gpt-4"
        assert json_response["effectiveness_score"] == 85.5
        assert json_response["rationale"] == "Test rationale"
        assert len(json_response["components"]) == 1
        assert json_response["components"][0]["type"] == "instruction"
        assert json_response["components"][0]["content"] == "Test content"
        assert json_response["components"][0]["position"] == 1
    
    def test_get_prompt_by_id_not_found(self):
        """Test the get prompt by id endpoint with non-existent id."""
        # Make request with non-existent id
        response = client.get("/api/v1/history/999")
        
        # Verify response
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_health_check_endpoint(self):
        """Test the health check endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["status"] == "healthy"
        assert "version" in json_response
        assert "timestamp" in json_response