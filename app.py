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

    game_ids = games.get_game_ids(whitelist_branches=playtester.keys())

    async def fetch_game_info(game_id):
        return await games.get_game_metadata(game_id, get_cover=True)

    async def gather_game_infos():
        coroutines = [fetch_game_info(game_id) for game_id in game_ids]
        results = await asyncio.gather(*coroutines)
        return [result for result in results if result]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    game_infos = loop.run_until_complete(gather_game_infos())
    loop.close()
        
    for game in game_infos:
        sanitized_settings = games.sanitize_settings_metadata(game['settings'], playtester[game['id']])
        if sanitized_settings == None: game_infos.remove(game)
        else: game["settings"] = sanitized_settings

    return jsonify(game_infos)

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
