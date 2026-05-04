import requests
import time
import json
import warnings
warnings.filterwarnings('ignore')

url = "http://localhost:8001/chat"
payload = {
    "question": "what is the difference between ARINC 664 and CAN bus",
    "module": "M5",
    "stream": "B2"
}

print("Polling localhost:8001...")
while True:
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print("Response:", json.dumps(response.json(), indent=2))
            break
        else:
            print("Status code:", response.status_code)
    except Exception as e:
        time.sleep(5)
