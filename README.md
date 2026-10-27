# AI Job Hunter Agent

A Streamlit app that searches for recent LinkedIn job posts, tries to identify a recruiter for each job, and prepares a draft outreach message. You can run one search at a time through the Python workflow or upload a batch of searches in the app.

## What it does

For each job title and location, the workflow:

1. Uses Tavily to search LinkedIn job-post URLs from the past week, requesting up to three results.
2. Uses a Groq-hosted language model to extract the company, job title, and job-post URL from the search results.
3. Uses Tavily to extract text from each job page and checks for a hiring-team section.
4. If the job page does not yield a recruiter, searches LinkedIn profile results for a recruiter associated with the company and role.
5. Returns the job and recruiter details. The Streamlit app also creates a draft outreach message and lets you download the batch results as a CSV.

The searches and extraction are best-effort: results depend on what Tavily can find and access, and the app does not verify that a job is still open or that a suggested recruiter is currently responsible for it. Review job and profile links before contacting anyone.

## Requirements

- Python
- API keys for [Groq](https://console.groq.com/) and [Tavily](https://tavily.com/)

Install the project dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

For Excel (`.xlsx`) uploads, also install the Excel reader:

```powershell
python -m pip install openpyxl
```

## Configure API keys

Create a `.env` file in the project directory:

```dotenv
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
```

Keep the `.env` file private; it is excluded from version control by `.gitignore`.

## Run the Streamlit app

```powershell
streamlit run app.py
```

Upload a `.csv` or `.xlsx` file with these column headers:

| Job Title | Location |
|---|---|
| Data Scientist | Berlin |
| Machine Learning Engineer | Amsterdam |

The app previews the input, processes each row when you select **Run Batch Search**, displays the results, and provides a CSV download. If a column is missing, the app uses `Data Scientist` for the job title or `Berlin` for the location.

## Run the workflow from the command line

`agent_core.py` also contains the workflow without the Streamlit interface. Run it directly to use its built-in example search:

```powershell
python agent_core.py
```

To use it from another Python file:

```python
from agent_core import run_workflow

results = run_workflow("Data Scientist", "Berlin")
print(results)
```

The returned list contains dictionaries with `company`, `job_title`, `job_post_url`, `recruiter_name`, and `profile_url`.

## Project files

- `app.py` — Streamlit batch-upload interface and outreach-message drafts.
- `agent_core.py` — job search, recruiter lookup, and workflow logic.
- `requirements.txt` — Python package dependencies.
