import streamlit as st
from langchain_community.document_loaders import WebBaseLoader
from chains import Chain
from scraper import batch_scrape
from preprocess import preprocess_and_embed
from portfolio import Portfolio
import json
import os
from datetime import datetime
import pandas as pd
from utils import sanitize_text
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# Format portfolio links from ChromaDB query to match prompt structure
def format_portfolio_links(portfolio_links):
    if not portfolio_links:
        with open('app/filter_log.txt', 'a') as f:
            f.write(f"{datetime.now().isoformat()} - Warning: No portfolio links returned from query\n")
        return []
    flattened_links = []
    for meta_list in portfolio_links:
        for meta in meta_list:
            if isinstance(meta, dict) and 'links' in meta and isinstance(meta['links'], str):
                flattened_links.append(meta['links'])
    if not flattened_links:
        with open('app/filter_log.txt', 'a') as f:
            f.write(f"{datetime.now().isoformat()} - Warning: No valid portfolio links in query result\n")
        return []
    # Top 2 most relevant
    selected_links = flattened_links[:2]
    if len(selected_links) < 2:
        with open('app/filter_log.txt', 'a') as f:
            f.write(f"{datetime.now().isoformat()} - Only {len(selected_links)} portfolio links available (wanted 2); check query relevance\n")
    return selected_links

# Send email to recruiter
def send_email(to_email, subject, body, from_email="dimpleg2820@gmail.com"):
    cleaned_body = re.sub(r'^Subject:.*$\n?', '', body, flags=re.MULTILINE | re.IGNORECASE).strip()
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(cleaned_body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, st.secrets["GMAIL_PASSWORD"])
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        return "Email sent successfully!"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

st.title("Cold Email Generator for Tech Jobs")
st.set_page_config(layout="wide", page_title="Cold Email Generator", page_icon="📧")

# Initialize Portfolio
portfolio = Portfolio(file_path="app/resource/portfolio.csv")
portfolio.load_portfolio()

# Load companies.json for recruiting emails
companies_file = 'app/data/companies.json'
with open(companies_file, 'r') as f:
    companies_data = json.load(f)
company_emails = {comp['name']: comp.get('recruiting_email', 'dimplecs8530@gmail.com') for comp in companies_data['companies']}

# Initialize session state
if 'job_data' not in st.session_state:
    st.session_state.job_data = None
if 'formatted_links' not in st.session_state:
    st.session_state.formatted_links = None
if 'manual_email_body' not in st.session_state:
    st.session_state.manual_email_body = None
if 'batch_email_body' not in st.session_state:
    st.session_state.batch_email_body = None

# Fortune 500 scraping section
st.subheader("Extract Fortune 500 Companies")
if st.button("🔄 Extract Jobs for Fortune 500 Companies"):
    with st.spinner("Extracting jobs..."):
        jobs = batch_scrape(companies_file='app/data/companies.json', batch_size=10)
        if jobs:
            preprocess_and_embed(jobs_file='app/data/jobs_cache.json')
            st.success("Jobs extracted and cached successfully!")
        else:
            st.error("No jobs found. Check app/filter_log.txt and app/raw_jobs_log.txt.")

# Manual Job URL Input and Email Generation
st.subheader("Enter a Job URL")
with st.form(key="manual_job_form"):
    job_url = st.text_input("Paste a job URL from any job site (e.g., https://jobs.apple.com/...)")
    scrape_button = st.form_submit_button("🔄 Extract Job Details & Generate Email")
    if scrape_button and job_url:
        with st.spinner("Extracting job..."):
            try:
                chain = Chain()
                loader = WebBaseLoader([job_url])
                data = sanitize_text(loader.load().pop().page_content)
                with open('app/filter_log.txt', 'a') as f:
                    f.write(f"{datetime.now().isoformat()} - Scraping {job_url} completed, raw data length: {len(data)}, sample: {data[:200]}\n")
                jobs = chain.extract_jobs(data)
                with open('app/filter_log.txt', 'a') as f:
                    f.write(f"{datetime.now().isoformat()} - Extracted jobs: {jobs}\n")
                if jobs and isinstance(jobs, list) and len(jobs) > 0:
                    job_data = jobs[0]
                    if not job_data.get('title') and job_data.get('role'):
                        job_data['title'] = job_data['role']
                    elif not job_data.get('title'):
                        job_data['title'] = f"Job from {job_url}"
                    with open('app/filter_log.txt', 'a') as f:
                        f.write(f"{datetime.now().isoformat()} - Job data extracted: {job_data}\n")
                    skills = job_data.get('skills', [])
                    # Extract skills from description if empty
                    if not skills:
                        prompt_skills_fallback = PromptTemplate.from_template(
                            """
                            Extract a list of 5-10 technical skills and qualifications from this job description: {desc}
                            Return ONLY a JSON array like ["skill1", "skill2"]. No preamble.
                            """
                        )
                        chain_fallback = prompt_skills_fallback | chain.llm
                        fallback_res = chain_fallback.invoke({"desc": job_data.get('description', '')})
                        try:
                            json_parser = JsonOutputParser()
                            skills = json_parser.parse(fallback_res.content)
                        except:
                            skills = []  
                        if not skills:
                            # Default skills if no skills found
                            skills = ["software development", "data engineering"]
                    if not skills:
                        st.warning("No skills extracted from job description. Using default skills for portfolio query.")
                        skills = ["software development", "data engineering"]
                    
                    portfolio_links = portfolio.query_links(skills, job_data.get('description', ''))
                    formatted_links = format_portfolio_links(portfolio_links)
                    # Log retrieved links
                    with open('app/filter_log.txt', 'a') as f:
                        f.write(f"{datetime.now().isoformat()} - Retrieved portfolio links for skills {skills}: {formatted_links}\n")
                    st.session_state.job_data = job_data
                    st.session_state.formatted_links = formatted_links
                    # Generate email
                    st.session_state.manual_email_body = chain.generate_mail(job=job_data, links=formatted_links, skills=skills)
                else:
                    st.error("No job data extracted from the URL.")
                    with open('app/filter_log.txt', 'a') as f:
                        f.write(f"{datetime.now().isoformat()} - No job data extracted from {job_url}\n")
            except Exception as e:
                st.error(f"An Error Occurred: {e}")
                with open('app/filter_log.txt', 'a') as f:
                    f.write(f"{datetime.now().isoformat()} - Exception during scraping {job_url}: {str(e)}\n")

# Dropdown for recruiting emails
if st.session_state.job_data and st.session_state.manual_email_body:
    st.subheader("Send Email (Job Posting URL)")
    st.text_area("Email Preview:", value=st.session_state.manual_email_body, height=300, disabled=True)
    company_name = st.session_state.job_data.get('company_name', 'Unknown')
    recruiting_emails = {
        'Apple': 'applecareers@apple.com',
        'Walmart': 'talentacquisition@walmart.com',
        'Amazon': 'hiring@amazon.com',
        'UnitedHealth Group': 'Investor_Relations@uhc.com',
        'Unknown': 'recruiting@example.com'
    }
    recruiting = recruiting_emails.get(company_name, 'recruiting@example.com')
    email_options = [recruiting, 'dimplecs8530@gmail.com']
    selected_email = st.selectbox("Select recipient email", email_options, key="manual_email_select")
    
    if st.button("📧 Send Email", key="manual_send_button"):
        with st.spinner("Sending email..."):
            subject = f"Unlock Your Business Potential with GunnenAI - {st.session_state.job_data['title']}"
            result = send_email(selected_email, subject, st.session_state.manual_email_body)
            st.success(result)
else:
    st.write("Extract a job first to enable email sending.")

# Batch Job Selection and Email Generation
st.subheader("Generate Cold Email")
jobs_cache_file = 'app/data/jobs_cache.json'
if os.path.exists(jobs_cache_file):
    with open(jobs_cache_file, 'r') as f:
        jobs_cache = json.load(f)
    companies = list(jobs_cache.keys())
    if companies:
        selected_company = st.selectbox("Select a Company", companies)
        if selected_company and jobs_cache[selected_company]:
            job_titles = [job['title'] for job in jobs_cache[selected_company]]
            selected_job = st.selectbox("Select a Position", job_titles)
            if selected_job:
                job_data = next(job for job in jobs_cache[selected_company] if job['title'] == selected_job)
                st.write(f"**Job Title**: {job_data['title']}")
                st.write(f"**Company**: {selected_company}")
                st.write(f"**Description**: {job_data.get('description', 'No description available')[:500]}...")
                st.write(f"**Job URL**: [{job_data.get('job_url', 'No URL available')}]")

                chain = Chain()
                cleaned_desc = sanitize_text(job_data.get('description', ''))
                extracted = chain.extract_jobs(cleaned_desc)
                skills = extracted[0].get('skills', []) if extracted and isinstance(extracted, list) and len(extracted) > 0 else []
                # Extract skills from description if empty
                if not skills:
                    prompt_skills_fallback = PromptTemplate.from_template(
                        """
                        Extract a list of 5-10 technical skills and qualifications from this job description: {desc}
                        Return ONLY a JSON array like ["skill1", "skill2"]. No preamble.
                        """
                    )
                    chain_fallback = prompt_skills_fallback | chain.llm
                    fallback_res = chain_fallback.invoke({"desc": cleaned_desc})
                    try:
                        json_parser = JsonOutputParser()
                        skills = json_parser.parse(fallback_res.content)
                    except:
                        skills = []  
                    if not skills:
                        # Default skills if no skills found
                        skills = ["software development", "data engineering"]
                if not skills:
                    st.warning("No skills extracted from job description. Using default skills for portfolio query.")
                    skills = ["software development", "data engineering"]

                portfolio_links = portfolio.query_links(skills, job_data.get('description', ''))
                formatted_links = format_portfolio_links(portfolio_links)
                # Log retrieved links
                with open('app/filter_log.txt', 'a') as f:
                    f.write(f"{datetime.now().isoformat()} - Retrieved portfolio links for {selected_company} '{selected_job}' skills {skills}: {formatted_links}\n")

                # Generate email
                if st.button("✉️ Generate Personalized Cold Email", key="batch_email_button"):
                    with st.spinner("Generating email..."):
                        try:
                            email_body = chain.generate_mail(job=job_data, links=formatted_links, skills=skills)
                            st.session_state.batch_email_body = email_body
                            st.text_area("Email Preview:", value=email_body, height=300, disabled=True)
                        except Exception as e:
                            st.error(f"Error generating email: {e}")

                # Send Email
                recruiting_email = company_emails.get(selected_company, 'dimplecs8530@gmail.com')
                if st.session_state.batch_email_body:
                    if st.button("📧 Send Email", key="batch_send_button"):
                        with st.spinner("Sending email..."):
                            subject = f"Unlock Your Business Potential with GunnenAI - {job_data['title']}"
                            result = send_email(recruiting_email, subject, st.session_state.batch_email_body)
                            st.success(result)
                else:
                    st.write("Generate the email first to enable sending.")
        else:
            st.write("No jobs available for the selected company.")
    else:
        st.write("No companies available. Please scrape jobs first.")
else:
    st.error("No job cache found. Please scrape jobs using one of the options above.")