import streamlit as st
import polars as pl

# --- Internationalization ---
translations = {
    "fr": {
        "page_title": "🇧🇪 Career Dreamer (Version Belgique)",
        "page_header": "Explorez les transitions professionnelles réelles basées sur les données de l'[UGent](https://huggingface.co/datasets/aida-ugent/JobHop).",
        "selectbox_label": "Quel est votre métier actuel ? (en anglais)",
        "subheader_text": "Où vont les {selected_job} ?",
        "no_data_message": "Pas assez de données pour ce métier spécifique.",
        "language_option": "Langue",
    },
    "en": {
        "page_title": "🇧🇪 Career Dreamer (Belgium Version)",
        "page_header": "Explore real career transitions based on [UGent](https://huggingface.co/datasets/aida-ugent/JobHop) data.",
        "selectbox_label": "What is your current job? (in English)",
        "subheader_text": "Where do {selected_job}s go?",
        "no_data_message": "Not enough data for this specific job.",
        "language_option": "Language",
    },
}

# --- Language Selection ---
if 'lang' not in st.session_state:
    st.session_state.lang = 'fr'  # Default language

# Create a sidebar for language selection
st.sidebar.title(translations[st.session_state.lang]["language_option"])
lang_choice = st.sidebar.radio("", ('Français', 'English'), index=0 if st.session_state.lang == 'fr' else 1)

if lang_choice == 'Français':
    st.session_state.lang = 'fr'
else:
    st.session_state.lang = 'en'

# Get the translated texts
T = translations[st.session_state.lang]


st.set_page_config(page_title="Career Dreamer BE", layout="centered")

# Using cache to avoid slowing down the interface
@st.cache_data
def load_data():
    """
    Loads and preprocesses the JobHop dataset.
    """
    df = pl.read_csv("hf://datasets/aida-ugent/JobHop/JobHop_train.csv")
    
    # Correction here: we extract and work directly on the column
    # str.extract_groups returns a struct type column
    df = df.with_columns([
        pl.col("start_date")
        .str.extract_groups(r"Q(?P<q>\d) (?P<y>\d{4})")
        .alias("temp_struct")
    ])
    
    # Now we can access the fields of 'temp_struct'
    df = df.with_columns([
        (
            pl.col("temp_struct").struct.field("y").cast(pl.Int32) + 
            (pl.col("temp_struct").struct.field("q").cast(pl.Int32) - 1) * 0.25
        ).alias("start_val")
    ]).drop("temp_struct") # We clean up the temporary column
    
    # The rest of the code...
    df_model = df.select([
        "matched_label", "matched_code", "person_id", "start_val"
    ]).sort(["person_id", "start_val"])

    # Add both next_job (forward) and previous_job (backward) for bidirectional analysis
    df_model = df_model.with_columns([
        pl.col("matched_label").shift(-1).over("person_id").alias("next_job_label"),
        pl.col("matched_label").shift(1).over("person_id").alias("previous_job_label")
    ])
    
    return df_model

df = load_data()

st.title(T["page_title"])
st.write(T["page_header"])

# --- Analysis Mode Selection ---
st.markdown("---")
mode_labels = {
    "fr": {"forward": "🔮 Où vont-ils ?", "reverse": "🔍 D'où viennent-ils ?"},
    "en": {"forward": "🔮 Where do they go?", "reverse": "🔍 Where do they come from?"}
}

analysis_mode = st.radio(
    "Mode d'analyse / Analysis Mode:",
    options=["forward", "reverse"],
    format_func=lambda x: mode_labels[st.session_state.lang][x],
    horizontal=True
)

st.markdown("---")

# Unique job list for the dropdown menu
job_list = df["matched_label"].unique().sort().to_list()

selected_job = st.selectbox(T["selectbox_label"], job_list)

if selected_job:
    if analysis_mode == "forward":
        # FORWARD ANALYSIS: Where do people go FROM this job?
        transitions = df.filter(
            (pl.col("matched_label") == selected_job) & 
            (pl.col("next_job_label").is_not_null())
        )
        total = transitions.shape[0]
        
        if total > 0:
            probas = (
                transitions.group_by("next_job_label")
                .agg(pl.count().alias("nb"))
                .with_columns((pl.col("nb") / total * 100).round(1).alias("%"))
                .sort("%", descending=True)
                .head(5)
            )
            
            st.subheader(T["subheader_text"].format(selected_job=selected_job))
            st.dataframe(probas.select(["next_job_label", "%"]), hide_index=True)
            
            # Visual bonus
            st.bar_chart(data=probas.to_pandas(), x="next_job_label", y="%")
        else:
            st.info(T["no_data_message"])
    
    else:
        # REVERSE ANALYSIS: Where do people come FROM to reach this job?
        origins = df.filter(
            (pl.col("matched_label") == selected_job) & 
            (pl.col("previous_job_label").is_not_null())
        )
        total = origins.shape[0]
        
        if total > 0:
            # Most common previous roles
            previous_roles = (
                origins.group_by("previous_job_label")
                .agg(pl.count().alias("nb"))
                .with_columns((pl.col("nb") / total * 100).round(1).alias("%"))
                .sort("%", descending=True)
                .head(5)
            )
            
            # Subheader
            if st.session_state.lang == "fr":
                st.subheader(f"🔍 D'où viennent les {selected_job} ?")
                st.markdown(f"**Rôles précédents les plus courants** ({total} transitions analysées)")
            else:
                st.subheader(f"🔍 Where do {selected_job}s come from?")
                st.markdown(f"**Most Common Previous Roles** ({total} transitions analyzed)")
            
            st.dataframe(previous_roles.select(["previous_job_label", "%"]), hide_index=True)
            st.bar_chart(data=previous_roles.to_pandas(), x="previous_job_label", y="%")
            
            # Show typical 2-step career sequences
            st.markdown("---")
            if st.session_state.lang == "fr":
                st.markdown("**📊 Séquences de carrière typiques (2 étapes)**")
                st.caption("Les parcours les plus fréquents menant à ce métier")
            else:
                st.markdown("**📊 Typical Career Sequences (2 steps)**")
                st.caption("Most common paths leading to this role")
            
            # Find 2-step sequences: Job A → Job B → selected_job
            # First, get all people in selected_job with their previous job
            people_in_job = origins.select(["person_id", "previous_job_label"])
            
            # Then find what job they had before that
            two_step_paths = df.join(
                people_in_job,
                on="person_id",
                how="inner"
            ).filter(
                (pl.col("matched_label") == pl.col("previous_job_label")) &
                (pl.col("previous_job_label_right").is_not_null())
            ).select([
                pl.col("previous_job_label_right").alias("step_1"),
                pl.col("matched_label").alias("step_2"),
            ])
            
            if two_step_paths.shape[0] > 0:
                path_counts = (
                    two_step_paths.group_by(["step_1", "step_2"])
                    .agg(pl.count().alias("count"))
                    .sort("count", descending=True)
                    .head(5)
                )
                
                for row in path_counts.iter_rows(named=True):
                    st.markdown(f"- **{row['step_1']}** → **{row['step_2']}** → **{selected_job}** ({row['count']} personnes / people)")
            else:
                if st.session_state.lang == "fr":
                    st.info("Données insuffisantes pour les séquences de 2 étapes.")
                else:
                    st.info("Insufficient data for 2-step sequences.")
        else:
            st.info(T["no_data_message"])

