import argparse
import sys
from zcore.cli.commands import start_app

def main() -> None:
    parser = argparse.ArgumentParser(
        description="ZCore Enterprise Framework CLI",
        prog="zc"
    )
    
    parser.add_argument("--version", action="store_true", help="Show the ZCore version")
    
    subparsers = parser.add_subparsers(dest="command", help="Available Commands")
    
    startapp_parser = subparsers.add_parser(
        "startapp", 
        help="Creates a new ZCore modular app (Model, Repo, Service, Router, Schema)"
    )
    startapp_parser.add_argument(
        "name", 
        type=str, 
        help="Name of the app (e.g., user_profile, product)"
    )

    args = parser.parse_args()

    if args.version:
        print("ZCore Framework - Version 0.1.0-Beta")
        sys.exit(0)

    if args.command == "startapp":
        app_name = args.name
        # Validation for clean python module names
        if not app_name.isidentifier():
            print(f"❌ Error: '{app_name}' is not a valid Python module name.")
            print("Use lowercase words separated by underscores (e.g., payment_gateway).")
            sys.exit(1)
            
        start_app(app_name)
    else:
        parser.print_help()
        sys.exit(0)