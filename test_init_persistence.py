"""
Test script to verify initialization persistence across multiple runs.
This simulates multiple app restarts/refreshes to ensure init commands only run once.
"""
import os
import time
import subprocess
import sys

def cleanup_marker():
    """Remove the initialization marker file if it exists."""
    marker_file = ".streamlit/.init_executed"
    if os.path.exists(marker_file):
        os.remove(marker_file)
        print(f"✓ Cleaned up marker file: {marker_file}")
    else:
        print(f"ℹ No marker file to clean up")

def check_marker_exists():
    """Check if the initialization marker file exists."""
    marker_file = ".streamlit/.init_executed"
    exists = os.path.exists(marker_file)
    if exists:
        with open(marker_file, 'r') as f:
            content = f.read()
        print(f"✓ Marker file exists: {marker_file}")
        print(f"  Content: {content.strip()}")
    else:
        print(f"✗ Marker file does not exist: {marker_file}")
    return exists

def test_init_persistence():
    """Test that initialization only runs once."""
    print("=" * 60)
    print("Testing Initialization Persistence")
    print("=" * 60)
    
    # Step 1: Clean up any existing marker
    print("\n[Step 1] Cleaning up existing marker file...")
    cleanup_marker()
    
    # Step 2: Verify marker doesn't exist
    print("\n[Step 2] Verifying marker file doesn't exist...")
    if check_marker_exists():
        print("✗ FAIL: Marker file should not exist after cleanup")
        return False
    
    # Step 3: Import and run the initialization check
    print("\n[Step 3] First run - initialization should execute...")
    try:
        # Import the module to trigger initialization logic
        import streamlit_app
        
        # Simulate the initialization check
        should_init_first = streamlit_app.should_execute_init()
        print(f"  should_execute_init() returned: {should_init_first}")
        
        if not should_init_first:
            print("✗ FAIL: Initialization should run on first execution")
            return False
        
        # Simulate creating the marker file
        streamlit_app.execute_init_commands()
        time.sleep(0.5)  # Give it time to create the file
        
        print("✓ PASS: First run triggered initialization")
        
    except Exception as e:
        print(f"✗ FAIL: Error during first run: {str(e)}")
        return False
    
    # Step 4: Verify marker was created
    print("\n[Step 4] Verifying marker file was created...")
    if not check_marker_exists():
        print("✗ FAIL: Marker file should exist after initialization")
        return False
    print("✓ PASS: Marker file created successfully")
    
    # Step 5: Simulate second run (page refresh)
    print("\n[Step 5] Second run - initialization should be skipped...")
    try:
        # Reload the module to simulate a fresh import
        import importlib
        importlib.reload(streamlit_app)
        
        should_init_second = streamlit_app.should_execute_init()
        print(f"  should_execute_init() returned: {should_init_second}")
        
        if should_init_second:
            print("✗ FAIL: Initialization should NOT run on second execution")
            return False
        
        print("✓ PASS: Second run skipped initialization")
        
    except Exception as e:
        print(f"✗ FAIL: Error during second run: {str(e)}")
        return False
    
    # Step 6: Final verification
    print("\n[Step 6] Final verification...")
    if not check_marker_exists():
        print("✗ FAIL: Marker file should still exist")
        return False
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
    print("\nSummary:")
    print("  - First run: Initialization executed ✓")
    print("  - Marker file created ✓")
    print("  - Second run: Initialization skipped ✓")
    print("  - Marker file persisted ✓")
    
    return True

if __name__ == "__main__":
    try:
        success = test_init_persistence()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
