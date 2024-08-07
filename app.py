from flask import Flask, render_template, abort, request, jsonify, Response
import asyncio, os, dotenv, github, utils

app = Flask(__name__)
dotenv.load_dotenv()
github.setup("Twilight-Studios", "Games", "Launcher", os.getenv("TOKEN"))

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
        access_key = json_file['key']
    except:
        abort(400)

    access_keys = utils.check_user_exist(access_key)
    if not access_keys: abort(404)

    return "", 200


@app.route("/api/get-game", methods=["POST"])
def get_game():
    try:
        json_file = request.get_json()
        access_key = json_file['key']
        game_id = json_file['id']
        game_branch = json_file['branch']
    except:
        abort(400)

    game = utils.check_game_available(access_key, game_id, game_branch)
    if not game: abort(404)

    game_info = asyncio.run(utils.get_game_info(game_id, game_branch))
    if not game_info: abort(404)

    return jsonify(game_info)


@app.route("/api/get-all-games", methods=["POST"])
def get_all_games():
    try:
        json_file = request.get_json()
        access_key = json_file['key']
    except:
        abort(400)

    access_keys = utils.check_user_exist(access_key)
    if not access_keys: abort(404)

    games = utils.get_games()

    async def fetch_game_info(game_obj):
        game_id = list(game_obj.keys())[0]
        if game_id not in games.keys():
            return None
        game_branch = game_obj[game_id]
        return await utils.get_game_info(game_id, game_branch)

    async def gather_game_infos():
        coroutines = [fetch_game_info(game_obj) for game_obj in access_keys[access_key]]
        results = await asyncio.gather(*coroutines)
        return [result for result in results if result]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    game_infos = loop.run_until_complete(gather_game_infos())
    loop.close()

    return jsonify(game_infos)

@app.route("/api/download-game", methods=["POST"])
def download_game():
    try:
        json_file = request.get_json()
        access_key = json_file['key']
        game_id = json_file['id']
        game_branch = json_file['branch']
        platform = json_file['platform']
    except:
        abort(400)

    game = utils.check_game_available(access_key, game_id, game_branch)
    if not game: abort(404)

    game_file_url, game_file_size = utils.get_game_file(game_id, game_branch, platform)
    if not game_file_url: abort(404)

    generate, headers = github.stream_content(game_file_url, "game.zip", game_file_size)
    if generate == None: abort(500)
    
    return Response(generate(), headers=headers)

@app.route("/updates/<path>")
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
    app.run(threaded=True)
