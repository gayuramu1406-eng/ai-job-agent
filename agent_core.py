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
        response = tavily_client.search(query=query, max_results=3, time_range="week")
        
        raw_results = ""
        for i, res in enumerate(response.get("results", []), 1):
            raw_results += f"Result {i}:\nTitle: {res.get('title')}\nURL: {res.get('url')}\nSnippet: {res.get('content')[:500]}\n\n"
            
        if not raw_results:
            return []

        prompt = f"""Extract the company name, job title, and job URL from these search results.
        Return a JSON list of objects with keys: 'company', 'job_title', 'job_post_url'.
        If the company name is not clear, use 'Unknown'.
        
        Search Results:
        {raw_results}
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


# --- STEP 1.5: EXTRACT DIRECTLY FROM JOB PAGE ---
def extract_from_job_page(job_url: str) -> dict:
    """Scrapes the job page directly to look for the 'Meet the hiring team' section."""
    print(f"📄 [Step 1.5] Scraping Job Page directly: {job_url}")
    
    if not job_url or job_url == "Unknown":
        return {"recruiter_name": "Unknown", "profile_url": "Unknown"}
        
    try:
        # Tavily extract pulls the clean text from the URL
        response = tavily_client.extract(urls=[job_url])
        
        if not response.get("results"):
            return {"recruiter_name": "Unknown", "profile_url": "Unknown"}
            
        page_text = response["results"][0].get("raw_content", "")
        
        # Look for keywords indicating the hiring team is on the page
        keywords = ["Meet the hiring team", "Job poster", "Hiring team", "直接发消息给"]
        has_hiring_team = any(kw.lower() in page_text.lower() for kw in keywords)
        
        if not has_hiring_team:
            return {"recruiter_name": "Unknown", "profile_url": "Unknown"}
            
        # If we found the hiring team section, use the LLM to extract the name
        prompt = f"""Read the following text from a LinkedIn job post. 
        Find the name and profile URL of the person under the "Meet the hiring team" or "Job poster" section.
        
        Text:
        {page_text[:5000]} 
        
        Return a JSON object with keys: 'recruiter_name', 'profile_url'.
        If you cannot find a specific name or URL, return 'Unknown' for both.
        """
        
        llm_resp = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0
        )
        
        extracted = json.loads(llm_resp.choices[0].message.content)
        
        # If we found a name but not a URL, let's find the URL
        if extracted.get("recruiter_name") != "Unknown" and extracted.get("profile_url") == "Unknown":
            name = extracted.get("recruiter_name")
            print(f"🔍 Found name '{name}', but no URL. Searching for profile URL...")
            url_search = tavily_client.search(query=f'site:linkedin.com/in "{name}"', max_results=1)
            if url_search.get("results"):
                extracted["profile_url"] = url_search["results"][0].get("url", "Unknown")
                print(f"✅ Found URL: {extracted['profile_url']}")
                
        return extracted
        
    except Exception as e:
        print(f"Error scraping job page: {e}")
        return {"recruiter_name": "Unknown", "profile_url": "Unknown"}


# --- STEP 2: FALLBACK RECRUITER SEARCH ---
def find_recruiter(company: str, job_title: str) -> dict:
    clean_title = " ".join(job_title.split()[:2]) 
    print(f"🔍 [Step 2] Searching for recruiters at: {company} for role: {clean_title}...")
    
    if company == "Unknown":
        return {"recruiter_name": "Unknown", "profile_url": "Unknown"}

    query = f'site:linkedin.com/in "{company}" "{clean_title}" "Recruiter" OR "Talent Acquisition"'
    
    try:
        response = tavily_client.search(query=query, max_results=3)
        return extract_recruiter_from_search(response, company)

    except Exception as e:
        print(f"Error finding recruiter: {e}")
        return {"recruiter_name": "Error", "profile_url": "Error"}


def extract_recruiter_from_search(response: dict, company: str) -> dict:
    raw_results = ""
    for i, res in enumerate(response.get("results", []), 1):
        raw_results += f"Result {i}:\nTitle: {res.get('title')}\nURL: {res.get('url')}\nSnippet: {res.get('content')[:300]}\n\n"
        
    if not raw_results:
        return {"recruiter_name": "Unknown", "profile_url": "Unknown"}

    prompt = f"""Extract the recruiter's name and LinkedIn profile URL from these search results.
    
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
    
    # Safety check for list format
    if isinstance(result, list) and len(result) > 0:
        return result[0]
    elif isinstance(result, dict):
        return result
    else:
        return {"recruiter_name": "Unknown", "profile_url": "Unknown"}


# --- THE MAIN WORKFLOW ---
def run_workflow(role: str, location: str):
    print(f"\n🎯 Starting Workflow for {role} in {location}...")
    
    jobs = find_jobs(role, location)
    if not jobs:
        print("❌ No jobs found.")
        return []
        
    print(f"✅ Found {len(jobs)} job(s).")
    
    final_results = []
    
    for job in jobs:
        company = job.get("company", "Unknown")
        job_title = job.get("job_title", role)
        job_url = job.get("job_post_url", "")
        
        if company == "Unknown" or not job_url:
            continue
            
        # 1. Try to get recruiter from the job page directly
        job_page_info = extract_from_job_page(job_url)
        
        if job_page_info.get("recruiter_name") != "Unknown":
            recruiter_info = job_page_info
        else:
            # 2. Fallback to Web Search
            recruiter_info = find_recruiter(company, job_title)
        
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