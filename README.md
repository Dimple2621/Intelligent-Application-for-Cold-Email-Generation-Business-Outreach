# Cold Email Generator for B2B Client Acquisition

## Overview

This AI-powered **Streamlit** application helps software service companies like **GunnenAI** acquire clients from **Fortune 500 firms** by automating personalized cold emails.  
It scrapes job postings from Indeed to identify hiring needs, matches them to your company’s portfolio projects, and generates tailored pitches.
Emails highlight how your services solve their gaps, including **2 relevant project links** for proof.

---

## 1. What It Does

- **Batch Mode**: Scrapes 50+ jobs per company, filters for tech roles, caches data.  
- **Manual Mode**: Processes a single job URL.  
- **Personalization**: Uses semantic search (ChromaDB + MiniLM embeddings) to pull top-2 portfolio matches.  
- **Generation**: Crafts emails using **Groq’s Llama 3.1-8B** via **LangChain** (Chain-of-Thought + few-shot prompts).  
- **Send & Evaluate**: Dispatches via Gmail SMTP; logs relevance stats (average link inclusion ~77.9%).  

Built with **Python**, **Streamlit**, **LangChain**, **JobSpy**, and other open-source tools for local execution.

---

## 2. Prerequisites

- Python **3.10+**
- Groq API Key → [https://console.groq.com/keys](https://console.groq.com/keys)
- Gmail App Password → [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
- (Optional) GitHub account for cloning repository

---

## 3. Environment Setup

1. **Create `.env` file** in the root directory:
   ```bash
   GROQ_API_KEY=your_groq_key_here
2. **Create `secrets.toml`** in app/ folder:
   ```bash
   GMAIL_PASSWORD = "your_gmail_app_password_here"
3. **Update sender email:  Replace "dummysender@gmail.com" with your own email in: `main.py,test.py,chains.py`** in app/ folder
4. **Update test recipient email:  Replace "dummyrecruiting@example.com" with your own email in: `companies.json`**
5. **Installation** : Run these steps in PowerShell (Windows) or Terminal (Mac/Linux):
   ```bash
   GROQ_API_KEY=your_groq_key_here
   cd "project_directory_path"  # Move to project directory
   Set-ExecutionPolicy -Scope Process Bypass  # Allow PowerShell scripts (Windows only)
   . .\.venv\Scripts\Activate.ps1  # Activate virtual environment (create if missing: python -m venv .venv)
   $env:USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"  # Set user agent for scraping
   # Clear cache files if any
   Remove-Item -Path .\app\data\jobs_cache.json -Force -ErrorAction SilentlyContinue
   Remove-Item -Path .\app\data\single_job.json -Force -ErrorAction SilentlyContinue
   Remove-Item -Path .\app\filter_log.txt -Force -ErrorAction SilentlyContinue
   Remove-Item -Path .\app\raw_jobs_log.txt -Force -ErrorAction SilentlyContinue
   Remove-Item -Path .\vectorstore -Recurse -Force -ErrorAction SilentlyContinue
   Remove-Item -Path .\app\chroma_jobs_db -Recurse -Force -ErrorAction SilentlyContinue
   pip install -r requirements.txt  # Install dependencies
## 3. Running the Project
To launch the app, run: 
```
python -m streamlit run app/main.py
```


## 4. View Performance Metrics
After sending several emails, generate a performance chart:
```
 python app/analyze_emails.py
```





   

