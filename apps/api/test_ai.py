import httpx
import json

url = "https://api.liara.ir/v1/chat/completions"
# url = "https://api.iran.liara.ir/v1/chat/completions"

headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXkiOiI2YTBhM2UxNTI0YTRjYjE0MGY1NmY1OTkiLCJ0eXBlIjoiYWlfa2V5IiwiaWF0IjoxNzc5MDU2MTQ5fQ.pwLmLzKQ9gG65cv6phbZ0tKy4HthDwNyB7bo_DRAWVU",
    "Content-Type": "application/json"
}
data = {
    "model": "Qwen2.5-72B-Instruct",
    "messages": [{"role": "user", "content": "سلام"}],
}

try:
    print("Testing api.liara.ir...")
    r = httpx.post(url, headers=headers, json=data, timeout=10)
    print(r.status_code, r.text)
except Exception as e:
    print("api.liara.ir Failed:", e)

try:
    print("Testing api.iran.liara.ir...")
    r = httpx.post("https://api.iran.liara.ir/v1/chat/completions", headers=headers, json=data, timeout=10)
    print(r.status_code, r.text)
except Exception as e:
    print("api.iran.liara.ir Failed:", e)
