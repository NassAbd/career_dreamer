import pandas as pd
import polars as pl
import streamlit as st

import vdab_api_service as vdab
from src.data_service import DataService

# --- Internationalization ---
translations = {
    "fr": {
        "page_title": "🇧🇪 Career Dreamer (Version Belgique)",
        "page_header": "Explorez les transitions professionnelles réelles basées sur les données de l'[UGent](https://huggingface.co/datasets/aida-ugent/JobHop).",
        "selectbox_label": "Quel est votre métier actuel ? (en anglais)",
        "subheader_text": "Où vont les {selected_job} ?",
        "no_data_message": "Pas assez de données pour ce métier spécifique.",
        "language_option": "Langue",
        # Skills gap section
        "show_skills": "🔍 Voir les compétences requises",
        "skills_gap_title": "Analyse du gap de compétences",
        "skills_col_have": "✅ Compétences déjà acquises",
        "skills_col_need": "🆕 Compétences à acquérir",
        "technical_skills": "🛠️ Compétences techniques",
        "knowledge_label": "📚 Connaissances",
        "soft_skills_label": "🤝 Compétences comportementales",
        "no_skills_found": "Aucune compétence trouvée dans le registre VDAB pour ce métier.",
        "api_not_configured": "💡 **Conseil** : Configurez votre clé API VDAB dans "
        "`.streamlit/secrets.toml` pour afficher les compétences requises pour chaque métier.",
        "loading_skills": "Chargement des compétences depuis le registre VDAB…",
        "skills_identical": "Les profils de compétences sont identiques.",
    },
    "en": {
        "page_title": "🇧🇪 Career Dreamer (Belgium Version)",
        "page_header": "Explorez les transitions professionnelles réelles "
        "basées sur les données de l'[UGent](https://huggingface.co/datasets/aida-ugent/JobHop).",
        "selectbox_label": "What is your current job? (in English)",
        "subheader_text": "Where do {selected_job}s go?",
        "no_data_message": "Not enough data for this specific job.",
        "language_option": "Language",
        # Skills gap section
        "show_skills": "🔍 Show required skills",
        "skills_gap_title": "Skills Gap Analysis",
        "skills_col_have": "✅ Skills you already have",
        "skills_col_need": "🆕 Skills to acquire",
        "technical_skills": "🛠️ Technical Skills",
        "knowledge_label": "📚 Knowledge",
        "soft_skills_label": "🤝 Soft Skills",
        "no_skills_found": "No skills found in the VDAB registry for this job title.",
        "api_not_configured": "💡 **Tip**: Configure your VDAB API key in "
        "`.streamlit/secrets.toml` to display required skills for each career transition.",
        "loading_skills": "Loading skills from the VDAB registry…",
        "skills_identical": "Both jobs share the same skill profile.",
    },
}

# --- Language Selection ---
if "lang" not in st.session_state:
    st.session_state.lang = "fr"

st.sidebar.title(translations[st.session_state.lang]["language_option"])
lang_choice = st.sidebar.radio(
    "Language",
    ("Français", "English"),
    index=0 if st.session_state.lang == "fr" else 1,
    label_visibility="hidden",
)

if lang_choice == "Français":
    st.session_state.lang = "fr"
else:
    st.session_state.lang = "en"

T = translations[st.session_state.lang]
api_lang = st.session_state.lang  # 'en' or 'fr'

st.set_page_config(page_title="Career Dreamer BE", layout="centered")


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------
@st.cache_resource
def get_data_service():
    """Loads and preprocesses the JobHop dataset and wraps in DataService."""
    df = pl.read_csv("hf://datasets/aida-ugent/JobHop/JobHop_train.csv")

    df = df.with_columns(
        [pl.col("start_date").str.extract_groups(r"Q(?P<q>\d) (?P<y>\d{4})").alias("temp_struct")]
    )

    df = df.with_columns(
        [
            (
                pl.col("temp_struct").struct.field("y").cast(pl.Int32)
                + (pl.col("temp_struct").struct.field("q").cast(pl.Int32) - 1) * 0.25
            ).alias("start_val")
        ]
    ).drop("temp_struct")

    df_model = df.select(["matched_label", "matched_code", "person_id", "start_val"]).sort(
        ["person_id", "start_val"]
    )

    df_model = df_model.with_columns(
        [
            pl.col("matched_label").shift(-1).over("person_id").alias("next_job_label"),
            pl.col("matched_label").shift(1).over("person_id").alias("previous_job_label"),
        ]
    )

    return DataService(df_model)


data_svc = get_data_service()

st.title(T["page_title"])
st.write(T["page_header"])

# --- Analysis Mode Selection ---
st.markdown("---")
mode_labels = {
    "fr": {"forward": "🔮 Où vont-ils ?", "reverse": "🔍 D'où viennent-ils ?"},
    "en": {"forward": "🔮 Where do they go?", "reverse": "🔍 Where do they come from?"},
}

analysis_mode = st.radio(
    "Mode d'analyse / Analysis Mode:",
    options=["forward", "reverse"],
    format_func=lambda x: mode_labels[st.session_state.lang][x],
    horizontal=True,
)

st.markdown("---")

job_list = data_svc.get_job_list()
selected_job = st.selectbox(T["selectbox_label"], job_list)


# ---------------------------------------------------------------------------
# Skills Gap UI helper
# ---------------------------------------------------------------------------
def _render_skill_pills(skills: list[str]) -> str:
    """Format a list of skills as space-separated pill-like spans (markdown-safe)."""
    if not skills:
        return "*—*"
    return "  \n".join(f"• {s}" for s in sorted(skills))


def _render_skills_gap(current_job: str, target_job: str, lang: str) -> None:
    """
    Render the skills gap analysis between two jobs using the VDAB API.
    Shows technical skills, knowledge, and soft skills in two columns.
    """
    with st.spinner(T["loading_skills"]):
        current_skills = vdab.get_skills_for_job(current_job, lang)
        target_skills = vdab.get_skills_for_job(target_job, lang)

    # Neither found → show info and bail
    if current_skills is None and target_skills is None:
        st.info(T["no_skills_found"])
        return

    # If only target is found, show the full target profile without gap
    if current_skills is None:
        current_skills = {"technical_skills": [], "knowledge": [], "soft_skills": []}

    if target_skills is None:
        st.info(T["no_skills_found"])
        return

    # Compute gap using sets
    cur_tech = set(current_skills.get("technical_skills", []))
    tgt_tech = set(target_skills.get("technical_skills", []))
    cur_know = set(current_skills.get("knowledge", []))
    tgt_know = set(target_skills.get("knowledge", []))
    cur_soft = set(current_skills.get("soft_skills", []))
    tgt_soft = set(target_skills.get("soft_skills", []))

    tech_have = sorted(cur_tech & tgt_tech)
    tech_need = sorted(tgt_tech - cur_tech)
    know_have = sorted(cur_know & tgt_know)
    know_need = sorted(tgt_know - cur_know)
    soft_have = sorted(cur_soft & tgt_soft)
    soft_need = sorted(tgt_soft - cur_soft)

    all_have = tech_have + know_have + soft_have
    all_need = tech_need + know_need + soft_need

    if not all_have and not all_need:
        st.info(T["skills_identical"])
        return

    col_have, col_need = st.columns(2)

    with col_have:
        st.markdown(f"**{T['skills_col_have']}**")

        if tech_have:
            st.markdown(f"*{T['technical_skills']}*")
            for s in tech_have:
                st.markdown(f"  • {s}")

        if know_have:
            st.markdown(f"*{T['knowledge_label']}*")
            for s in know_have:
                st.markdown(f"  • {s}")

        if soft_have:
            st.markdown(f"*{T['soft_skills_label']}*")
            for s in soft_have:
                st.markdown(f"  • {s}")

        if not all_have:
            st.markdown("*—*")

    with col_need:
        st.markdown(f"**{T['skills_col_need']}**")

        if tech_need:
            st.markdown(f"*{T['technical_skills']}*")
            for s in tech_need:
                st.markdown(f"  • {s}")

        if know_need:
            st.markdown(f"*{T['knowledge_label']}*")
            for s in know_need:
                st.markdown(f"  • {s}")

        if soft_need:
            st.markdown(f"*{T['soft_skills_label']}*")
            for s in soft_need:
                st.markdown(f"  • {s}")

        if not all_need:
            st.markdown("*—*")

    # Soft skills always shown full-width as a summary row
    all_target_soft = sorted(tgt_soft)
    if all_target_soft:
        st.markdown("---")
        st.caption(f"{T['soft_skills_label']}: " + " · ".join(all_target_soft))


# ---------------------------------------------------------------------------
# Main app logic
# ---------------------------------------------------------------------------
if selected_job:
    if analysis_mode == "forward":
        transitions = data_svc.get_transitions(selected_job)

        if transitions:
            # Prepare data for rendering
            data = [
                {"next_job_label": t.next_job_label, "%": t.probability_percent}
                for t in transitions
            ]
            probas_df = pd.DataFrame(data)

            st.subheader(T["subheader_text"].format(selected_job=selected_job))
            st.dataframe(probas_df, hide_index=True)
            st.bar_chart(data=probas_df, x="next_job_label", y="%")

            # --- Skills Gap Section ------------------------------------------
            st.markdown("---")

            if not vdab.is_api_configured():
                st.info(T["api_not_configured"])
            else:
                for row in transitions:
                    target_job = row.next_job_label
                    pct = row.probability_percent
                    with st.expander(f"{T['show_skills']} — **{target_job}** ({pct}%)"):
                        _render_skills_gap(selected_job, target_job, api_lang)

        else:
            st.info(T["no_data_message"])

    else:
        # REVERSE ANALYSIS: Where do people come FROM to reach this job?
        previous_roles = data_svc.get_previous_roles(selected_job)

        if previous_roles:
            data = [
                {"previous_job_label": r.previous_job_label, "%": r.probability_percent}
                for r in previous_roles
            ]
            probas_df = pd.DataFrame(data)

            if st.session_state.lang == "fr":
                st.subheader(f"🔍 D'où viennent les {selected_job} ?")
                st.markdown("**Rôles précédents les plus courants**")
            else:
                st.subheader(f"🔍 Where do {selected_job}s come from?")
                st.markdown("**Most Common Previous Roles**")

            st.dataframe(probas_df, hide_index=True)
            st.bar_chart(data=probas_df, x="previous_job_label", y="%")

            # 2-step career sequences
            st.markdown("---")
            if st.session_state.lang == "fr":
                st.markdown("**📊 Séquences de carrière typiques (2 étapes)**")
                st.caption("Les parcours les plus fréquents menant à ce métier")
            else:
                st.markdown("**📊 Typical Career Sequences (2 steps)**")
                st.caption("Most common paths leading to this role")

            sequences = data_svc.get_career_sequences(selected_job)

            if sequences:
                for seq in sequences:
                    st.markdown(
                        f"- **{seq.step_1}** → **{seq.step_2}** → **{seq.target_job}** "
                        f"({seq.count} personnes / people)"
                    )
            else:
                if st.session_state.lang == "fr":
                    st.info("Données insuffisantes pour les séquences de 2 étapes.")
                else:
                    st.info("Insufficient data for 2-step sequences.")
        else:
            st.info(T["no_data_message"])
