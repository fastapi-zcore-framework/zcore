import argparse

def main() -> None:
    parser = argparse.ArgumentParser(description="ZCore Framework CLI")
    parser.add_argument("--version", action="store_true", help="Show ZCore version")
    args = parser.parse_args()

    if args.version:
        print("ZCore Framework - Beta")
    else:
        print("ZCore CLI is running. (More commands coming in Phase 3)")

if __name__ == "__main__":
    main()