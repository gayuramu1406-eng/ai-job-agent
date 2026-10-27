# AI Job Hunter Agent

A tool-using AI agent that finds recruiters hiring for specific roles on LinkedIn and drafts outreach messages.

## What it does

1. User enters a **Job Role** and **Location** in the Streamlit UI
2. The agent searches LinkedIn Jobs (via Tavily) for the past week
3. Extracts company names and job URLs using an LLM
4. For each company, searches for the hiring recruiter's LinkedIn profile
5. Drafts a personalized outreach message ready to copy-paste

No scraping. No LinkedIn login. No risk of account bans.

## Architecture
