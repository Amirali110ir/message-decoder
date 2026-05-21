import httpx
import json

url = "https://ai.liara.ir/api/6a0a3d119e145954af352534/v1/chat/completions"
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXkiOiI2YTBhM2UxNTI0YTRjYjE0MGY1NmY1OTkiLCJ0eXBlIjoiYWlfa2V5IiwiaWF0IjoxNzc5MDU2MTQ5fQ.pwLmLzKQ9gG65cv6phbZ0tKy4HthDwNyB7bo_DRAWVU",
    "Content-Type": "application/json"
}

results = []

# Test 1: With JSON format
data_with_json = {
    "model": "Qwen2.5-72B-Instruct",
    "messages": [{"role": "user", "content": "سلام. یک فایل JSON بفرست که فقط شامل فیلد test با مقدار 1 باشد."}],
    "response_format": {"type": "json_object"}
}

try:
    results.append("--- Test 1: With response_format JSON ---")
    r = httpx.post(url, headers=headers, json=data_with_json, timeout=15)
    results.append(f"Status Code: {r.status_code}")
    results.append(f"Response: {r.text}")
except Exception as e:
    results.append(f"Test 1 Failed with exception: {str(e)}")

# Test 2: Without JSON format
data_without_json = {
    "model": "Qwen2.5-72B-Instruct",
    "messages": [{"role": "user", "content": "سلام. یک فایل JSON بفرست که فقط شامل فیلد test با مقدار 1 باشد."}],
}

try:
    results.append("\n--- Test 2: Without response_format JSON ---")
    r = httpx.post(url, headers=headers, json=data_without_json, timeout=15)
    results.append(f"Status Code: {r.status_code}")
    results.append(f"Response: {r.text}")
except Exception as e:
    results.append(f"Test 2 Failed with exception: {str(e)}")

with open("ai_test_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print("Done! Results written to ai_test_result.txt")
