import requests
import json
from tqdm import tqdm

def test_download_game():
    url = "http://localhost:5000/api/download-game"
    
    data = {
        "key": "adjaffar",
        "id": "mga",
        "state": "Dev Build",
        "platform": "windows"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data), stream=True)
    
    if response.status_code == 200:
        file_name = response.headers.get('Content-Disposition').split('filename=')[-1]
        total_size = int(response.headers.get('Content-Size', 0))
        
        chunk_size = 8192
        with open(file_name, 'wb') as file, tqdm(
                desc=file_name,
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    file.write(chunk)
                    bar.update(len(chunk))
        print(f"Game downloaded successfully as {file_name}")
    else:
        print(f"Failed to download the game. Status code: {response.status_code}")

if __name__ == "__main__":
    test_download_game()