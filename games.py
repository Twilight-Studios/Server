import aiohttp, asyncio, github

def sanitize_game_metadata(metadata, available_branches):
    for key, value in metadata['settings'].items(): metadata[key] = value
    del metadata['settings']
    
    game_branches = list(metadata['game_branches'].keys())
    
    for branch in game_branches:
        if branch not in available_branches: del metadata['game_branches'][branch]
    
    if len(metadata['game_branches'].keys()) == 0: return None
    return metadata

def get_game_ids(whitelist_branches: list[str] = []) -> dict[str, list]:
    branches = github.get_all_games_repo_branches()
    forbidden_branches = ['main', 'beta', 'example']

    games = []
    for branch in branches:
        game_id = branch['name']
        
        if game_id in forbidden_branches: continue
        if whitelist_branches != [] and game_id not in whitelist_branches: continue
        
        games.append(game_id)

    return games

async def get_game_metadata(game_id: str, get_all=False, get_icon=False, get_logo=False, get_cover=False, get_background=False, get_patch_image=False, get_patch_notes=False):
    async with aiohttp.ClientSession() as session:
        files_to_fetch = [{"name": "settings", "path" : "settings.json"}]
        
        if get_icon or get_all: files_to_fetch.append({"name": "icon", "path" : "art/icon.png"})
        if get_logo or get_all: files_to_fetch.append({"name": "logo", "path" : "art/logo.png"})
        if get_cover or get_all: files_to_fetch.append({"name": "cover", "path" : "art/cover.png"})
        if get_background or get_all: files_to_fetch.append({"name": "background", "path" : "art/background.png"})
        if get_patch_image or get_all: files_to_fetch.append({"name": "patch", "path" : "art/patch.png"})
        
        non_patch_note_content_amount = len(files_to_fetch)
        
        if get_patch_notes or get_all:
            patch_note_urls = await github.load_file_async("notes", session, branch=game_id, return_github_json_wrapper=True)
            for note in patch_note_urls: files_to_fetch.append({"name": "note", "path" : f"notes/{note['name']}"})

        coroutines = [github.load_file_async(file_info["path"], session, branch=game_id) for file_info in files_to_fetch]
        results = await asyncio.gather(*coroutines)
        
        patch_notes = None
        if get_patch_notes or get_all: 
            patch_notes = results[non_patch_note_content_amount:]
            results = results[:non_patch_note_content_amount]
        
        metadeta = {}
        for index, data in enumerate(results):
            metadeta[files_to_fetch[index]["name"]] = data
            
        if get_patch_notes or get_all: metadeta["patch_notes"] = patch_notes
        metadeta['id'] = game_id
        
        return metadeta