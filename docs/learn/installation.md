# Installation & Scaffolding

Standardize and scaffold your architectural foundation in seconds using the ZCore CLI.

---

<div class="zcore-meta-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Type</span><br>
    <strong>CLI Utility</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Status</span><br>
    <strong>Core Tool</strong>
  </div>
  <div style="padding: 1rem; background: #18181b; border: 1px solid #27272a; border-radius: 0.375rem;">
    <span style="color: #a1a1aa; font-size: 0.8rem; text-transform: uppercase;">Underlying Tech</span><br>
    <strong>Pathlib / Subprocess</strong>
  </div>
</div>

## The Challenge
Unlike frameworks like Django, FastAPI does not provide a built-in "admin" or scaffolding tool. Developers often spend the first few hours of a project manually creating directories, setting up `main.py` entry points, configuring `.env` files, and writing repetitive boilerplate for every new domain module. This lack of structure leads to inconsistent layouts across different projects within the same team.

## The ZCore Elegance
ZCore provides the `zc` command-line interface. It handles project initialization, environment configuration, and modular "app" scaffolding with optional boilerplate templates, ensuring every project follows the same clean architectural patterns from day one.

=== "ZCore Scaffolding"
        :::bash
        # 1. Install the framework
        pip install fastapi-zcore-framework[all]

        # 2. Initialize a new project
        zc init my_awesome_api
        cd my_awesome_api

        # 3. Create a modular app with full boilerplate
        zc startapp billing --template

        # 4. Launch development server
        zc run

=== "FastAPI Manual Setup"
        :::bash
        # Standard FastAPI requires manual setup for everything:
        mkdir my_api && cd my_api
        touch main.py .env requirements.txt
        # (Open editor, manually copy-paste FastAPI boilerplate)
        # (Manually create subdirectories for billing)
        mkdir billing
        touch billing/models.py billing/schemas.py billing/routers.py
        # (Write repetitive CRUD logic for the 100th time...)
        uvicorn main:app --reload

---

## Getting Started

### 1. Installation
Install ZCore using `pip`. It is recommended to use a virtual environment. The `[all]` extra includes SQLAlchemy, Redis, and Argon2 support.

```bash
pip install fastapi-zcore-framework[all]
```

### 2. Initializing a Project
The `init` command creates the project root, a pre-configured `main.py`, a `.env` file with a generated `SECRET_KEY`, and a `requirements.txt`.

```bash
zc init my_project
```

### 3. Creating a Modular App
ZCore promotes a modular domain-driven structure. Each "app" is a directory containing its own models, services, and routers, wrapped in a `Plugin` class.

*   **Clean App:** Creates empty files for a clean slate.
    ```bash
    zc startapp orders
    ```
*   **Template App:** Populates files with ZCore's standard CRUD/Repository boilerplate.
    ```bash
    zc startapp orders --template
    ```

---

## Boundaries & Integration
The `zc` tool is a convenience utility, not a requirement. 

*   **Standard Python:** All files generated are standard `.py` files. You can modify, move, or delete them without breaking the CLI.
*   **Uvicorn Integration:** The `zc run` command is a wrapper for `uvicorn main:app --reload`. It automatically reads `HOST` and `PORT` from your `.env` file and ensures your `PYTHONPATH` is set correctly.
*   **Manual Control:** You are never locked into the CLI. If you prefer to write your own project structure from scratch, you can still import and use ZCore components (like `Kernel`, `BaseRouter`, or `BaseService`) manually.

---

## Under-the-Hood Spec

### 1. Cryptographically Secure Scaffolding
When you run `zc init`, the CLI uses Python's `secrets` module to generate a 64-character hex string for your `SECRET_KEY`. This ensures that even development environments start with high-entropy secrets, preventing common security oversights.

### 2. Environment-Aware Execution
The `zc run` command performs a sanity check to ensure `main.py` exists in the current directory. It dynamically injects the current working directory into `sys.path` (via `PYTHONPATH`) before launching Uvicorn, allowing modular imports to work seamlessly without manual path hacking.

### 3. Smart Path Evaluation
The `startapp` command uses `pathlib` to resolve absolute paths. It verifies that the requested app name is a valid Python identifier and checks for directory collisions before writing any files, preventing accidental data loss or malformed module names.