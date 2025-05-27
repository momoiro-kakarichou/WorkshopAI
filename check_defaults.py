import os
import shutil
import json
import argparse
from cryptography.fernet import Fernet

ENCRYPTION_KEY_ENV_VAR = 'WORKSHOP_AI_ENCRYPTION_KEY'

json_file_path = './defaults/paths.json'
parser = argparse.ArgumentParser(description="Copies the default files to their respective destinations.")
parser.add_argument('--force', action='store_true', help="Force default files recovery.")
args = parser.parse_args()

with open(json_file_path, 'r', encoding='utf-8') as file:
    file_list = json.load(file)

for file_info in file_list:
    source = file_info['source']
    destination = file_info['destination']
    
    if not os.path.exists(destination) or args.force:
        shutil.copy(source, destination)

env_file_path = './.env'
key_exists = False
lines = []

if os.path.exists(env_file_path):
    with open(env_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if line.startswith(f"{ENCRYPTION_KEY_ENV_VAR}="):
            key_exists = True
            if args.force:
                print(f"Force flag set. Regenerating {ENCRYPTION_KEY_ENV_VAR} in {env_file_path}")
                new_key = Fernet.generate_key()
                lines[i] = f"{ENCRYPTION_KEY_ENV_VAR}={new_key.decode()}\n"
            break

if not key_exists:
    print(f"{ENCRYPTION_KEY_ENV_VAR} not found in {env_file_path}. Generating and adding it.")
    new_key = Fernet.generate_key()
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'
    lines.append(f"{ENCRYPTION_KEY_ENV_VAR}={new_key.decode()}\n")
    with open(env_file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
elif args.force and key_exists:
    with open(env_file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
elif key_exists and not args.force:
    print(f"{ENCRYPTION_KEY_ENV_VAR} already exists in {env_file_path}. Use --force to overwrite.")
else:
    pass