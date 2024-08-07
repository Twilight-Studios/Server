import github, aiohttp, asyncio

def check_user_exist(access_key) -> dict | bool:
    access_keys = github.load_file("access.json")

    if access_key not in access_keys.keys(): return False
    return access_keys

def check_game_available(access_key, game_id, game_branch) -> bool:
    access_keys = check_user_exist(access_key)
    if not access_keys: return False

    found = False

    for game in access_keys[access_key]:
        if game_id not in game: continue
        if game[game_id] != game_branch: continue

        found = True
        break

    if not found: return False

    games = get_games()
    if game_id not in games: return False
    if game_branch not in games[game_id]: return False
    return True


def get_games() -> dict[str, list]:
    branches = github.get_all_games_repo_branches()

    games = {}
    for branch in branches:
        game_id = branch['name']
        
        if game_id == 'main' or game_id == 'example': continue
        
        games[game_id] = []
        game_settings = github.load_file("settings.json", branch=game_id)
        
        for game_branch in game_settings['game_branches'].keys():
            games[game_id].append(game_branch)

    return games


def get_game_file(game_id, game_branch, platform) -> tuple[str, int] | None:
    game_settings = github.load_file("settings.json", branch=game_id)

    if not game_settings['enabled_global']: return None
    if game_branch not in game_settings['game_branches'].keys(): return None
    if not game_settings['game_branches'][game_branch]['enabled']: return None
    if platform not in game_settings['game_branches'][game_branch]['platforms']: return None

    version = game_settings['game_branches'][game_branch]['latest_version']
    tag = f"{version}-{game_id}"

    release = github.get_release_by_tag(tag)
    release_id = release['id']
    assets_list = github.get_release_assets(release_id)

    game_asset_url = game_asset_size = None
    for asset in assets_list:
        if asset['name'] == f"{platform}.zip":
            game_asset_url = asset['url']
            game_asset_size = asset['size']
            
    if game_asset_url == None or game_asset_size == None: return None

    return game_asset_url, game_asset_size


async def get_game_info(game_id, game_branch) -> dict:
    async with aiohttp.ClientSession() as session:
        files_to_fetch = ["art/icon.png", "art/logo.png", "art/cover.png", 
                          "art/background.png", "art/patch.png", "settings.json"]
        
        patch_note_urls = await github.load_file_async("notes", session, branch=game_id, return_github_json_wrapper=True)
        for note in patch_note_urls: files_to_fetch.append(f"notes/{note['name']}")

        coroutines = [github.load_file_async(file_path, session, branch=game_id) for file_path in files_to_fetch]
        results = await asyncio.gather(*coroutines)

        b_icon, b_logo, b_cover, b_background, b_patch, settings, patch_note_titles = results[:7]
        b_patch_notes = results[7:]

        game_info = {
            "art": {
                "icon": b_icon,
                "logo": b_logo,
                "cover": b_cover,
                "background": b_background,
                "patch": b_patch
            },
            "settings": settings,
            "notes": {
                "titles": patch_note_titles,
                "patch_notes": b_patch_notes
            },
            "id": game_id,
            "branch": game_branch
        }

        return game_info