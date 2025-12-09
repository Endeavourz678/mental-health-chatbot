from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=10.0
)

print("Testing OpenAI API...")

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=20,
        timeout=10
    )
    print("✓ Success!")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"✗ Error: {e}")