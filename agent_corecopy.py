import os
import json
from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# --- STEP 1: FIND THE JOBS ---
def find_jobs(role: str, location: str) -> list[dict]:
    print(f"🔍 [Step 1] Searching for jobs: {role} in {location}...")
    
    query = f'site:linkedin.com/jobs/view "{role}" "{location}"'
    
    try:
        response = tavily_client.search(query=query, max_results=5, time_range="week")
        
        raw_results = ""
        for i, res in enumerate(response.get("results", []), 1):
            raw_results += f"Result {i}:\nTitle: {res.get('title')}\nURL: {res.get('url')}\nSnippet: {res.get('content')[:500]}\n\n"
            
        if not raw_results:
            return []

        # Ask LLM to extract the job info AND look for a recruiter name in the snippet
        prompt = f"""Extract the company name, job title, and job URL from these search results.
        
        ALSO: Look carefully in the snippet for any mention of the hiring team or recruiter (e.g., "Meet the hiring team", "Job poster", "Hiring Manager").
        If you find a recruiter's name in the snippet, extract it.
        
        Search Results:
        {raw_results}
        
        Return a JSON list of objects with keys: 'company', 'job_title', 'job_post_url', 'snippet_recruiter'.
        If no recruiter is found in the snippet, use 'Unknown' for snippet_recruiter.
        """
        
        llm_resp = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0
        )
        
        extracted = json.loads(llm_resp.choices[0].message.content)
        jobs = extracted if isinstance(extracted, list) else extracted.get("jobs", extracted.get("results", []))
        return jobs

    except Exception as e:
        print(f"Error finding jobs: {e}")
        return []


# --- STEP 2: FIND THE RECRUITERS ---
def find_recruiter(company: str, job_title: str, snippet_recruiter: str = "Unknown") -> dict:
    # IF the job post already told us the recruiter, use that!
    if snippet_recruiter and snippet_recruiter != "Unknown":
        print(f"✅ Found recruiter directly in job post: {snippet_recruiter}")
        # We still need to search for their profile URL
        return find_recruiter_profile(company, snippet_recruiter)
    
    clean_title = " ".join(job_title.split()[:2]) 
    print(f"🔍 [Step 2] Searching for recruiters at: {company} for role: {clean_title}...")
    
    if company == "Unknown":
        return {"recruiter_name": "Unknown", "profile_url": "Unknown"}

    query = f'site:linkedin.com/in "{company}" "{clean_title}" "Recruiter" OR "Talent Acquisition"'
    
    try:
        response = tavily_client.search(query=query, max_results=5)
        return extract_recruiter_from_search(response, company)

    except Exception as e:
        print(f"Error finding recruiter: {e}")
        return {"recruiter_name": "Error", "profile_url": "Error"}

def find_recruiter_profile(company: str, recruiter_name: str) -> dict:
    query = f'site:linkedin.com/in "{recruiter_name}" "{company}"'
    try:
        response = tavily_client.search(query=query, max_results=5)
        return extract_recruiter_from_search(response, company, required_name=recruiter_name)
    except:
        return {"recruiter_name": recruiter_name, "profile_url": "Unknown"}

def extract_recruiter_from_search(response: dict, company: str, required_name: str = None) -> dict:
    raw_results = ""
    for i, res in enumerate(response.get("results", []), 1):
        raw_results += f"Result {i}:\nTitle: {res.get('title')}\nURL: {res.get('url')}\nSnippet: {res.get('content')[:300]}\n\n"
        
    if not raw_results:
        return {"recruiter_name": "No recruiter found", "profile_url": "None"}

    name_rule = f"ONLY extract the profile if the name is '{required_name}'." if required_name else ""

    prompt = f"""Extract the recruiter's name and LinkedIn profile URL from these search results.
    
    {name_rule}
    
    CRITICAL RULES:
    1. You must ONLY return a profile if the snippet explicitly proves this person works at "{company}".
    2. You must ONLY return a profile if the snippet or their title explicitly says they are a "Recruiter", "Talent Acquisition", "Hiring Manager", or "Talent Partner". 
    3. If they are an "Engineer", "Data Scientist", "Manager" (non-hiring), or "Developer", return 'Unknown'.
    4. If you are not 100% sure, return 'Unknown'.
    
    Search Results:
    {raw_results}
    
    Return a JSON object with keys: 'recruiter_name', 'profile_url'.
    """
    
    llm_resp = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0
    )
    
    result = json.loads(llm_resp.choices[0].message.content)
    
    # Sometimes the LLM returns a list instead of a dict. Let's fix that.
    if isinstance(result, list) and len(result) > 0:
        return result[0]  # Just take the first item
    elif isinstance(result, dict):
        return result
    else:
        return {"recruiter_name": "Unknown", "profile_url": "Unknown"}
    
# --- THE MAIN WORKFLOW ---
def run_workflow(role: str, location: str):
    print(f"\n🎯 Starting Workflow for {role} in {location}...")
    
    # Step 1: Get Jobs
    jobs = find_jobs(role, location)
    if not jobs:
        print("❌ No jobs found.")
        return []
        
    print(f"✅ Found {len(jobs)} job(s).")
    
    final_results = []
    
    # Step 2: For each job, find the recruiter
    for job in jobs:
        company = job.get("company", "Unknown")
        job_title = job.get("job_title", role)
        job_url = job.get("job_post_url", "")
        
        if company == "Unknown":
            continue
            
        snippet_recruiter = job.get("snippet_recruiter", "Unknown")
        recruiter_info = find_recruiter(company, job_title, snippet_recruiter)
        
        final_results.append({
            "company": company,
            "job_title": job_title,
            "job_post_url": job_url,
            "recruiter_name": recruiter_info.get("recruiter_name", "Unknown"),
            "profile_url": recruiter_info.get("profile_url", "Unknown")
        })
        
    print("\n✅ Workflow Finished!")
    return final_results

if __name__ == "__main__":
    results = run_workflow("Data Scientist", "Berlin")
    print(json.dumps(results, indent=2))