import logging
from typing import Dict, List, Optional

import requests
import streamlit as st

from src.schemas import OccupationalProfileInfo, SkillsProfile

logger = logging.getLogger(__name__)


class VDABApiService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.vdab.be/services/opendata/competent/v2"
        self.headers = {"X-IBM-Client-Id": self.api_key, "Accept": "application/hal+json"}
        self.lang_fallback_order = ["en", "nl", "fr", "de"]

    def _extract_mls(self, mls: Optional[Dict], lang: str) -> str:
        """Extract a string from a MultiLanguageString dict."""
        if not mls or not isinstance(mls, dict):
            return ""
        candidates = [lang] + [lc for lc in self.lang_fallback_order if lc != lang]
        for code in candidates:
            value = mls.get(code)
            if value:
                return value.strip()
        return ""

    def search_profile(self, job_title: str, lang: str = "en") -> Optional[OccupationalProfileInfo]:
        """Search the VDAB /search endpoint."""
        # Force Dutch language to be sure to get results
        search_lang = "nl"

        try:
            resp = requests.get(
                f"{self.base_url}/search",
                headers=self.headers,
                params={
                    "searchValue": job_title,
                    "entityTypes": "OCCUPATIONAL_PROFILE",
                    "language": search_lang,
                    "size": 1,
                    "page": 0,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("_embedded", {}).get("competentSearchResultList", [])
            if not results:
                return None

            doc = results[0].get("document", {})
            title_mls = doc.get("title")
            parsed_title = self._extract_mls(title_mls, lang)
            return OccupationalProfileInfo(
                id=doc.get("id"),
                code=doc.get("code", ""),
                release_number=doc.get("releaseNumber", "current"),
                title=parsed_title if parsed_title else job_title,
            )
        except requests.exceptions.RequestException as e:
            logger.warning(f"VDAB API search failed: {e}")
            return None


    def get_skills(
        self, profile_id: str, release: str = "current", lang: str = "en"
    ) -> SkillsProfile:
        """Fetch the skills profile for a specific occupational profile.

        The profile detail endpoint returns linked competences and soft skills
        directly in the JSON body (essentialCompetences, specificCompetences, softSkills).
        """
        tech_skills: List[str] = []
        knowledge: List[str] = []
        soft_skills: List[str] = []

        try:
            # 1. Fetch occupational profile detail
            resp = requests.get(
                f"{self.base_url}/releases/{release}/occupationalprofiles/{profile_id}",
                headers=self.headers,
                params={"lang": lang},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            # 2. Extract Technical Competences (Essential + Specific)
            comp_lists = [
                data.get("essentialCompetences", []),
                data.get("specificCompetences", []),
            ]

            for comp_list in comp_lists:
                if not isinstance(comp_list, list):
                    continue
                # Technically we could have many, but we'll limit to maintain a clean UI
                for tc in comp_list[:10]:
                    # Extract skill label
                    skill_obj = tc.get("skill", {})
                    skill_label = self._extract_mls(skill_obj.get("description"), lang)
                    if skill_label and skill_label not in tech_skills:
                        tech_skills.append(skill_label)

                    # Extract knowledge items
                    for ki in tc.get("knowledgeItems", []):
                        ki_label = self._extract_mls(ki.get("description"), lang)
                        if ki_label and ki_label not in knowledge:
                            knowledge.append(ki_label)

            # 3. Extract Soft Skills
            # Can be in "softSkills" directly or handled via HAL "_links" (previous plan)
            # but usually they are direct or embedded.
            ss_list = data.get("softSkills", [])
            if not ss_list:
                # Try embedded if not found directly
                ss_list = data.get("_embedded", {}).get("softSkillList", [])

            for item in ss_list:
                # Field can be 'title' or 'description' or 'shortDescription'
                label = self._extract_mls(item.get("title"), lang)
                if not label:
                    label = self._extract_mls(item.get("description"), lang)
                if not label:
                    label = self._extract_mls(item.get("shortDescription"), lang)

                if label and label not in soft_skills:
                    soft_skills.append(label)

        except requests.exceptions.RequestException as e:
            logger.warning(f"VDAB API get_skills failed for profile {profile_id}: {e}")

        # Fallback for technical competences if none found in detail
        if not tech_skills:
            logger.info(f"Fallback to global listing for profile {profile_id}")
            try:
                tc_resp = requests.get(
                    f"{self.base_url}/releases/{release}/technicalcompetences",
                    headers=self.headers,
                    params={"lang": lang, "size": 5, "page": 0},
                    timeout=10,
                )
                if tc_resp.status_code == 200:
                    tc_data = tc_resp.json()
                    tc_items = tc_data.get("_embedded", {}).get(
                        "technicalCompetenceListInfoList", []
                    )
                    for item in tc_items:
                        # Since we don't have descriptions in list, we'd need another call.
                        # For simplicity, we skip fallback detail fetch to avoid complex N+1
                        # unless absolutely necessary.
                        pass
            except Exception:
                pass

        return SkillsProfile(
            technical_skills=tech_skills, knowledge=knowledge, soft_skills=soft_skills
        )



# Helper function backwards compatibility with app.py caching
@st.cache_data(ttl=3600, show_spinner=False)
def get_skills_for_job(job_title: str, lang: str = "en") -> Optional[Dict]:
    try:
        api_key = st.secrets["vdab"]["api_key"]
    except (KeyError, FileNotFoundError):
        return None

    if not api_key or api_key == "YOUR_X_IBM_CLIENT_ID_HERE":
        return None

    service = VDABApiService(api_key=api_key)
    profile = service.search_profile(job_title, lang)
    if not profile:
        return None

    skills = service.get_skills(profile.id, profile.release_number, lang)
    return skills.model_dump()


def is_api_configured() -> bool:
    """Return True only if a real (non-placeholder) API key is set."""
    try:
        api_key = st.secrets["vdab"]["api_key"]
        return bool(api_key and api_key != "YOUR_X_IBM_CLIENT_ID_HERE")
    except (KeyError, FileNotFoundError):
        return False
