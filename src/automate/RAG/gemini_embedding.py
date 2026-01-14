from google import genai

GOOGLE_API_KEY = "AIzaSyDBhPisK2y127Rg8rCluMInEJ7dJIl9Dx4"

client = genai.Client(
    api_key = GOOGLE_API_KEY
)

result = client.models.embed_content(
        model="gemini-embedding-001",
        contents="What is the meaning of life?"
)

print(result.embeddings)