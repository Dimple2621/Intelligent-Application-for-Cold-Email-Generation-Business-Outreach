import json
from utils import sanitize_text
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.docstore.document import Document
from datetime import datetime

# Clean metadata for database compatibility
def simplify_metadata(metadata):
    simple_metadata = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            simple_metadata[key] = value
        else:
            simple_metadata[key] = str(value)
    return simple_metadata

# Load JSON, clean, split and embed into a new Chroma collection
def preprocess_and_embed(jobs_file='app/data/jobs_cache.json', persist_dir='chroma_jobs_db'):
    try:
        with open(jobs_file, 'r') as f:
            all_jobs = json.load(f)
        
        documents = []
        skipped_jobs = []
        
        # BATCH SCRAPE
        if isinstance(all_jobs, dict):
            for company, jobs in all_jobs.items():
                if not isinstance(jobs, list):
                    skipped_jobs.append((company, 'Unknown', 'Jobs is not a list'))
                    continue
                for job in jobs:
                    if not isinstance(job, dict):
                        skipped_jobs.append((company, job.get('title', 'Unknown'), 'Job is not a dictionary'))
                        continue
                    if not isinstance(job.get('title'), str) or not job.get('title'):
                        skipped_jobs.append((company, job.get('title', 'Unknown'), 'Invalid or missing title'))
                        continue
                    if not isinstance(job.get('description'), str) or not job.get('description'):
                        skipped_jobs.append((company, job.get('title', 'Unknown'), 'Invalid or missing description'))
                        continue
                    cleaned_desc = sanitize_text(job.get('description'))
                    if not isinstance(cleaned_desc, str) or not cleaned_desc:
                        skipped_jobs.append((company, job.get('title', 'Unknown'), 'Empty or invalid description after cleaning'))
                        continue
                    skills = job.get('skills', '')
                    if isinstance(skills, str):
                        skills = [s.strip() for s in skills.split(',') if s.strip()]
                    elif not skills:
                        # Use these generic skills if there are no keywords in the job description
                        skills = ["software development"] 
                    skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
                    # Create Document
                    doc = Document(
                        page_content=cleaned_desc,
                        metadata={
                            'company': str(company),
                            'title': job.get('title', ''),
                            'url': str(job.get('job_url', '')),
                            'experience': str(job.get('experience', 'Not specified')),
                            'skills': skills_str  # Store as string
                        }
                    )
                    documents.append(doc)
        # MANUAL SCRAPE
        elif isinstance(all_jobs, list):
            for job in all_jobs:
                if not isinstance(job, dict):
                    skipped_jobs.append(('Unknown', job.get('title', 'Unknown'), 'Job is not a dictionary'))
                    continue
                if not isinstance(job.get('title'), str) or not job.get('title'):
                    skipped_jobs.append(('Unknown', job.get('title', 'Unknown'), 'Invalid or missing title'))
                    continue
                if not isinstance(job.get('description'), str) or not job.get('description'):
                    skipped_jobs.append(('Unknown', job.get('title', 'Unknown'), 'Invalid or missing description'))
                    continue
                cleaned_desc = sanitize_text(job.get('description'))
                if not isinstance(cleaned_desc, str) or not cleaned_desc:
                    skipped_jobs.append(('Unknown', job.get('title', 'Unknown'), 'Empty or invalid description after cleaning'))
                    continue
                skills = job.get('skills', '')
                if isinstance(skills, str):
                    skills = [s.strip() for s in skills.split(',') if s.strip()]
                elif not skills:
                    # Use these generic skills if there are no keywords in the job description
                    skills = ["software development"]
                skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
                # Create Document
                doc = Document(
                    page_content=cleaned_desc,
                    metadata={
                        'company': str(job.get('company', 'Unknown')),
                        'title': job.get('title', ''),
                        'url': str(job.get('job_url', '')),
                        'experience': str(job.get('experience', 'Not specified')),
                        'skills': skills_str  # Store as string
                    }
                )
                documents.append(doc)
        else:
            raise ValueError("Invalid JSON format: Expected a dictionary or list")
        
        if skipped_jobs:
            with open('app/filter_log.txt', 'a') as f:
                f.write(f"{datetime.now().isoformat()} - Skipped {len(skipped_jobs)} jobs in preprocessing:\n")
                for company, title, reason in skipped_jobs[:5]:
                    f.write(f"  {company}: {title} ({reason})\n")
        
        if not documents:
            print("Warning: No valid jobs to process after filtering. Check app/filter_log.txt for details.")
            with open('app/filter_log.txt', 'a') as f:
                f.write(f"{datetime.now().isoformat()} - No valid jobs to process after filtering.\n")
            return
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(documents)
        
        # Validate splits are Documents
        valid_splits = []
        for doc in splits:
            if not isinstance(doc, Document) or not hasattr(doc, 'metadata'):
                with open('app/filter_log.txt', 'a') as f:
                    f.write(f"{datetime.now().isoformat()} - Invalid split: {str(doc)[:50]}... (not a Document)\n")
                continue
            valid_splits.append(doc)
        
        if not valid_splits:
            print("Warning: No valid document splits after processing. Check app/filter_log.txt.")
            with open('app/filter_log.txt', 'a') as f:
                f.write(f"{datetime.now().isoformat()} - No valid document splits after processing.\n")
            return
        
        # Simplify metadata for all splits
        filtered_splits = []
        for doc in valid_splits:
            try:
                simplified_metadata = simplify_metadata(doc.metadata)
                filtered_splits.append(Document(page_content=doc.page_content, metadata=simplified_metadata))
            except Exception as e:
                with open('app/filter_log.txt', 'a') as f:
                    f.write(f"{datetime.now().isoformat()} - Error simplifying metadata for {doc.metadata.get('title', 'Unknown')}: {e}\n")
                continue
        
        if not filtered_splits:
            print("Warning: No valid documents after metadata simplification. Check app/filter_log.txt.")
            with open('app/filter_log.txt', 'a') as f:
                f.write(f"{datetime.now().isoformat()} - No valid documents after metadata simplification.\n")
            return
        
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        vectorstore = Chroma.from_documents(
            documents=filtered_splits,
            embedding=embeddings,
            persist_directory=persist_dir,
            collection_name="fortune_jobs"
        )
        
        print(f"Embedded {len(filtered_splits)} job chunks for {len(all_jobs)} companies.")
    except Exception as e:
        print(f"Error in preprocessing: {e}")
        with open('app/filter_log.txt', 'a') as f:
            f.write(f"{datetime.now().isoformat()} - Preprocessing error: {e}\n")

        raise
