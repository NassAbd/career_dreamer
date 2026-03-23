from typing import List

import polars as pl

from src.schemas import CareerSequence, PreviousRoleProbability, TransitionProbability


class DataService:
    def __init__(self, df: pl.DataFrame):
        self.df = df

    def get_job_list(self) -> List[str]:
        return self.df["matched_label"].unique().sort().to_list()

    def get_transitions(self, job_title: str) -> List[TransitionProbability]:
        transitions = self.df.filter(
            (pl.col("matched_label") == job_title) & (pl.col("next_job_label").is_not_null())
        )
        total = transitions.shape[0]
        if total == 0:
            return []

        probas = (
            transitions.group_by("next_job_label")
            .agg(pl.len().alias("nb"))
            .with_columns((pl.col("nb") / total * 100).round(1).alias("%"))
            .sort("%", descending=True)
            .head(5)
        )

        return [
            TransitionProbability(
                next_job_label=row["next_job_label"], probability_percent=row["%"]
            )
            for row in probas.iter_rows(named=True)
        ]

    def get_previous_roles(self, job_title: str) -> List[PreviousRoleProbability]:
        origins = self.df.filter(
            (pl.col("matched_label") == job_title) & (pl.col("previous_job_label").is_not_null())
        )
        total = origins.shape[0]
        if total == 0:
            return []

        previous_roles = (
            origins.group_by("previous_job_label")
            .agg(pl.len().alias("nb"))
            .with_columns((pl.col("nb") / total * 100).round(1).alias("%"))
            .sort("%", descending=True)
            .head(5)
        )

        return [
            PreviousRoleProbability(
                previous_job_label=row["previous_job_label"], probability_percent=row["%"]
            )
            for row in previous_roles.iter_rows(named=True)
        ]

    def get_career_sequences(self, target_job: str) -> List[CareerSequence]:
        origins = self.df.filter(
            (pl.col("matched_label") == target_job) & (pl.col("previous_job_label").is_not_null())
        )
        if origins.shape[0] == 0:
            return []

        people_in_job = origins.select(["person_id", "previous_job_label"])

        two_step_paths = (
            self.df.join(people_in_job, on="person_id", how="inner")
            .filter(
                (pl.col("matched_label") == pl.col("previous_job_label_right"))
                & (pl.col("previous_job_label").is_not_null())
            )
            .select(
                [
                    pl.col("previous_job_label").alias("step_1"),
                    pl.col("matched_label").alias("step_2"),
                ]
            )
        )

        if two_step_paths.shape[0] == 0:
            return []

        path_counts = (
            two_step_paths.group_by(["step_1", "step_2"])
            .agg(pl.len().alias("count"))
            .sort("count", descending=True)
            .head(5)
        )

        return [
            CareerSequence(
                step_1=row["step_1"],
                step_2=row["step_2"],
                target_job=target_job,
                count=row["count"],
            )
            for row in path_counts.iter_rows(named=True)
        ]
