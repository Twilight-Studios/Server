import requests

response = requests.post("http://127.0.0.1:5000/api/get-game", json={"key":"key1", "id": "example", "state":"Development"})

print(response)
print(response.json()['notes'])