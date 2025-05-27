import os
from openai import OpenAI
from dotenv import load_dotenv

# Load API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ask_chat(prompt):
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# Interactive loop
if __name__ == "__main__":
    print("🤖 GPT Assistant Ready — type 'exit' to quit.")
    while True:
        q = input("💬 You: ")
        if q.lower() in ("exit", "quit"):
            print("👋 Goodbye!")
            break
        print("🤖 GPT:", ask_chat(q))