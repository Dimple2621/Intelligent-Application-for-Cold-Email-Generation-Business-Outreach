import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from dotenv import load_dotenv
import json
from datetime import datetime
import re

load_dotenv()

class Chain:
    def __init__(self):
        self.llm = ChatGroq(temperature=0.1, groq_api_key=os.getenv("GROQ_API_KEY"), model_name="llama-3.1-8b-instant")

    def extract_jobs(self, cleaned_text):
        prompt_extract = PromptTemplate.from_template(
        """
        ### SCRAPED TEXT FROM WEBSITE:
        {page_data}
        ### INSTRUCTION:
        Extract job postings from the scraped text and return ONLY a valid JSON array of objects. Each object MUST contain the keys: `role`, `experience`, `skills`, and `description`. 

        For `skills`, extract a list of 5-10 key skills, tools, technologies, and qualifications mentioned (or implied) in the text (e.g., from requirements, responsibilities, or preferred sections). Categorize into technical (e.g., Python, AWS) and soft (e.g., teamwork, problem-solving). Include synonyms and variations (e.g., if "ML" is mentioned, add "machine learning"). Prioritize the most relevant 5-10; if fewer, that's fine—do not invent.

        ### STEP-BY-STEP REASONING:
        Step 1: Scan for technical skills (programming languages, tools, frameworks like React, Docker).
        Step 2: Add soft skills (communication, leadership) if mentioned.
        Step 3: Note variations (e.g., "cloud" → "AWS, Azure").
        Step 4: Limit to 5-10 total, ranked by frequency/importance.

        Example Output for Skills: ["Python (programming)", "AWS (cloud computing)", "Agile methodology (team collaboration)", "SQL (database)"]

        Do NOT include any explanations, code, or preamble—return JSON only. If no jobs are found, return an empty array: [].
        ### VALID JSON (NO PREAMBLE):
        """
        )

        chain_extract = prompt_extract | self.llm
        res = chain_extract.invoke(input={"page_data": cleaned_text})
        try:
            json_parser = JsonOutputParser()
            res = json_parser.parse(res.content)
            return res if res and isinstance(res, list) and len(res) > 0 else []
        except OutputParserException:
            # If parsing fails, return empty list and log
            from datetime import datetime
            with open('app/filter_log.txt', 'a') as f:
                f.write(f"{datetime.now().isoformat()} - Failed to parse job data from LLM: {res.content[:500]}\n")
            return []

    def generate_mail(self, job, links, skills=None):
        skills_str = ", ".join(skills) if skills and isinstance(skills, list) else ""
        prompt_email = PromptTemplate.from_template(
            """
            ### JOB DESCRIPTION:
            {job_description}

            ### KEY SKILLS FROM JOB:
            {skills_list}
            ### EXAMPLE EMAILS (Follow This Style):
            Example 1 (for Python job): "Dear Hiring Manager, Your Python developer role needs scalable apps—GunnenAI excels here. Our Django project [link1] cut costs 30% via automation. For cloud integration, see our AWS setup [link2]. Let's chat? Best, Jay"

            Example 2 (for DevOps job): "Dear Hiring Manager, Excited about your DevOps needs at your organization. GunnenAI optimizes pipelines: Our CI/CD tools [link1] boosted efficiency 40%. Matching your Docker reqs, our infra project [link2] ensures reliability. Reply to connect? Jay"

            ### STEP-BY-STEP REASONING (Think Aloud Before Writing):
            Step 1: Scan the JD and skills list for 2-3 top requirements (e.g., Python, cloud tools).
            Step 2: Match them to links: Link1 fits [skill1, explain why], Link2 fits [skill2, explain why].
            Step 3: Outline email: Greeting → Tie to JD needs → GunnenAI strengths → Insert both links with fit reasons → Call to action → Sign-off as Jay.
            Step 4: Double-check: Both links included? No extras invented?

            ### INSTRUCTION:
            You are Jay, a business development executive at GunnenAI. GunnenAI is an AI & Software Consulting company dedicated to facilitating
            the seamless integration of business processes through automated tools. 
            Over our experience, we have empowered numerous enterprises with tailored solutions, fostering scalability, 
            process optimization, cost reduction, and heightened overall efficiency. 
            Your job is to write a cold email to the client regarding the job mentioned above describing the capability of GunnenAI 
            in fulfilling their needs.
            Start the email with "Dear Hiring Manager," (use this exact phrase, do NOT use placeholders like [Hiring Manager's Name] or any other variation).
            Identify key skills, technologies, and qualifications from the job (e.g., from the skills list above or description). Then, add 2 of the most relevant portfolio links from the following that match those keywords: {link_list}. Use ONLY the links provided in {link_list}. Do NOT invent, create, or add any other links, URLs, or portfolio examples. For each link you include, provide a brief explanation of why it fits (e.g., "Our Python/Django project at [link] demonstrates expertise in the required skills..."). If no links are relevant, omit them entirely.
            IMPORTANT: Include EXACTLY these two most relevant portfolio links in the email body, integrated naturally (e.g., "As demonstrated in our Python project: [link1]" and "For DevOps expertise, see: [link2]"). Do not omit either. Use them to showcase GunnenAI's portfolio.

            Relevant links to include:
            1. {link1}
            2. {link2}

            Remember you are Jay, BDE at GunnenAI. Mention this in signature.

            Do not provide a preamble.
            ### EMAIL (NO PREAMBLE):
            """
        )
        chain_email = prompt_email | self.llm
        link1 = links[0] if len(links) >= 1 else ""
        link2 = links[1] if len(links) >= 2 else ""
        link_list = ", ".join(links) if links else ""

        res = chain_email.invoke({
            "job_description": str(job),
            "skills_list": skills_str,
            "link_list": link_list,
            "link1": link1,
            "link2": link2
        })
        # Extract Job Description keywords
        job_desc = str(job)
        job_keywords = re.findall(r'\b[A-Z][a-z]{3,}\b', job_desc) 

        # Count included links
        included_links_count = sum(1 for link in links if link in res.content)
        total_links = len(links)

        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'job_title': job.get('title', 'Unknown'),
            'job_desc_keywords': job_keywords,
            'generated_email': res.content,
            'included_links_count': included_links_count,
            'total_links': total_links
        }

        # Store logs
        with open('app/email_logs.json', 'a', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False)
            f.write('\n')
        return res.content

if __name__ == "__main__":
    print(os.getenv("GROQ_API_KEY"))