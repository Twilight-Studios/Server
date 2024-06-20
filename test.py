import requests

response = requests.post("http://127.0.0.1:5000/api/download-game", json={"key":"key1", "id": "voyage", "state":"Development"})

print(response)
print(response.json())