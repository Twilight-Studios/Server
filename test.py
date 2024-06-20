import requests

url = "http://127.0.0.1:5000/api/download-game"
payload = {
    "key": "key1",
    "id": "voyage",
    "state": "Development",
    "platform": "windows"
}

response = requests.post(url, json=payload, stream=True)

if response.status_code == 200:
    output_file = "voyage_v0.0.0.zip"

    with open(output_file, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            
    print(f"Downloaded: {output_file}")
else:
    print(f"Failed to download the game, status code: {response.status_code}")