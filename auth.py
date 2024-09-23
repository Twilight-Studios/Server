import github

def get_playtester(playtester_id):
    playtesters = github.load_file("access.json")
    if playtester_id not in playtesters: return None
    return playtesters[playtester_id]