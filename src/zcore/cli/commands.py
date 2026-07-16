# src/zcore/cli/commands.py
import os
import sys
import secrets
import subprocess
from pathlib import Path
from .templates import (
    MAIN_PY_TEMPLATE,
    ENV_TEMPLATE,
    REQUIREMENTS_TEMPLATE,
    GITIGNORE_TEMPLATE,
    MODEL_TEMPLATE,
    SCHEMA_TEMPLATE,
    REPOSITORY_TEMPLATE,
    SERVICE_TEMPLATE,
    ROUTER_TEMPLATE,
    PLUGIN_TEMPLATE
)

def create_file(path: Path, content: str) -> None:
    if path.exists():
        print(f"⚠️  Skip: {path} already exists.")
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Created: {path}")

def init_project(project_name: str) -> None:
    project_dir = Path(project_name.lower())
    if project_dir.exists():
        print(f"❌ Error: Directory '{project_dir}' already exists.")
        sys.exit(1)

    project_dir.mkdir(parents=True)
    generated_secret = secrets.token_hex(32)
    
    files_to_create = {
        "main.py": MAIN_PY_TEMPLATE,
        ".env": ENV_TEMPLATE.format(project_name=project_name, secret_key=generated_secret),
        "requirements.txt": REQUIREMENTS_TEMPLATE,
        ".gitignore": GITIGNORE_TEMPLATE
    }

    print(f"\n🧱 Initializing ZCore Project: '{project_name}'...")
    for filename, content in files_to_create.items():
        create_file(project_dir / filename, content)
        
    db_file = project_dir / "zcore_dev.db"
    db_file.touch()
    print(f"✅ Created: {db_file}")
        
    print(f"\n🎉 Project '{project_name}' initialized successfully!")
    print(f"👉 Run: 'cd {project_name}' and run 'python -m zcore.cli startapp <app_name>' to generate a plugin!")

def start_app(app_name: str, with_template: bool = False) -> None:
    app_dir = Path(app_name.lower())
    
    if app_dir.exists():
        print(f"❌ Error: App folder '{app_dir}' already exists.")
        sys.exit(1)

    app_dir.mkdir(parents=True)
    
    model_name = "".join(word.capitalize() for word in app_name.split("_"))
    table_name = app_name.lower()
    
    context = {
        "ModelName": model_name,
        "table_name": table_name,
        "app_name": table_name,
        "project_name": Path(os.getcwd()).name
    }

    files_to_create = {
        "__init__.py": "",
        "models.py": MODEL_TEMPLATE.format(**context) if with_template else "",
        "schemas.py": SCHEMA_TEMPLATE.format(**context) if with_template else "",
        "repositories.py": REPOSITORY_TEMPLATE.format(**context) if with_template else "",
        "services.py": SERVICE_TEMPLATE.format(**context) if with_template else "",
        "routers.py": ROUTER_TEMPLATE.format(**context) if with_template else "",
        "plugin.py": PLUGIN_TEMPLATE.format(**context)
    }

    print(f"\n🚀 Scaffolding ZCore Domain App (with Built-In Plugin): {model_name}..."
           if with_template else f"\n💫 Scaffolding Clean ZCore App (WITHOUT Boilerplate): {model_name}...")
    for filename, content in files_to_create.items():
        create_file(app_dir / filename, content)
        
    print(f"\n🎉 Modular App '{app_name}' created successfully with its core Plugin wrapper!")
    print("👉 REGISTER this plugin in your main.py:")
    print(f"   from {app_name}.plugin import {model_name}Plugin")
    print(f"   kernel.add_plugin({model_name}Plugin())")

def run_server() -> None:
    if not os.path.exists("main.py"):
        print("❌ Error: 'main.py' not found in current directory. Are you in a ZCore project root?")
        sys.exit(1)

    host = "127.0.0.1"
    port = "8000"

    if os.path.exists(".env"):
        with open(".env", "r") as env_file:
            for line in env_file:
                if line.strip() and not line.startswith("#"):
                    parts = line.strip().split("=", 1)
                    if len(parts) == 2:
                        key, val = parts[0].strip(), parts[1].strip()
                        if key == "HOST":
                            host = val
                        elif key == "PORT":
                            port = val

    print(f"📡 Starting ZCore Dev Server on {host}:{port}...")
    
    env = os.environ.copy()
    current_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f".{os.pathsep}{current_pythonpath}" if current_pythonpath else "."

    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "main:app", f"--host={host}", f"--port={port}", "--reload"],
            env=env,
            check=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server shutdown cleanly.")
    except Exception as e:
        print(f"❌ Failed to run Uvicorn dev server: {e}")