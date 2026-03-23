import polars as pl
import pytest

from src.data_service import DataService
from src.schemas import CareerSequence, PreviousRoleProbability, TransitionProbability


@pytest.fixture
def mock_df():
    # A minimal dataframe mimicking the JobHop processed data
    return pl.DataFrame(
        {
            "person_id": [1, 1, 1, 2, 2],
            "start_val": [2010.0, 2011.0, 2012.0, 2010.0, 2011.0],
            "matched_label": [
                "Junior Dev",
                "Senior Dev",
                "Lead Dev",
                "Junior Dev",
                "Project Manager",
            ],
            "next_job_label": ["Senior Dev", "Lead Dev", None, "Project Manager", None],
            "previous_job_label": [None, "Junior Dev", "Senior Dev", None, "Junior Dev"],
        }
    )


def test_get_transitions(mock_df):
    service = DataService(mock_df)
    transitions = service.get_transitions("Junior Dev")

    assert len(transitions) == 2
    assert isinstance(transitions[0], TransitionProbability)

    # 1 went to Senior Dev, 1 went to Project Manager
    labels = [t.next_job_label for t in transitions]
    assert "Senior Dev" in labels
    assert "Project Manager" in labels

    # Each should be 50%
    assert transitions[0].probability_percent == 50.0


def test_get_previous_roles(mock_df):
    service = DataService(mock_df)
    roles = service.get_previous_roles("Senior Dev")

    assert len(roles) == 1
    assert isinstance(roles[0], PreviousRoleProbability)
    assert roles[0].previous_job_label == "Junior Dev"
    assert roles[0].probability_percent == 100.0


def test_get_career_sequences(mock_df):
    service = DataService(mock_df)
    sequences = service.get_career_sequences("Lead Dev")

    assert len(sequences) == 1
    assert isinstance(sequences[0], CareerSequence)
    assert sequences[0].step_1 == "Junior Dev"
    assert sequences[0].step_2 == "Senior Dev"
    assert sequences[0].target_job == "Lead Dev"
    assert sequences[0].count == 1
