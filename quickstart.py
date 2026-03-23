import marimo

__generated_with = "0.17.6"
app = marimo.App(width="medium")


@app.cell
def _():
    import polars as pl

    # Login using e.g. `huggingface-cli login` to access this dataset
    splits = {
        "train": "JobHop_train.csv",
        "validation": "JobHop_val.csv",
        "test": "JobHop_test.csv",
    }
    df = pl.read_csv("hf://datasets/aida-ugent/JobHop/" + splits["train"])
    return df, pl


@app.cell
def _(df):
    print(f"Shape: {df.shape}")
    return


@app.cell
def _(df, pl):
    # 2 rows where 'matched_label' = 'resource manager'
    df.filter(pl.col("matched_label") == "resource manager").head(3)
    # matched_code is the same
    return


@app.cell
def _(pl):
    # transform "QX YYYY" dates to numeric values
    def parse_quarterly_dates(col_name):
        # On extrait les groupes dans une colonne temporaire de type Struct
        extracted = pl.col(col_name).str.extract_groups(r"Q(?P<quarter>\d) (?P<year>\d{4})")

        # On accède aux champs de la structure via .struct.field()
        return (
            extracted.struct.field("year").cast(pl.Int32)
            + (extracted.struct.field("quarter").cast(pl.Int32) - 1) * 0.25
        )

    return (parse_quarterly_dates,)


@app.cell
def _(df, parse_quarterly_dates):
    df_cleaned_dates = df.with_columns(
        [
            parse_quarterly_dates("start_date").alias("start_val"),
            parse_quarterly_dates("end_date").alias("end_val"),
        ]
    )

    df_cleaned_dates.head()
    return (df_cleaned_dates,)


@app.cell
def _(df_cleaned_dates, pl):
    # duration of job per person
    df_cleaned_dates_duration = df_cleaned_dates.with_columns(
        (pl.col("end_val") - pl.col("start_val")).alias("duration_years")
    ).sort(["person_id", "start_val"])

    df_cleaned_dates_duration.head()
    return (df_cleaned_dates_duration,)


@app.cell
def _(df_cleaned_dates_duration, pl):
    # identify the next job (hop)
    df_cleaned_dates_duration_hop = df_cleaned_dates_duration.with_columns(
        pl.col("matched_label").shift(-1).over("person_id").alias("next_job_label"),
        pl.col("matched_code").shift(-1).over("person_id").alias("next_job_code"),
    )

    df_cleaned_dates_duration_hop.head()
    return (df_cleaned_dates_duration_hop,)


@app.cell
def _(df_cleaned_dates_duration_hop, pl):
    # check missing values
    _ = df_cleaned_dates_duration_hop.select([pl.all().null_count()])

    # Remove useless expression
    return


@app.cell
def _(df_cleaned_dates_duration_hop, pl):
    df_model = df_cleaned_dates_duration_hop.filter(
        pl.col("next_job_label").is_not_null()
        & pl.col("matched_code").is_not_null()
        & pl.col("start_val").is_not_null()
    )

    print(f"Rows used for predictions : {df_model.shape[0]}")
    return (df_model,)


@app.cell
def _(df_model, pl):
    def get_next_job_probas(current_job_title, dataframe, top_n=5):
        # 1. Filtrer pour le job actuel
        transitions = dataframe.filter(pl.col("matched_label") == current_job_title)

        total_transitions = transitions.shape[0]

        if total_transitions == 0:
            return "Désolé, ce métier n'est pas dans notre base de données belge."

        # 2. Calculer les probabilités
        probas = (
            transitions.group_by("next_job_label")
            .agg(pl.count().alias("count"))
            .with_columns((pl.col("count") / total_transitions * 100).round(2).alias("probability"))
            .sort("probability", descending=True)
            .head(top_n)
        )

        return probas

    # Test sur ton exemple : "ICT help desk agent"
    print(get_next_job_probas("health and safety officer", df_model))
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
