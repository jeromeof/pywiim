#!/usr/bin/env python3
"""Quick verification script to check if new tests can be imported."""

import sys
import importlib.util

# Try to import the test module
spec = importlib.util.spec_from_file_location("test_player", "tests/unit/test_player.py")
if spec is None or spec.loader is None:
    print("ERROR: Could not load test_player.py")
    sys.exit(1)

try:
    test_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(test_module)
    print("✓ test_player.py imports successfully")
    
    # Check if new test classes exist
    classes_to_check = [
        "TestPlayerErrorHandling",
        "TestPlayerRoleTransitions", 
        "TestPlayerSourceConflicts"
    ]
    
    for class_name in classes_to_check:
        if hasattr(test_module, class_name):
            cls = getattr(test_module, class_name)
            test_count = len([m for m in dir(cls) if m.startswith("test_")])
            print(f"✓ {class_name} found with {test_count} test methods")
        else:
            print(f"✗ {class_name} NOT FOUND")
            sys.exit(1)
    
    print("\nAll new test classes found successfully!")
    
except Exception as e:
    print(f"ERROR importing test_player.py: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
