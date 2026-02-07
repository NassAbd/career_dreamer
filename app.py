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

    df_model = df_model.with_columns(
        pl.col("matched_label").shift(-1).over("person_id").alias("next_job_label")
    ).filter(pl.col("next_job_label").is_not_null())
    
    return df_model

df = load_data()

st.title(T["page_title"])
st.write(T["page_header"])

# Unique job list for the dropdown menu
job_list = df["matched_label"].unique().sort().to_list()

selected_job = st.selectbox(T["selectbox_label"], job_list)

if selected_job:
    # Probability calculation
    transitions = df.filter(pl.col("matched_label") == selected_job)
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
        
        # Small visual bonus
        st.bar_chart(data=probas.to_pandas(), x="next_job_label", y="%")
    else:
        st.info(T["no_data_message"])
