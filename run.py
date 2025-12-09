#!/usr/bin/env python3
"""
Run script for Mental Health Chatbot
Usage: python run.py [--reload] [--port PORT]
"""
import os
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_environment():
    """Check if environment is properly configured"""
    from dotenv import load_dotenv
    
    # Load .env file
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print("✓ Loaded .env file")
    else:
        print("⚠ No .env file found. Using environment variables.")
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("✗ OPENAI_API_KEY not set!")
        print("  Please set it in .env file or as environment variable")
        return False
    
    print("✓ OpenAI API key configured")
    return True


def check_data():
    """Check if data files exist"""
    data_dir = project_root / "data"
    
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
        print(f"✓ Created data directory: {data_dir}")
    
    qa_file = data_dir / "dataset_qa.csv"
    if qa_file.exists():
        import pandas as pd
        df = pd.read_csv(qa_file, header=None)
        print(f"✓ Found QA dataset: {len(df)} entries")
    else:
        print("⚠ QA dataset not found at data/dataset_qa.csv")
    
    stmt_file = data_dir / "dataset_statements.csv"
    if stmt_file.exists():
        import pandas as pd
        df = pd.read_csv(stmt_file)
        print(f"✓ Found statements dataset: {len(df)} entries")
    else:
        print("⚠ Statements dataset not found (optional)")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Run Mental Health Chatbot")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--skip-checks", action="store_true", help="Skip environment checks")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Mental Health Support Chatbot")
    print("=" * 50)
    print()
    
    if not args.skip_checks:
        print("Checking environment...")
        if not check_environment():
            sys.exit(1)
        
        print()
        print("Checking data...")
        check_data()
        print()
    
    print(f"Starting server on {args.host}:{args.port}")
    print(f"API Docs: http://localhost:{args.port}/docs")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
