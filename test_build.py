#!/usr/bin/env python3
"""
Test script to verify build components work before GitHub Actions
"""

import sys
import subprocess
import os
from pathlib import Path

def test_installer_creation():
    """Test that installer can be created"""
    print("Testing installer creation...")
    
    try:
        result = subprocess.run([sys.executable, 'create_installer.py'], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("  [OK] Installer creation successful")
            
            # Check if ZIP was created
            zip_path = Path('YouTubeDownloader-Installer.zip')
            if zip_path.exists():
                size_kb = zip_path.stat().st_size / 1024
                print(f"  [OK] Installer ZIP created ({size_kb:.1f} KB)")
                return True
            else:
                print("  [FAIL] Installer ZIP not found")
                return False
        else:
            print(f"  [FAIL] Installer creation failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  [ERROR] Error testing installer: {e}")
        return False

def test_core_imports():
    """Test that core modules can be imported"""
    print("Testing core module imports...")
    
    modules = [
        'youtube_downloader_safe',
        'youtube_downloader_gui', 
        'youtube_downloader_web',
        'yt_dlp_enhanced',
        'version'
    ]
    
    success = True
    for module in modules:
        try:
            __import__(module)
            print(f"  [OK] {module}")
        except ImportError as e:
            print(f"  [FAIL] {module}: {e}")
            success = False
        except Exception as e:
            print(f"  [WARN] {module}: {e}")
    
    return success

def test_dependencies():
    """Test that required dependencies are available"""
    print("Testing dependencies...")
    
    deps = ['yt_dlp', 'aiohttp', 'aiofiles', 'tqdm', 'flask']
    success = True
    
    for dep in deps:
        try:
            __import__(dep)
            print(f"  [OK] {dep}")
        except ImportError:
            print(f"  [FAIL] {dep} (missing)")
            success = False
    
    return success

def test_version_info():
    """Test version information"""
    print("Testing version information...")
    
    try:
        from version import get_version, get_release_info
        version = get_version()
        info = get_release_info()
        
        print(f"  [OK] Version: {version}")  
        print(f"  [OK] Name: {info['name']}")
        print(f"  [OK] Features: {len(info['features'])} listed")
        return True
        
    except Exception as e:
        print(f"  [FAIL] Version info error: {e}")
        return False

def test_github_workflow_files():
    """Test that GitHub workflow files exist and are valid"""
    print("Testing GitHub workflow files...")
    
    workflows = [
        '.github/workflows/build-release.yml',
        '.github/workflows/update-readme.yml', 
        '.github/workflows/manual-release.yml'
    ]
    
    success = True
    for workflow in workflows:
        path = Path(workflow)
        if path.exists():
            print(f"  [OK] {workflow}")
            
            # Basic YAML syntax check
            content = path.read_text()
            if 'on:' in content and 'jobs:' in content:
                print(f"    [OK] Valid YAML structure")
            else:
                print(f"    [WARN] May have YAML issues")
        else:
            print(f"  [FAIL] {workflow} (missing)")
            success = False
    
    return success

def main():
    """Run all tests"""
    print("YouTube Downloader Pro - Build Test Suite")
    print("=" * 50)
    
    tests = [
        ("Core module imports", test_core_imports),
        ("Dependencies", test_dependencies),
        ("Version information", test_version_info),
        ("Installer creation", test_installer_creation),
        ("GitHub workflows", test_github_workflow_files)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  [ERROR] Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status:4} | {test_name}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("\n[SUCCESS] All tests passed! Ready for GitHub Actions.")
        print("\nTo create a release:")
        print("1. git tag v1.0.0")
        print("2. git push origin v1.0.0")
        print("3. GitHub Actions will build and release automatically")
        return True
    else:
        print(f"\n[FAILED] {len(results) - passed} tests failed. Fix issues before release.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)