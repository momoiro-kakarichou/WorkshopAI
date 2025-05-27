# Workshop AI
## Installation

Requirements: git, Python >= 3.12

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/momoiro-kakarichou/WorkshopAI.git
    cd WorkshopAI
    ```

2.  **Run the installation script:**
    This script will create a Python virtual environment, install the required dependencies from [`requirements.txt`](requirements.txt:1), set up default configurations by running [`check_defaults.py`](check_defaults.py:1), and prepare the database.
    ```bash
    python install.py
    ```
    Or, if you need to specify a particular Python interpreter:
    ```bash
    /path/to/your/python install.py
    ```
    The script will create a virtual environment in the `.venv` directory.

## Running the Application

1.  **Activate the virtual environment:**
    *   On Windows:
        ```bash
        .\.venv\Scripts\activate
        ```
    *   On macOS and Linux:
        ```bash
        source .venv/bin/activate
        ```

2.  **Run the application:**
    Once the virtual environment is activated, start the application using [`run.py`](run.py:1):
    ```bash
    python run.py
    ```

    The application should now be running. Check your terminal output for the address (e.g., `http://127.0.0.1:5000/`).