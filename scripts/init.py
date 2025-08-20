"""
Initialize the AI Interviewer application
- Create necessary directories
- Initialize database
- Check dependencies
"""

import os
import sys
from pathlib import Path

def create_directories():
    """Create necessary application directories"""
    directories = [
        "backend/app/data/audio",
        "backend/app/data/software_engineering",
        "backend/app/data/data_science", 
        "backend/app/data/ai_ml",
        "backend/app/data/hardware_ece",
        "backend/app/data/robotics",
        "backend/chroma_db",
    ]
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def check_environment():
    """Check if environment file exists"""
    env_file = Path("backend/.env")
    if not env_file.exists():
        print("📝 Creating .env file from template...")
        example_file = Path("backend/.env.example")
        if example_file.exists():
            import shutil
            shutil.copy(example_file, env_file)
            print("✅ Created backend/.env")
        else:
            print("❌ backend/.env.example not found")
            return False
    else:
        print("✅ backend/.env exists")
    return True

def main():
    """Main initialization function"""
    print("🚀 AI Interviewer - Python Initialization")
    print("==========================================")
    
    # Change to project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    print(f"📁 Working directory: {project_root}")
    
    # Create directories
    create_directories()
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    print("\n🎉 Initialization complete!")
    print("\nNext steps:")
    print("1. Install dependencies: make install-deps")
    print("2. Start development: make dev")
    print("3. Or run locally: make start-local")

if __name__ == "__main__":
    main()
