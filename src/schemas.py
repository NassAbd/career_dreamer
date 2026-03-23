from typing import List

from pydantic import BaseModel, ConfigDict


class SkillsProfile(BaseModel):
    """Schema representing the extracted skills for a job profile."""

    model_config = ConfigDict(frozen=True)

    technical_skills: List[str] = []
    knowledge: List[str] = []
    soft_skills: List[str] = []


class OccupationalProfileInfo(BaseModel):
    """Schema representing a high-level VDAB occupational profile."""

    id: str
    code: str
    release_number: str
    title: str


class TransitionProbability(BaseModel):
    """Schema representing a job transition probability."""

    next_job_label: str
    probability_percent: float


class PreviousRoleProbability(BaseModel):
    """Schema representing a previous role probability."""

    previous_job_label: str
    probability_percent: float


class CareerSequence(BaseModel):
    """Schema representing a 2-step career sequence."""

    step_1: str
    step_2: str
    target_job: str
    count: int
