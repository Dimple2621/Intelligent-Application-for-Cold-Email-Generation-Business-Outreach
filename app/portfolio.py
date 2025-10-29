import pandas as pd
import chromadb
import uuid
from sentence_transformers import SentenceTransformer

class Portfolio:
    def __init__(self, file_path="app/resource/portfolio.csv"):
        self.file_path = file_path
        self.data = pd.read_csv(file_path)
        self.chroma_client = chromadb.PersistentClient('vectorstore')
        self.collection = self.chroma_client.get_or_create_collection(
            name="portfolio",
            embedding_function=None
        )
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


# Generate embeddings for tech skills in portfolio
    def load_portfolio(self):
        if not self.collection.count():
            tech_stacks = self.data["Techskills"].tolist()
            embeddings = self.embedding_model.encode(tech_stacks, convert_to_tensor=False).tolist()
            
            for idx, row in self.data.iterrows():
                self.collection.add(
                    documents=[row["Techskills"]],
                    embeddings=[embeddings[idx]],
                    metadatas=[{"links": row["Links"]}],
                    ids=[str(uuid.uuid4())]
                )

# Query top 5 links from the portfolio vector store that matches job description
    def query_links(self, skills, description=""):
        try:
            valid_skills = [str(skill).strip() for skill in skills if str(skill).strip()]
            if not valid_skills:
                return []
            skills_str = ", ".join(valid_skills)
            
            # Description: Use first 100 chars as snippet for context
            desc_snippet = description[:100].strip() if description else ""
            if desc_snippet:
                desc_snippet = f". Key context: {desc_snippet}"
            
            # Build query string
            query_str = f"Required skills: {skills_str}{desc_snippet}"
            query_embedding = self.embedding_model.encode([query_str]).tolist()[0]
            
            # Query
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=5
            )
            metadatas = results.get('metadatas', [[]])[0]
            return [metadatas]  
        except Exception as e:
            from datetime import datetime
            with open('app/filter_log.txt', 'a') as f:
                f.write(f"{datetime.now().isoformat()} - Error querying portfolio links: {e}\n")
            return []