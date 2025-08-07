import os
import sys
import subprocess
import shutil
import requests
import py7zr
import winreg
import re

DOWNLOAD_URL = "https://static.gaq9.com/maps/map_files.7z"
ARCHIVE_NAME = "map_files.7z"
SOURCE_DIR = "map_files"
TARGET_FOLDER_NAME = "maps"
SOURCES_FOLDER_NAME = "sources"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0"

SOURCE_GAMES = {
    220: {"name": "Half-Life 2", "subdir": "hl2"},
    240: {"name": "Counter-Strike: Source", "subdir": "cstrike"},
    280: {"name": "Half-Life: Source", "subdir": "hl1"},
    360: {"name": "Half-Life Deathmatch: Source", "subdir": "hl2mp"},
    380: {"name": "Half-Life 2: Episode One", "subdir": "episodic"},
    400: {"name": "Portal", "subdir": "portal"},
    420: {"name": "Half-Life 2: Episode Two", "subdir": "ep2"},
    440: {"name": "Team Fortress 2", "subdir": "tf"},
    500: {"name": "Left 4 Dead", "subdir": "left4dead"},
    550: {"name": "Left 4 Dead 2", "subdir": "left4dead2"},
    620: {"name": "Portal 2", "subdir": "portal2"},
    730: {"name": "Counter-Strike: Global Offensive", "subdir": "csgo"},
}

def main_menu():
    print("\nSource Map Manager")
    print("1. Install maps")
    print("2. Uninstall maps")
    print("3. Exit")
    while True:
        choice = input("Select option (1-3): ")
        if choice in ('1', '2', '3'):
            return choice
        print("Invalid choice!")

def find_steam_installations():
    steam_paths = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Valve\\Steam") as key:
            steam_paths.append(winreg.QueryValueEx(key, "InstallPath")[0])
    except:
        pass
    
    library_folders = []
    for steam_path in steam_paths:
        lib_file = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
        if os.path.exists(lib_file):
            with open(lib_file, 'r') as f:
                for line in f:
                    if '"path"' in line:
                        path = line.split('"')[3].replace('\\\\', '\\')
                        library_folders.append(path)
    
    return steam_paths + library_folders

def find_source_games():
    games = []
    steam_locations = find_steam_installations()
    for location in steam_locations:
        appmanifest_dir = os.path.join(location, "steamapps")
        if os.path.isdir(appmanifest_dir):
            for filename in os.listdir(appmanifest_dir):
                if filename.startswith('appmanifest_') and filename.endswith('.acf'):
                    try:
                        appid = int(filename.split('_')[1].split('.')[0])
                        if appid in SOURCE_GAMES:
                            manifest_path = os.path.join(appmanifest_dir, filename)
                            with open(manifest_path, 'r') as f:
                                content = f.read()
                            installdir_match = re.search(r'"installdir"\s*"(.*?)"', content)
                            name_match = re.search(r'"name"\s*"(.*?)"', content)
                            if installdir_match:
                                installdir = installdir_match.group(1).replace('\\\\', '\\')
                                name = name_match.group(1) if name_match else SOURCE_GAMES[appid]['name']
                                game_dir = os.path.join(location, 'steamapps', 'common', installdir)
                                if os.path.exists(game_dir):
                                    subdir = SOURCE_GAMES[appid]['subdir']
                                    full_path = os.path.join(game_dir, subdir)
                                    if os.path.exists(full_path):
                                        games.append({'name': name, 'path': full_path})
                    except:
                        pass
    return games

def select_source_game(games):
    if not games:
        print("No Source games found!")
        return None
    
    if len(games) == 1:
        print(f"Auto-selected {games[0]['name']} installation: {games[0]['path']}")
        return games[0]['path']
    
    print("\nFound Source games:")
    for i, game in enumerate(games, 1):
        print(f"{i}. {game['name']} - {game['path']}")
    
    while True:
        choice = input(f"\nSelect installation (1-{len(games)}), or 'q' to quit: ")
        if choice.lower() == 'q':
            return None
        try:
            index = int(choice) - 1
            if 0 <= index < len(games):
                return games[index]['path']
        except ValueError:
            pass
        print("Invalid selection!")

def download_and_extract():
    try:
        print("\nDownloading map package...")
        headers = {'User-Agent': USER_AGENT}
        with requests.get(DOWNLOAD_URL, headers=headers, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            with open(ARCHIVE_NAME, 'wb') as f:
                downloaded = 0
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    print(f"\rProgress: {downloaded/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB", end='')
        print("\nDownload complete!")

        print("Extracting files...")
        with py7zr.SevenZipFile(ARCHIVE_NAME, mode='r') as z:
            z.extractall(SOURCE_DIR)
        return True
    except Exception as e:
        print(f"\nError: {str(e)}")
        return False

def get_latest_maps():
    from collections import defaultdict
    map_versions = defaultdict(list)
    
    if os.path.exists(SOURCE_DIR):
        for root, _, files in os.walk(SOURCE_DIR):
            for file in files:
                if file.lower().endswith('.bsp'):
                    lower_file = file.lower()
                    match_v = re.match(r'^(.*?)_v(\d+)\.bsp$', lower_file)
                    if match_v:
                        base_lower, ver = match_v.groups()
                        base_length = len(base_lower)
                        original_base = file[:base_length]
                        map_versions[base_lower].append((int(ver), file, os.path.join(root, file), original_base))
                    else:
                        match_a = re.match(r'^(.*?)_anomi\.bsp$', lower_file)
                        if match_a:
                            base_lower = match_a.group(1)
                            base_length = len(base_lower)
                            original_base = file[:base_length]
                            map_versions[base_lower].append((9999, file, os.path.join(root, file), original_base))
                        else:
                            # Non-versioned
                            base_lower = lower_file[:-4]
                            original_base = file[:-4]
                            map_versions[base_lower].append((0, file, os.path.join(root, file), original_base))
    
    latest_maps = {}
    for base_lower, versions in map_versions.items():
        if versions:
            max_ver, original_file, path, original_base = max(versions, key=lambda x: x[0])
            display_name = f"{original_base}.bsp"
            latest_maps[display_name] = path
    
    return latest_maps

def get_installed_maps(target_dir):
    maps = {}
    if os.path.exists(target_dir):
        for file in os.listdir(target_dir):
            if file.lower().endswith('.bsp'):
                maps[file] = os.path.join(target_dir, file)
    return maps

def select_maps(available_maps, action="install"):
    print(f"\nAvailable maps to {action}:")
    map_list = sorted(available_maps.keys())
    for i, map_file in enumerate(map_list, 1):
        print(f"{i}. {map_file}")
    
    print(f"\nEnter map numbers to {action} (comma separated), 'a' for all, or 'q' to cancel")
    while True:
        choice = input("Selection: ").strip().lower()
        if choice == 'q':
            return None
        if choice == 'a':
            return available_maps
        
        selected_maps = {}
        try:
            indices = [int(x.strip()) - 1 for x in choice.split(',')]
            for i in indices:
                if 0 <= i < len(map_list):
                    map_file = map_list[i]
                    selected_maps[map_file] = available_maps[map_file]
            if selected_maps:
                return selected_maps
        except:
            pass
        print("Invalid selection!")

def install_selected_maps(game_path, selected_maps):
    target_dir = os.path.join(game_path, TARGET_FOLDER_NAME)
    sources_dir = os.path.join(target_dir, SOURCES_FOLDER_NAME)
    
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(sources_dir, exist_ok=True)

    bsp_count = 0
    other_count = 0

    for map_file, src_path in selected_maps.items():
        dest = os.path.join(target_dir, map_file)
        if os.path.exists(dest):
            os.remove(dest)
        shutil.move(src_path, dest)
        bsp_count += 1
        print(f"Installed: {map_file}")

    for root, _, files in os.walk(SOURCE_DIR):
        for file in files:
            if not file.lower().endswith('.bsp'):
                src_path = os.path.join(root, file)
                dest = os.path.join(sources_dir, file)
                if os.path.exists(dest):
                    os.remove(dest)
                shutil.move(src_path, dest)
                other_count += 1

    print(f"\nInstalled {bsp_count} BSP files")
    print(f"Moved {other_count} supporting files")

def uninstall_maps(game_path):
    target_dir = os.path.join(game_path, TARGET_FOLDER_NAME)
    sources_dir = os.path.join(target_dir, SOURCES_FOLDER_NAME)
    
    installed_maps = get_installed_maps(target_dir)
    if not installed_maps:
        print("No maps found to uninstall!")
        return
    
    selected_maps = select_maps(installed_maps, action="uninstall")
    if not selected_maps:
        return
    
    removed_maps = 0
    for map_file, map_path in selected_maps.items():
        if os.path.exists(map_path):
            os.remove(map_path)
            removed_maps += 1
            print(f"Removed: {map_file}")
    
    # Optionally remove sources if no maps left
    if os.path.exists(sources_dir) and not any(f.endswith('.bsp') for f in os.listdir(target_dir)):
        shutil.rmtree(sources_dir)
        print("Removed sources folder")
    
    print(f"\nRemoved {removed_maps} map files")

def cleanup():
    if os.path.exists(ARCHIVE_NAME):
        os.remove(ARCHIVE_NAME)
    if os.path.exists(SOURCE_DIR):
        shutil.rmtree(SOURCE_DIR)

def main():

    while True:
        choice = main_menu()
        
        if choice == '3':
            break
            
        games = find_source_games()
        selected_path = select_source_game(games)
        
        if not selected_path:
            input("\nPress Enter to continue...")
            continue
            
        if choice == '1':
            if not download_and_extract():
                input("\nPress Enter to continue...")
                continue
            available_maps = get_latest_maps()
            selected_maps = select_maps(available_maps)
            if selected_maps:
                install_selected_maps(selected_path, selected_maps)
            cleanup()
        elif choice == '2':
            uninstall_maps(selected_path)
            # No need for download/extract for uninstall now
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()