import streamlit as st
import pandas as pd
import time
from agent_core import run_workflow

st.set_page_config(page_title="AI Job Hunter - Batch", page_icon="🚀", layout="wide")

st.title("🚀 AI Job Hunter (Batch Mode)")
st.markdown("Upload an Excel file with `Job Title` and `Location` columns to run multiple searches at once.")

# --- 1. File Upload ---
uploaded_file = st.file_uploader("Upload your search criteria (Excel or CSV)", type=["xlsx", "csv"])

if uploaded_file is not None:
    # Read the file
    if uploaded_file.name.endswith('.csv'):
        df_input = pd.read_csv(uploaded_file)
    else:
        df_input = pd.read_excel(uploaded_file)
        
    st.write("### 📋 Input Data Preview")
    st.dataframe(df_input.head())
    
    if st.button("🚀 Run Batch Search (This may take a few minutes)", use_container_width=True):
        
        all_results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_rows = len(df_input)
        
        # --- 2. The Batch Loop ---
        for index, row in df_input.iterrows():
            job_title = row.get("Job Title", "Data Scientist")
            location = row.get("Location", "Berlin")
            
            status_text.text(f"Processing {index + 1}/{total_rows}: {job_title} in {location}...")
            
            try:
                # Run the agent for this single row
                results = run_workflow(job_title, location)
                
                # If the agent found jobs, add them to the master list
                if results:
                    for res in results:
                        recruiter_name = res.get("recruiter_name", "there")
                        company_name = res.get("company", "your company")
                        job_title_found = res.get("job_title", "the role")
                        
                        # Generate the personalized draft message
                        if recruiter_name != "Unknown":
                            draft_message = f"Hi {recruiter_name}, I saw you are hiring for the {job_title_found} role at {company_name}. I am very interested and have relevant experience in this domain. Have you found a suitable candidate yet?"
                        else:
                            draft_message = "Recruiter not found. Please check the job link manually."

                        all_results.append({
                            "Job Title (Search)": job_title,
                            "Location (Search)": location,
                            "Company": company_name,
                            "Job Title (Found)": job_title_found,
                            "Job Post URL": res.get("job_post_url", "Unknown"),
                            "Recruiter Name": recruiter_name,
                            "Recruiter Profile": res.get("profile_url", "Unknown"),
                            "Draft Message": draft_message
                        })
            except Exception as e:
                st.warning(f"Error processing {job_title}: {e}")
                
            # Update progress bar
            progress_bar.progress((index + 1) / total_rows)
            time.sleep(1) # Small delay to prevent UI freezing
            
        status_text.text("✅ Batch Processing Complete!")
        
        # --- 3. Display and Download Results ---
        if all_results:
            df_output = pd.DataFrame(all_results)
            st.write("### 🎯 Results")
            st.dataframe(df_output)
            
            # Convert to CSV for download
            csv = df_output.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv,
                file_name='job_search_results.csv',
                mime='text/csv',
                use_container_width=True
            )
        else:
            st.error("No results found for any of the criteria.")