from jobspy import scrape_jobs
import json
import pandas as pd
from datetime import datetime
import time
import re

# Normalize text by converting to lowercase, removing punctuation, and collapsing spaces
def normalize_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)  
    text = re.sub(r'\s+', ' ', text).strip()  
    return text

# Scrape up to 50 jobs for a company
def scrape_company_jobs(company_name, num_pages=2):
    try:
        # Alternative search terms for companies
        search_terms = [company_name]
        if company_name == "Walmart":
            search_terms.append("Walmart Global Tech")
        elif company_name == "Amazon":
            search_terms.append("Amazon Web Services")
        elif company_name == "Alphabet":
            search_terms.append("Google")
        
        all_jobs = []
        for term in search_terms:
            jobs = scrape_jobs(
                site_name="indeed",
                search_term=term,
                location="United States",
                results_wanted=50,
                page=num_pages,
                country="USA"
            )
            if isinstance(jobs, pd.DataFrame):
                jobs['scraped_at'] = datetime.now().isoformat()
                all_jobs.append(jobs)
        
        if all_jobs:
            jobs = pd.concat(all_jobs, ignore_index=True).drop_duplicates(subset=['title', 'job_url'])
        else:
            jobs = pd.DataFrame()
        
        if jobs.empty:
            with open('app/filter_log.txt', 'a') as f:
                f.write(f"{datetime.now().isoformat()} - {company_name}: No jobs scraped\n")
            return []
        
        # Software-focused keywords
        software_keywords = [
            "software", "developer", "data science", "data scientist", "data engineer",
            "devops", "programmer", "cloud", "ai", "machine learning","ml", "llm", "llms",
            "react", "node.js", "mongodb", "angular", ".net", "sql server",
            "vue.js", "ruby on rails", "postgresql", "python", "django", "mysql",
            "java", "spring boot", "oracle", "flutter", "firebase", "graphql",
            "wordpress", "php", "magento", "react native", "ios", "swift",
            "core data", "android", "room persistence", "kotlin", "android tv",
            "android ndk", "arkit", "cross-platform", "xamarin", "azure",
            "typescript", "express.js", "tensorflow", "jenkins", "docker",
            "full stack", "backend", "frontend", "database", "cybersecurity",
            "network engineer", "systems developer", "qa engineer", "test automation",
            "automation engineer", "site reliability", "sre", "infrastructure developer",
            "artificial intelligence", "ml engineer", "software development",
            "web developer", "application developer", "app", "engineer"
        ]
        # Exclusions for non-software keywords
        non_software_keywords = [
            "pharmacy", "pharmacist", "technician", "retail", "store", "associate",
            "cashier", "clerk", "sales", "customer service", "warehouse", "driver",
            "delivery", "healthcare", "nurse", "medical", "manufacturing", "mechanical",
            "civil", "electrical", "chemical", "biomedical", "industrial", "cake decorator",
            "safety specialist", "loss prevention", "asset protection", "customer host",
            "health & beauty", "fashion team", "backroom team", "car wash", "packaging engineer",
            "tax analyst", "claims specialist", "team supervisor"
        ]

        # Filtering Tech Jobs by atleast one software keyword in title OR description
        def is_software_job(row):
            title = normalize_text(row.get('title', ''))
            desc = normalize_text(row.get('description', ''))
            matched_software = [k for k in software_keywords if k in title or k in desc]
            has_software = len(matched_software) >= 1
            non_software_found = [k for k in non_software_keywords if k in title]
            no_non_software = not non_software_found
            reason = "Passed"
            if not has_software:
                reason = f"Missing software keyword (found: {matched_software}, expected at least 1)"
            elif not no_non_software:
                reason = f"Non-software keyword found in title: {non_software_found}"
            return has_software and no_non_software, reason, matched_software
        
        # Log raw job titles for analysis
        with open('app/raw_jobs_log.txt', 'a') as f:
            f.write(f"{datetime.now().isoformat()} - {company_name}: Raw jobs scraped ({len(jobs)}):\n")
            raw_titles = [row['title'] for _, row in jobs.head(10).iterrows()]
            f.write(f"Sample raw titles: {raw_titles}\n")
        # Apply filter and collect reasons
        filtered_jobs = []
        reasons = []
        for _, row in jobs.iterrows():
            if not isinstance(row.get('title'), str) or not row.get('title') or not isinstance(row.get('description'), str) or not row.get('description'):
                reasons.append((row.get('title', 'Unknown'), 'Missing or invalid title/description', []))
                continue
            is_software, reason, matched_keywords = is_software_job(row)
            if is_software:
                job_dict = row.to_dict()
                for key, value in job_dict.items():
                    if value is None:
                        job_dict[key] = ""
                    elif not isinstance(value, (str, int, float, bool)):
                        job_dict[key] = str(value)
                filtered_jobs.append(job_dict)
            reasons.append((row.get('title', ''), reason, matched_keywords))
        filtered_jobs = pd.DataFrame(filtered_jobs).to_dict('records')
        # Enhanced logging
        included_titles = [row['title'] for row in filtered_jobs[:10]]
        excluded = [(title, reason) for title, reason, _ in reasons if reason != "Passed"][:5]
        with open('app/filter_log.txt', 'a') as f:
            f.write(f"{datetime.now().isoformat()} - {company_name}: Scraped {len(jobs)} jobs, filtered to {len(filtered_jobs)} software jobs\n")
            f.write(f"Included: {included_titles}\n")
            f.write(f"Excluded: {[f'{title} ({reason}, matched: {keywords})' for title, reason, keywords in reasons if reason != 'Passed'][:5]}\n")
            if len(filtered_jobs) == 0:
                all_titles = [row['title'] for _, row in jobs.head(10).iterrows()]
                f.write(f"No software jobs found for {company_name}. Sample titles: {all_titles}\n")
        return filtered_jobs
    except Exception as e:
        print(f"Error scraping {company_name}: {e}")
        with open('app/filter_log.txt', 'a') as f:
            f.write(f"{datetime.now().isoformat()} - Error scraping {company_name}: {e}\n")
        return []

# Save the scraped jobs as batches to JSON
def batch_scrape(companies_file='app/data/companies.json', batch_size=50):
    try:
        with open(companies_file, 'r') as f:
            companies = json.load(f)['companies']
        
        all_jobs = {}
        total_companies = len(companies)
        for i in range(0, total_companies, batch_size):
            batch_companies = companies[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1} of {(total_companies + batch_size - 1)//batch_size} ({len(batch_companies)} companies)...")
            for comp in batch_companies:
                print(f"Scraping {comp['name']}...")
                jobs = scrape_company_jobs(comp['name'])
                all_jobs[comp['name']] = jobs
                if not jobs:
                    print(f"Warning: No software jobs found for {comp['name']}. This is normal for non-tech companies. Check app/filter_log.txt and app/raw_jobs_log.txt.")
                # 5-second delay to avoid rate limiting
                time.sleep(5)
                  
            with open('app/data/jobs_cache.json', 'w') as f:
                json.dump(all_jobs, f, indent=2, default=str)
            print(f"Batch {i//batch_size + 1} saved to jobs_cache.json")
        
        return all_jobs
    except Exception as e:
        print(f"Error in batch scrape: {e}")
        with open('app/filter_log.txt', 'a') as f:
            f.write(f"{datetime.now().isoformat()} - Batch scrape error: {e}\n")
        return {}