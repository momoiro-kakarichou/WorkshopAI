import os
import sys
import subprocess
from defaults.config import InstallationConfig

python_path = InstallationConfig.PYTHON_PATH
if python_path == 'default':
    python_path = sys.executable

venv_path = './.venv'
requirements_path = './requirements.txt'

if not os.path.exists(venv_path):
    create_venv_command = [python_path, '-m', 'venv', venv_path]
    try:
        subprocess.run(create_venv_command, check=True)
        print('Python venv created.')
    except subprocess.CalledProcessError as e:
        print(f'Error while creating venv: {e}')
        sys.exit(1)
    
pip_path = os.path.join(venv_path, 'bin', 'pip') if os.name != 'nt' else os.path.join(venv_path, 'Scripts', 'pip.exe')
install_requirements_command = [pip_path, 'install', '-q', '-r', requirements_path]

try:
    subprocess.run(install_requirements_command, check=True)
    print('Python libraries installed.')
except subprocess.CalledProcessError as e:
    print(f'Error while installing libraries: {e}')

print('Running check_defaults.py to ensure default configurations and .env setup...')
venv_python_path = os.path.join(venv_path, 'bin', 'python') if os.name != 'nt' else os.path.join(venv_path, 'Scripts', 'python.exe')
check_defaults_command = [venv_python_path, 'check_defaults.py']
try:
    result = subprocess.run(check_defaults_command, check=True, capture_output=True, text=True, encoding='utf-8')
    print('check_defaults.py executed successfully.')
    if result.stdout:
        print("Output from check_defaults.py:", result.stdout)
except subprocess.CalledProcessError as e:
    print(f'Error while executing check_defaults.py: {e}')
    if e.stdout:
        print(f'Stdout: {e.stdout}')
    if e.stderr:
        print(f'Stderr: {e.stderr}')

flask_path = os.path.join(venv_path, 'bin', 'flask') if os.name != 'nt' else os.path.join(venv_path, 'Scripts', 'flask.exe')
migrations_folder = './migrations'

if os.path.exists(flask_path):
    print(f'Using Flask executable at: {flask_path}')
    
    if not os.path.exists(migrations_folder):
        print('Initializing database migration support (flask db init)...')
        db_init_command = [flask_path, 'db', 'init']
        try:
            result = subprocess.run(db_init_command, check=True, capture_output=True, text=True, encoding='utf-8')
            print('Database migration support initialized successfully.')
            if result.stdout:
                print("Output from db init:", result.stdout)
        except subprocess.CalledProcessError as e:
            print(f'Error during database migration initialization: {e}')
            if e.stdout:
                print(f'Stdout: {e.stdout}')
            if e.stderr:
                print(f'Stderr: {e.stderr}')
            print("This might happen if FLASK_APP is not set or there are issues with the project setup.")
    else:
        print(f'Migrations folder "{migrations_folder}" already exists. Skipping "flask db init".')

    print('Applying database migrations (flask db upgrade)...')
    db_upgrade_command = [flask_path, 'db', 'upgrade']
    try:
        result = subprocess.run(db_upgrade_command, check=True, capture_output=True, text=True, encoding='utf-8')
        print('Database migrations applied successfully.')
        if result.stdout:
            print("Output from db upgrade:", result.stdout)
    except subprocess.CalledProcessError as e:
        print(f'Error during database migration application: {e}')
        if e.stdout:
            print(f'Stdout: {e.stdout}')
        if e.stderr:
            print(f'Stderr: {e.stderr}')
        print("Please ensure your database is running, accessible, and FLASK_APP is set correctly.")
        sys.exit(1)
else:
    print(f'Flask executable not found at {flask_path}. Skipping database operations.')
    print('This might be because Flask (and Flask-Migrate) is not listed in requirements.txt or its installation failed.')
    print('If your application uses Flask-Migrate, these database steps are necessary.')

print('Installation script finished.')
