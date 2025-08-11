#!/usr/bin/env python3
"""
Build script for creating a distributable ODInfo application using PyInstaller.

This script:
1. Installs required dependencies
2. Runs PyInstaller to create the executable
3. Creates a distribution folder with the executable and external config template
4. Provides instructions for end users
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

def run_command(cmd, description, timeout=600):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, timeout=timeout)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.TimeoutExpired:
        print(f"ERROR: {description} timed out after {timeout} seconds!")
        return False
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {description} failed!")
        print(f"Command: {cmd}")
        print(f"Return code: {e.returncode}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return False
    except KeyboardInterrupt:
        print(f"ERROR: {description} was interrupted!")
        return False

def check_dependencies():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"PyInstaller found: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("PyInstaller not found. Installing...")
        return run_command("pip install pyinstaller", "Installing PyInstaller")

def build_executable():
    """Run PyInstaller to create the executable."""
    if not os.path.exists("odinfo.spec"):
        print("ERROR: odinfo.spec file not found!")
        return False
    
    return run_command("pyinstaller odinfo.spec", "Building executable with PyInstaller")

def create_distribution():
    """Create distribution folder with executable and external files."""
    print("\nCreating distribution folder...")
    
    # Determine executable name based on platform
    exe_name = "odinfo.exe" if platform.system() == "Windows" else "odinfo"
    dist_exe_path = os.path.join("dist", exe_name)
    
    if not os.path.exists(dist_exe_path):
        print(f"ERROR: Expected executable not found at: {dist_exe_path}")
        return False
    
    # Create distribution folder with odinfo subfolder
    dist_folder = "publish"
    if os.path.exists(dist_folder):
        shutil.rmtree(dist_folder)
    os.makedirs(dist_folder)
    
    # Create the odinfo subfolder that users will get when they unzip
    odinfo_folder = os.path.join(dist_folder, "odinfo")
    os.makedirs(odinfo_folder)
    
    # Copy executable
    shutil.copy2(dist_exe_path, odinfo_folder)
    print(f"Copied executable to {odinfo_folder}/")
    
    # Create README for distribution
    readme_content = '''# ODInfo - Packaged Application

## First Time Setup

1. **Run the application once** - It will create template configuration files for you
2. **Edit the configuration files**:
   - `instance/secret.txt` - Add your OpenDominion credentials and settings
   - `instance/users.json` - Set your web interface login credentials
3. **Update the round number** in secret.txt to match the current OpenDominion round

## Running the Application

Double-click the odinfo executable (or run from command line).

The application will:
- Create an `instance/` folder with template config files (first run only)
- Check your configuration files and prompt you to edit them if needed
- Create the database if it doesn't exist  
- Start the web server (usually at http://localhost:5000)

## Upgrading

When upgrading to a new version:
- Your existing `instance/` folder (with config and database) will be preserved
- Simply replace the old executable with the new one
- Your settings and data will remain intact

## Troubleshooting

- If the app exits immediately, check that you've edited the config files
- Look for error messages - they will guide you to what needs to be fixed
- Database files are created automatically - don't delete them unless you want to reset
- For help, check the original project documentation or OpenDominion Discord

## What's in the instance folder:

- `secret.txt` - Your personal configuration (credentials, settings)
- `users.json` - Web interface login settings
- `*.sqlite` - Your game data database(s)
'''
    
    with open(os.path.join(odinfo_folder, "README.md"), "w") as f:
        f.write(readme_content)
    
    print(f"Distribution created in '{dist_folder}/' folder")
    return True

def main():
    """Main build process."""
    print("ODInfo Build Script")
    print("=" * 50)
    
    # Check we're in the right directory
    if not os.path.exists("odinfo.spec"):
        print("ERROR: Run this script from the odinfo project root directory")
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Build executable
    if not build_executable():
        sys.exit(1)
    
    # Create distribution
    if not create_distribution():
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("BUILD SUCCESSFUL!")
    print("\nNext steps:")
    print("1. Test the executable in publish/")
    print("2. Edit the configuration files as needed")
    print("3. Distribute the publish/ folder to end users")
    print("\nEnd users will need to edit instance/secret.txt and instance/users.json")

if __name__ == "__main__":
    main()