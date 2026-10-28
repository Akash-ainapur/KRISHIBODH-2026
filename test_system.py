"""
Test script for Plant Health Analysis System
"""
import os
import sys
from pathlib import Path

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")

    try:
        from config import GEMINI_API_KEY, AGENT_CONFIGS
        print("✅ Config import successful")
    except Exception as e:
        print(f"❌ Config import failed: {e}")
        return False

    try:
        from tools.gemini_tools import GeminiImageAnalyzer
        print("✅ Gemini tools import successful")
    except Exception as e:
        print(f"❌ Gemini tools import failed: {e}")
        return False

    try:
        from agents.plant_health_agents import PlantHealthCrew
        print("✅ Plant health agents import successful")
    except Exception as e:
        print(f"❌ Plant health agents import failed: {e}")
        return False

    return True

def test_configuration():
    """Test configuration settings"""
    print("\nTesting configuration...")

    try:
        from config import GEMINI_API_KEY, AGENT_CONFIGS, CREW_CONFIG

        if not GEMINI_API_KEY:
            print("⚠️  GEMINI_API_KEY not set - add it to .env file")
            return False
        else:
            print("✅ GEMINI_API_KEY is configured")

        if len(AGENT_CONFIGS) == 5:
            print("✅ All 5 agents configured")
        else:
            print(f"❌ Expected 5 agents, found {len(AGENT_CONFIGS)}")
            return False

        print("✅ Configuration validation successful")
        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_agent_initialization():
    """Test agent initialization without API calls"""
    print("\nTesting agent initialization...")

    try:
        from agents.plant_health_agents import PlantHealthCrew

        # Test crew creation (this will initialize Gemini API)
        crew = PlantHealthCrew()
        print("✅ Crew initialization successful")

        # Test agent status
        status = crew.get_agent_status()
        if len(status) == 5:
            print("✅ All 5 agents ready")
            for agent_name, agent_info in status.items():
                print(f"  - {agent_name}: {agent_info['role']}")
        else:
            print(f"❌ Expected 5 agents, found {len(status)}")
            return False

        return True

    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        return False

def test_image_validation():
    """Test image validation functions"""
    print("\nTesting image validation...")

    try:
        from tools.gemini_tools import validate_image_format, get_image_size_mb

        # Test format validation
        test_files = ["test.jpg", "test.png", "test.webp", "test.gif"]
        for test_file in test_files:
            is_valid = validate_image_format(test_file)
            expected = test_file != "test.gif"
            if is_valid == expected:
                print(f"✅ Format validation for {test_file}: {is_valid}")
            else:
                print(f"❌ Format validation failed for {test_file}")
                return False

        # Test size calculation (if test file exists)
        test_image = "README.md"  # Use existing file for size test
        if os.path.exists(test_image):
            size_mb = get_image_size_mb(test_image)
            print(f"✅ Size calculation: {size_mb:.2f} MB")
            if size_mb > 0:
                print("✅ Size calculation working")
            else:
                print("❌ Size calculation failed")
                return False

        return True

    except Exception as e:
        print(f"❌ Image validation test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Plant Health Analysis System - Test Suite")
    print("=" * 50)

    tests = [
        ("Import Tests", test_imports),
        ("Configuration Tests", test_configuration),
        ("Agent Initialization Tests", test_agent_initialization),
        ("Image Validation Tests", test_image_validation),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! System is ready for use.")
        print("\nNext steps:")
        print("1. Add your Gemini API key to .env file")
        print("2. Run: python api.py (for web interface)")
        print("   Or: python main.py <image_path> (for CLI)")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
