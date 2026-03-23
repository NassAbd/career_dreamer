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


def test_vdab_get_skills_profile_limits_api_calls(mock_api):
    # Setup mock to return a limited list for technical competences
    # thus preventing 429
    def mock_get_side_effect(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "/technicalcompetences/" in url:
            # Detail call
            resp.json.return_value = {
                "skill": {"description": {"en": "Machine Learning", "nl": "Machine Learning"}},
                "knowledgeItems": [{"description": {"en": "Python", "nl": "Python"}}],
            }
        elif "/technicalcompetences" in url:
            # List call
            resp.json.return_value = {
                "_embedded": {
                    "technicalCompetenceListInfoList": [
                        {"id": "tc1"},
                        {"id": "tc2"},  # Only 2 items returned by API (since we pass size=5)
                    ]
                }
            }
        elif "/softskills" in url:
            # List call
            resp.json.return_value = {
                "_embedded": {
                    "softSkillList": [{"shortDescription": {"en": "Teamwork", "nl": "Teamwork"}}]
                }
            }
        return resp

    mock_api.side_effect = mock_get_side_effect

    service = VDABApiService(api_key="dummy")

    # Contract: get_skills returns SkillsProfile schema
    skills = service.get_skills("123", "3.25")

    assert isinstance(skills, SkillsProfile)
    assert "Machine Learning" in skills.technical_skills
    assert "Python" in skills.knowledge
    assert "Teamwork" in skills.soft_skills

    # Important validation to avoid 429
    # 1 for tech list, 2 for tech details, 1 for softskills list = 4 calls total.
    assert mock_api.call_count == 4
