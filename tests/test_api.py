"""Tests for the FastAPI activities application"""
import copy
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Provide a test client"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store the original state
    original_activities = copy.deepcopy(activities)
    yield
    # Restore after test
    activities.clear()
    activities.update(original_activities)


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirect(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestGetActivities:
    """Tests for the GET /activities endpoint"""

    def test_get_all_activities(self, client, reset_activities):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Chess Club" in data
        assert "Programming Class" in data

    def test_activity_structure(self, client, reset_activities):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        activity = data["Chess Club"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)


class TestSignupEndpoint:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""

    def test_successful_signup(self, client, reset_activities):
        """Test successful student signup"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]

    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup actually adds the participant"""
        email = "newstudent@mergington.edu"
        client.post(f"/activities/Chess%20Club/signup?email={email}")
        
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]

    def test_duplicate_signup_rejected(self, client, reset_activities):
        """Test that duplicate signups are rejected"""
        email = "michael@mergington.edu"
        response = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_case_insensitive_duplicate_check(self, client, reset_activities):
        """Test that duplicate check is case-insensitive"""
        email = "MICHAEL@MERGINGTON.EDU"
        response = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Fake%20Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_signup_to_full_activity(self, client, reset_activities):
        """Test signup to a full activity"""
        # Create a full activity
        activities["Full Activity"] = {
            "description": "Full",
            "schedule": "Test",
            "max_participants": 2,
            "participants": ["student1@test.edu", "student2@test.edu"]
        }
        
        response = client.post(
            "/activities/Full%20Activity/signup?email=student3@test.edu"
        )
        assert response.status_code == 400
        assert "full" in response.json()["detail"]


class TestUnregisterEndpoint:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint"""

    def test_successful_unregister(self, client, reset_activities):
        """Test successful unregistration"""
        email = "michael@mergington.edu"
        response = client.delete(
            f"/activities/Chess%20Club/unregister?email={email}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "Unregistered" in data["message"]

    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes the participant"""
        email = "michael@mergington.edu"
        client.delete(f"/activities/Chess%20Club/unregister?email={email}")
        
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Chess Club"]["participants"]

    def test_unregister_case_insensitive(self, client, reset_activities):
        """Test that unregister is case-insensitive"""
        email = "MICHAEL@MERGINGTON.EDU"
        response = client.delete(
            f"/activities/Chess%20Club/unregister?email={email}"
        )
        assert response.status_code == 200

    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister from non-existent activity"""
        response = client.delete(
            "/activities/Fake%20Activity/unregister?email=student@test.edu"
        )
        assert response.status_code == 404

    def test_unregister_not_registered_student(self, client, reset_activities):
        """Test unregister when student is not registered"""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=notregistered@test.edu"
        )
        assert response.status_code == 404
        assert "not registered" in response.json()["detail"]


class TestIntegration:
    """Integration tests for complete workflows"""

    def test_signup_and_unregister_workflow(self, client, reset_activities):
        """Test a complete signup and unregister workflow"""
        email = "integration@test.edu"
        activity = "Chess Club"
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify removal
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]

    def test_multiple_signups_and_unregisters(self, client, reset_activities):
        """Test multiple student operations"""
        activity = "Programming Class"
        students = ["alice@test.edu", "bob@test.edu", "charlie@test.edu"]
        
        # Sign up all students
        for student in students:
            response = client.post(f"/activities/{activity}/signup?email={student}")
            assert response.status_code == 200
        
        # Verify all signed up
        response = client.get("/activities")
        for student in students:
            assert student in response.json()[activity]["participants"]
        
        # Unregister middle student
        response = client.delete(f"/activities/{activity}/unregister?email={students[1]}")
        assert response.status_code == 200
        
        # Verify only middle student removed
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        assert students[0] in participants
        assert students[1] not in participants
        assert students[2] in participants
