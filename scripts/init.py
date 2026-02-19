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
        "backend/src/main/resources/data/software_engineering",
        "backend/src/main/resources/data/data_science", 
        "backend/src/main/resources/data/ai_ml",
        "backend/src/main/resources/data/hardware_ece",
        "backend/src/main/resources/data/robotics",
    ]
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def check_environment():
    """Check if Java is available"""
    import shutil
    java_available = shutil.which("java") is not None
    if java_available:
        print("✅ Java is available")
    else:
        print("❌ Java not found. Please install JDK 17+.")
        return False
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
