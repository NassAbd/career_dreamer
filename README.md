# Career Dreamer 🇧🇪

This repository contains a Streamlit application that lets you explore real career transitions in Belgium.

## About the Application

"Career Dreamer" is a web application that shows you the most likely career paths from a given starting job. You can select your current job from a list, and the application will display the top 5 most common next jobs based on real-world data.

The application is available in both English and French.

## Data Source

The career transition data comes from the [JobHop dataset](https://huggingface.co/datasets/aida-ugent/JobHop) from Ghent University (UGent). This dataset contains anonymized career data from individuals in Belgium.

## How to Run the Application

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/NassAbd/career_dreamer.git
    cd career_dreamer
    ```

2.  **Install/Sync dependencies:**
    This project uses `uv` for environment management and dependency isolation (Zero-Global).
    ```bash
    uv sync
    ```

3.  **Run the Streamlit app:**
    ```bash
    uv run streamlit run app.py
    ```

    The application will then be available in your web browser, usually at `http://localhost:8501`.

## Technologies Used

*   **Streamlit:** For building the interactive web application.
*   **Polars:** For high-performance data manipulation.
*   **uv:** For project management and environment isolation.
*   **Ruff/Pytest:** For linting and TDD.

## Engineering Guidelines

This project follows a "Zero-Global" philosophy. Use `uv` for all operations.

1. **Linting**: Ensure code passes ruff before committing:
   ```bash
   uv run ruff check .
   ```
2. **Testing**: Run tests regularly:
   ```bash
   uv run pytest
   ```
3. **Execution**: Always wrap commands in `uv run`.
4. **Sanity Check**: Run `./docs/sanity_check.sh` to auditing environment health.
