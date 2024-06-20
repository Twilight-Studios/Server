from flask import Flask, render_template, send_from_directory, abort, request, jsonify
import json

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/download")
def download_launcher():
    return send_from_directory("./TwilightLauncherInstaller.exe")\
        
def check_user_exist(access_key):
    with open('access.json') as f: access_keys = json.load(f)
    if access_key not in access_keys.items(): return False
    return access_keys

def check_game_available(access_key, game_id):
    access_keys = check_user_exist(access_key)
    if not access_keys: return False
    
    if game_id not in access_keys[access_key]: return False
    
    with open('games.json') as f: games = json.load(f)
    if game_id not in games.items(): return False
    return games[game_id]

@app.route("/api/validate-access", methods=["POST"])
def validate_access():
    try:
        json_file = request.get_json()
        access_key = json_file['key']
        
        access_keys = check_user_exist(access_key)
        if not access_keys: abort(404)
            
        return jsonify(access_keys[access_key])
    except:
        abort(400)
        
@app.route("/api/get-game", methods=["POST"])
def get_game():
    try:
        json_file = request.get_json()
        access_key = json_file['key']
        game_id = json_file['gameid']
        
        game = check_game_available(access_key, game_id)
        if not game: abort(404)
            
        return jsonify(game)
    except:
        abort(400)

if __name__ == "__main__":
    app.run(debug=True)