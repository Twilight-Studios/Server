import requests, json, base64, aiohttp

def setup(repo_owner: str, games_repo: str, launcher_repo: str, token: str):
    global REPO_OWNER, GAMES_REPO, LAUNCHER_REPO, TOKEN
    REPO_OWNER = repo_owner
    GAMES_REPO = games_repo
    LAUNCHER_REPO = launcher_repo
    TOKEN = token

def get_all_games_repo_branches() -> dict:
    url = f"https://api.github.com/repos/{REPO_OWNER}/{GAMES_REPO}/branches"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v4+json"
    }

    response = requests.get(url, headers=headers)
    return response.json()

def load_file(file_path: str, branch: str = None, return_github_json_wrapper = False):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{GAMES_REPO}/contents/{file_path}"
    
    is_json = file_path.endswith(".json")
    
    if branch:
        url += f"?ref={branch}"

    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v4+json"
    }

    github_json = requests.get(url, headers=headers).json()
    
    if return_github_json_wrapper:
        return github_json
    
    content = github_json["content"]
    
    if is_json:
        content = json.loads(base64.b64decode(content).decode("utf-8"))
        
    return content

async def load_file_async(file_path: str, session: aiohttp.ClientSession, branch: str = None, return_github_json_wrapper=False):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{GAMES_REPO}/contents/{file_path}"
    
    is_json = file_path.endswith(".json")
    
    if branch:
        url += f"?ref={branch}"
    
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v4."
    }

    if is_json: headers["Accept"] += "json"
    else: headers["Accept"] += "raw"

    async with session.get(url, headers=headers) as response:
        if return_github_json_wrapper:
            github_json = await response.json()
            return github_json
        
        if not is_json:
            binary_data = await response.read()
            return base64.b64encode(binary_data).decode('utf-8')

        github_json = await response.json()
        return json.loads(base64.b64decode(github_json["content"]).decode("utf-8"))
    
def get_release_by_tag(tag: str) -> dict:
    url = f"https://api.github.com/repos/{REPO_OWNER}/{GAMES_REPO}/releases/tags/{tag}"
    
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v4+json"
    }
    
    response = requests.get(url, headers=headers)
    return response.json()

def get_release_assets(release_id) -> list[dict]:
    url = f"https://api.github.com/repos/{REPO_OWNER}/{GAMES_REPO}/releases/{release_id}/assets"
    
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v4+json"
    }
    
    response = requests.get(url, headers=headers)
    return response.json()

def get_latest_launcher_release() -> dict | None:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{LAUNCHER_REPO}/releases/latest"
        
        headers = {
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github.v4+json"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200: return None
        
        return response.json()
    
def get_latest_launcher_assets() -> list[dict]:
    latest_release = get_latest_launcher_release()
    
    assets_url = f"{latest_release['url']}/assets"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v4+json"
    }
    
    response = requests.get(assets_url, headers=headers)
    if response.status_code != 200: return None
    return response.json()
    
    
def get_latest_launcher_download() -> tuple[str, int] | tuple[None, None]:
    latest_release = get_latest_launcher_release()
    
    if latest_release == None: return None, None
    
    latest_version = latest_release.get('tag_name', None)
    if latest_version == None: return None, None
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{LAUNCHER_REPO}/releases/tags/{latest_version}"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v4+json"
    }
        
    response = requests.get(url, headers=headers)
    if response.status_code != 200: return None, None
    release = response.json()
        
    for asset in release['assets']:
        if asset['name'] == (f"Twilight-Studios-Launcher-Setup-{latest_version}.exe"):
            return asset['url'], asset['size']
        
def stream_content(url, file_name : str = None, file_size : int = None, chunk_size=8192):
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/octet-stream"
    }
    
    response = requests.get(url, headers=headers, stream=True)
    if response.status_code != 200:
        return None, None
        
    def generate():
        for chunk in response.iter_content(chunk_size=chunk_size):
            yield chunk
            
    
    headers= {
        'Content-Disposition': response.headers.get('content-disposition', 'attachment;'),
        'Content-Type': 'application/octet-stream',
    }
    
    if file_name:
        headers['Content-Disposition'] = response.headers.get('content-disposition', f'attachment; filename={file_name}')
        
    if file_size:
        headers['Content-Length'] = str(file_size)
            
    return generate, headers
            