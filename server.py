from flask import Flask, render_template, send_from_directory, abort, request, jsonify, Response
import requests, base64, aiohttp, asyncio, os, json

TOKEN = os.getenv("TOKEN")

def check_user_exist(access_key):
    with open('access.json') as f: access_keys = json.load(f)
    if access_key not in access_keys.keys(): return False
    return access_keys

def check_game_available(access_key, game_id, game_state=None):
    access_keys = check_user_exist(access_key)
    if not access_keys: return False

    found = False
        
    for i, game in enumerate(access_keys[access_key]):
        if game_id not in game: continue
        if game[game_id] != game_state: continue
        
        found = True
        break
        
    if not found: return False
    
    games = get_games()
    if game_id not in games: return False
    return True

def get_games():
    branches_url = "https://api.github.com/repos/Twilight-Studios/Games/branches"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v4+json"
    }
    
    response = requests.get(branches_url, headers=headers)
    branches = response.json()
    
    games = []
    for branch in branches:
        if branch['name'] != 'main' and branch['name'] != 'example': games.append(branch['name'])
    
    return games

async def fetch_content(session: aiohttp.ClientSession, url, is_json, return_git_json_wrapper=False):
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v4."
    }
    
    if is_json: headers["Accept"] += "json"
    else: headers["Accept"] += "raw"
    
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            if return_git_json_wrapper:
                json = await response.json() 
                return json
            
            if not is_json: 
                binary_data = await response.read()
                return base64.b64encode(binary_data).decode('utf-8')
            
            json = await response.json() 
            return base64.b64decode(json["content"]).decode("utf-8")
        response.raise_for_status()
        
def get_game_file(game_id, game_state, platform):
    game_base_url = f"https://api.github.com/repos/Twilight-Studios/Games/contents/settings.json?ref={game_id}"
    
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v4+json"
    }
        
    content = requests.get(game_base_url, headers=headers).json()["content"]
    settings = json.loads(base64.b64decode(content).decode("utf-8"))
    
    if not settings['enabled_global']:
        return False
    
    if game_state not in settings['game_states'].keys():
        return False
    
    if not settings['game_states'][game_state]['enabled']:
        return False
    
    if platform not in settings['game_states'][game_state]['platforms']:
        return False
    
    version = settings['game_states'][game_state]['latest_version']
        
    releases_base_url = f"https://api.github.com/repos/Twilight-Studios/Games/releases/tags/{version}-{game_id}"
    response = requests.get(releases_base_url, headers=headers)
    if response.status_code != 200: return False
    release_id = response.json()['id']
    
    assets_list_base_url = f"https://api.github.com/repos/Twilight-Studios/Games/releases/{release_id}/assets"
    response = requests.get(assets_list_base_url, headers=headers)
    if response.status_code != 200: return False
    assets_list = response.json()
    
    game_asset_url = False
    game_asset_size = 0
    for asset in assets_list:
        if asset['name'] == f"{platform}.zip":
            game_asset_url = asset['url']
            game_asset_size = asset['size']
            
    return game_asset_url, game_asset_size
        

async def get_game_info(game_id, game_state):
    async with aiohttp.ClientSession() as session:
        game_base_url = "https://api.github.com/repos/Twilight-Studios/Games/contents/{}?ref=" + game_id
        
        files_to_fetch = [
            ("art/icon.png", False),
            ("art/logo.png", False),
            ("art/cover.png", False),
            ("art/background.png", False),
            ("art/patch.png", False),
            ("notes/titles.json", True),
            ("settings.json", True)
        ]

        coroutines = [fetch_content(session, game_base_url.format(file_path), is_json) for file_path, is_json in files_to_fetch]
        results = await asyncio.gather(*coroutines)

        b_icon, b_logo, b_cover, b_background, b_patch, patch_note_titles, settings = results
        
        patch_note_urls = await fetch_content(
            session, game_base_url.format("notes"), is_json=True, return_git_json_wrapper=True
        )

        patch_note_coroutines = [
            fetch_content(session, note['url'], is_json=False) 
            for note in patch_note_urls if note['name'].endswith(".html")
        ]
        
        b_patch_notes = await asyncio.gather(*patch_note_coroutines)

        game_info = {
            "art" : {
                "icon": b_icon,
                "logo": b_logo,
                "cover": b_cover,
                "background": b_background,
                "patch": b_patch
            },
            "settings": json.loads(settings),
            "notes" : {
                "titles": json.loads(patch_note_titles),
                "patch_notes": b_patch_notes
            },
            "state" : game_state
        }
        
        return game_info  

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/download")
def download_launcher():
    return send_from_directory("./TwilightLauncherInstaller.exe")

@app.route("/api/validate-access", methods=["POST"])
def validate_access():
    try:
        json_file = request.get_json()
        access_key = json_file['key']
    except:
        abort(400)
        
    access_keys = check_user_exist(access_key)
    if not access_keys: abort(404)
            
    return "", 200
        
@app.route("/api/get-game", methods=["POST"])
def get_game():
    try:
        json_file = request.get_json()
        access_key = json_file['key']
        game_id = json_file['id']
        game_state = json_file['state']
    except:
        abort(400)
        
    game = check_game_available(access_key, game_id, game_state)
    if not game: abort(404)
            
    game_info = asyncio.run(get_game_info(game_id, game_state))
    if not game_info: abort(404)
    
    return jsonify(game_info)

@app.route("/api/get-all-games", methods=["POST"])
def get_all_games():
    try:
        json_file = request.get_json()
        access_key = json_file['key']
    except:
        abort(400)
    
    access_keys = check_user_exist(access_key)
    if not access_keys: abort(404)
    
    game_infos = {}
    games = get_games()
    
    for game_obj in access_keys[access_key]:
        game_id = list(game_obj.keys())[0]
        if game_id not in games: continue
        game_state = game_obj[game_id]
        
        game_info = asyncio.run(get_game_info(game_id, game_state))
        if not game_info: continue
        
        game_infos[game_id] = game_info
    
    return jsonify(game_infos)

@app.route("/api/download-game", methods=["POST"])
def download_game():
    try:
        json_file = request.get_json()
        access_key = json_file['key']
        game_id = json_file['id']
        game_state = json_file['state']
        platform = json_file['platform']
    except:
        abort(400)
    
    game = check_game_available(access_key, game_id, game_state)
    if not game: abort(404)
    
    game_file_url, game_file_size = get_game_file(game_id, game_state, platform)
    if not game_file_url: abort(404)
    
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/octet-stream"
    }
    
    response = requests.get(game_file_url, headers=headers, stream=True)
    if response.status_code != 200: abort(404)
    
    def generate():
        for chunk in response.iter_content(chunk_size=8192):
            yield chunk

    content_disposition = response.headers.get('content-disposition', 'attachment; filename=game.zip')
    return Response(generate(), headers={'Content-Disposition': content_disposition, 'Content-Type': 'application/octet-stream', 'Content-Length': str(game_file_size)})

if __name__ == "__main__":
    app.run(debug=True)