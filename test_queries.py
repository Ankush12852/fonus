import requests
import json

queries = [
    "i failed m6 last session by 6 marks, 30 days left, guide me",
    "create a note on corrosion",
    "what are the most repeated questions in M6"
]

for q in queries:
    resp = requests.post(
        "http://localhost:8000/chat",
        json={"question": q, "module": "M6", "stream": "B1.1"}
    )
    print(f"--- Question: {q} ---")
    try:
        data = resp.json()
        print(f"Response ({data.get('llm_used', 'N/A')}):\n{data.get('answer', '')}\n")
    except Exception as e:
        print(f"Error: {e}\nResponse text: {resp.text}\n")
