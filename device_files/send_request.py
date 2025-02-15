import urequests
import json

import config

# Replace with your actual API key
api_key = config.API_KEY
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=" + api_key

headers = {
    "Content-Type": "application/json"
}

data = {
    "contents": [{
        "parts": [{"text": "Explain how AI works"}]
    }]
}

# Send the POST request
response = urequests.post(url, headers=headers, data=json.dumps(data))

# Print the response from the API
print(response.text)
response.close()