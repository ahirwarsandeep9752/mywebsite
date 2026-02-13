import os
from google import genai

print("KEY:", os.getenv("GEMINI_API_KEY"))

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

response = client.models.generate_content(
    model="models/gemini-flash-latest",
    contents="Say hello in one line"
)

print("AI:", response.text)
