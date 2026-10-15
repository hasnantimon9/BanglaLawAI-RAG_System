from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    task_type="RETRIEVAL_QUERY" 
)

query = "ভোক্তা অধিকার লঙ্ঘন হলে কী করা যায়?"

vector = embeddings.embed_query(query)

print("Embedding dimensions:", len(vector))
print("First 5 values:", vector[:5])