from flask import Flask, render_template, abort, request, jsonify, Response
import asyncio, os, dotenv, github, auth, games

app = Flask(__name__)
dotenv.load_dotenv()
github.setup("Twilight-Studios", "Games", "Launcher", os.getenv("TOKEN"), True)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/download")
def download_launcher():
    asset_url, asset_size = github.get_latest_launcher_download()
    if not asset_url or not asset_size:
        abort(404, description="Launcher not found")

    generate, headers = github.stream_content(asset_url, "TwilightStudiosLauncherSetup.exe", asset_size)
    
    if generate == None:
        abort(500, "Launcher download failed")
        
    return Response(generate(), headers=headers)

@app.route("/api/validate-access", methods=["POST"])
def validate_access():
    try:
        json_file = request.get_json()
        playtester_id = json_file['playtester_id']
    except:
        abort(400)

    playtester_id = auth.get_playtester(playtester_id)
    if not playtester_id: abort(403)

    return "", 200


@app.route("/api/get-all-games", methods=["POST"]) # TODO: Add improved error validation
def get_all_games():
    try:
        json_file = request.get_json()
        playtester_id = json_file['playtester_id']
    except:
        abort(400)

    playtester = auth.get_playtester(playtester_id)
    if not playtester: abort(403)
    
    minimal = False
    if 'minimal' in json_file:
        if type(json_file['minimal']) == bool: 
            minimal = json_file['minimal']

    game_ids = games.get_game_ids(whitelist_branches=playtester.keys())

    async def fetch_game_metadata(game_id):
        if minimal: return await games.get_game_metadata(game_id, get_cover=True)
        else: return await games.get_game_metadata(game_id, get_all=True)

    async def gather_game_metadatas():
        coroutines = [fetch_game_metadata(game_id) for game_id in game_ids]
        results = await asyncio.gather(*coroutines)
        return [result for result in results if result]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    game_metadatas = loop.run_until_complete(gather_game_metadatas())
    loop.close()
    
    sanitized_metadatas = []
    for game_metadata in game_metadatas:
        sanitized_metadata = games.sanitize_game_metadata(game_metadata, playtester[game_metadata['id']])
        if sanitized_metadata != None: sanitized_metadatas.append(sanitized_metadata)

    return jsonify(sanitized_metadatas)


@app.route("/api/get-game", methods=["POST"]) # TODO: Add improved error validation
def get_game():
    try:
        json_file = request.get_json()
        playtester_id = json_file['playtester_id']
        game_id = json_file['game_id']
    except:
        abort(400)

    playtester = auth.get_playtester(playtester_id)
    if not playtester: abort(403)
    if game_id not in playtester: abort(406)
    
    minimal = False
    if 'minimal' in json_file:
        if type(json_file['minimal']) == bool: 
            minimal = json_file['minimal']

    async def fetch_game_metadata():
        if minimal: return await games.get_game_metadata(game_id, get_cover=True)
        else: return await games.get_game_metadata(game_id, get_all=True)

    game_metadata = asyncio.run(fetch_game_metadata())
    
    sanitized_metadata = games.sanitize_game_metadata(game_metadata, playtester[game_metadata['id']])
    if not sanitized_metadata: abort(406)
    print(sanitized_metadata)

    return jsonify(sanitized_metadata)

@app.route("/updates/<path>") # Only used if launcher has custom update settings.
def updates(path: str):
    path = path.replace(" ", "-")
    
    latest_release_assets = github.get_latest_launcher_assets()
    if latest_release_assets == None: abort(404)

    asset_info = None
    for asset in latest_release_assets:
        if asset['name'] == path:
            asset_info = (asset['url'], asset['size'])

    if not asset_info: abort(404)
    
    generate, headers = github.stream_content(asset_info[0], file_size=asset_info[1])
    if generate == None: abort(500)
    
    return Response(generate(), headers=headers)


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
