import os
import sys
import subprocess
import shutil
import requests
import py7zr
import winreg

DOWNLOAD_URL = "https://static.gaq9.com/maps/map_files.7z"
ARCHIVE_NAME = "map_files.7z"
SOURCE_DIR = "map_files"
TARGET_FOLDER_NAME = "maps"
SOURCES_FOLDER_NAME = "sources"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0"

def main_menu():
    print("\nTF2 Map Manager")
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

def find_tf2_installations():
    tf2_paths = []
    steam_locations = find_steam_installations()
    
    for location in steam_locations:
        potential_path = os.path.join(location, "steamapps", "common", "Team Fortress 2", "tf")
        if os.path.exists(potential_path):
            tf2_paths.append(potential_path)
    
    return tf2_paths

def select_tf2_installation(tf2_paths):
    if not tf2_paths:
        print("No TF2 installations found!")
        return None
    
    if len(tf2_paths) == 1:
        print(f"Auto-selected TF2 installation: {tf2_paths[0]}")
        return tf2_paths[0]
    
    print("\nFound TF2 installations:")
    for i, path in enumerate(tf2_paths, 1):
        print(f"{i}. {path}")
    
    while True:
        choice = input(f"\nSelect installation (1-{len(tf2_paths)}), or 'q' to quit: ")
        if choice.lower() == 'q':
            return None
        try:
            index = int(choice) - 1
            if 0 <= index < len(tf2_paths):
                return tf2_paths[index]
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

def get_available_maps():
    maps = {}
    if os.path.exists(SOURCE_DIR):
        for root, _, files in os.walk(SOURCE_DIR):
            for file in files:
                if file.lower().endswith('.bsp'):
                    maps[file] = os.path.join(root, file)
    return maps

def select_maps_to_install(available_maps):
    print("\nAvailable maps:")
    map_list = sorted(available_maps.keys())
    for i, map_file in enumerate(map_list, 1):
        print(f"{i}. {map_file}")
    
    print("\nEnter map numbers to install (comma separated), 'a' for all, or 'q' to cancel")
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

def install_selected_maps(tf2_path, selected_maps):
    target_dir = os.path.join(tf2_path, TARGET_FOLDER_NAME)
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

def uninstall_maps(tf2_path):
    target_dir = os.path.join(tf2_path, TARGET_FOLDER_NAME)
    sources_dir = os.path.join(target_dir, SOURCES_FOLDER_NAME)
    
    available_maps = get_available_maps()
    if not available_maps:
        print("No maps found to uninstall!")
        return
    
    selected_maps = select_maps_to_install(available_maps)
    if not selected_maps:
        return
    
    removed_maps = 0
    for map_file in selected_maps:
        map_path = os.path.join(target_dir, map_file)
        if os.path.exists(map_path):
            os.remove(map_path)
            removed_maps += 1
            print(f"Removed: {map_file}")
    
    if os.path.exists(sources_dir) and not os.listdir(target_dir):
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
            
        tf2_paths = find_tf2_installations()
        tf2_path = select_tf2_installation(tf2_paths)
        
        if not tf2_path:
            input("\nPress Enter to continue...")
            continue
            
        if choice == '1':
            if not download_and_extract():
                input("\nPress Enter to continue...")
                continue
            available_maps = get_available_maps()
            selected_maps = select_maps_to_install(available_maps)
            if selected_maps:
                install_selected_maps(tf2_path, selected_maps)
            cleanup()
        elif choice == '2':
            if not os.path.exists(SOURCE_DIR):
                if not download_and_extract():
                    input("\nPress Enter to continue...")
                    continue
            uninstall_maps(tf2_path)
            cleanup()
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()