import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/health/")
    assert response.status_code == 200
    assert "status" in response.json()

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_get_domains():
    """Test getting available interview domains"""
    response = client.get("/api/interview/domains")
    assert response.status_code == 200
    data = response.json()
    assert "domains" in data
    assert "Software Engineering" in data["domains"]

def test_create_interview_session():
    """Test creating a new interview session"""
    session_data = {
        "domain": "Software Engineering",
        "difficulty": "medium",
        "duration_minutes": 45
    }
    response = client.post("/api/interview/sessions", json=session_data)
    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "Software Engineering"
    assert data["difficulty"] == "medium"
    assert data["status"] == "active"
