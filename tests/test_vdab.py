from unittest.mock import MagicMock, patch

import pytest

from src.schemas import OccupationalProfileInfo, SkillsProfile
from vdab_api_service import VDABApiService


@pytest.fixture
def mock_api():
    with patch("vdab_api_service.requests.get") as mock_get:
        yield mock_get


def test_vdab_search_returns_profile_schema(mock_api):
    # Mock search api response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "_embedded": {
            "competentSearchResultList": [
                {
                    "document": {
                        "id": "123",
                        "code": "A1",
                        "releaseNumber": "3.25",
                        "title": {"en": "Data scientist", "nl": "Data scientist"},
                    }
                }
            ]
        }
    }
    mock_api.return_value = mock_resp

    service = VDABApiService(api_key="dummy")

    # We enforce English in our query via our requirements
    profile = service.search_profile("Data scientist")

    # Check that it returns an OccupationalProfileInfo schema model
    assert isinstance(profile, OccupationalProfileInfo)
    assert profile.id == "123"
    assert profile.title == "Data scientist"


def test_vdab_get_skills_one_call(mock_api):
    """Test that get_skills handles embedded competences in profile response."""

    base = "https://api.vdab.be/services/opendata/competent/v2"
    profile_url = f"{base}/releases/3.25/occupationalprofiles/123"

    def mock_get_side_effect(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200

        if url == profile_url:
            resp.json.return_value = {
                "id": "123",
                "essentialCompetences": [
                    {
                        "skill": {"description": {"en": "Machine Learning"}},
                        "knowledgeItems": [{"description": {"en": "Python"}}],
                    }
                ],
                "softSkills": [
                    {"title": {"en": "Teamwork"}}
                ],
            }
        return resp

    mock_api.side_effect = mock_get_side_effect

    service = VDABApiService(api_key="dummy")
    skills = service.get_skills("123", "3.25")

    assert isinstance(skills, SkillsProfile)
    assert "Machine Learning" in skills.technical_skills
    assert "Python" in skills.knowledge
    assert "Teamwork" in skills.soft_skills

    # Only 1 call to profile detail should be made!
    assert mock_api.call_count == 1


def test_vdab_different_profiles_produce_different_skills(mock_api):
    """Two distinct profiles must yield different skill sets for a gap to exist."""

    def mock_get_side_effect(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200

        if "/occupationalprofiles/profile_A" in url:
            resp.json.return_value = {
                "id": "profile_A",
                "essentialCompetences": [
                    {"skill": {"description": {"en": "Shared Skill"}}}
                ],
                "softSkills": [{"title": {"en": "Leadership"}}],
            }
        elif "/occupationalprofiles/profile_B" in url:
            resp.json.return_value = {
                "id": "profile_B",
                "essentialCompetences": [
                    {"skill": {"description": {"en": "Shared Skill"}}},
                    {"skill": {"description": {"en": "New Skill"}}},
                ],
                "softSkills": [
                    {"title": {"en": "Leadership"}},
                    {"title": {"en": "Creativity"}},
                ],
            }
        return resp

    mock_api.side_effect = mock_get_side_effect

    service = VDABApiService(api_key="dummy")

    skills_a = service.get_skills("profile_A", "current")
    skills_b = service.get_skills("profile_B", "current")

    # B has more skills than A
    assert "New Skill" not in skills_a.technical_skills
    assert "New Skill" in skills_b.technical_skills
    assert "Creativity" not in skills_a.soft_skills
    assert "Creativity" in skills_b.soft_skills

