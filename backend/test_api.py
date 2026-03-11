# test_api_fixed.py
import requests
import time
import sys

BASE_URL = "http://127.0.0.1:5000"

def check_server():
    """Check if Flask server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        return True
    except requests.exceptions.ConnectionError:
        return False

def wait_for_server(timeout=10):
    """Wait for server to start"""
    print("Waiting for server to start...")
    for i in range(timeout):
        if check_server():
            print("✅ Server is running!")
            return True
        print(f"Attempt {i+1}/{timeout} - Server not ready...")
        time.sleep(1)
    return False

def test_home():
    print("\n🏠 Testing Home Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_api_endpoints():
    """Test all API endpoints"""
    
    # Test home
    if not test_home():
        print("\n❌ Cannot connect to server. Make sure Flask is running!")
        print("Run this command in another terminal:")
        print("cd C:\\Users\\nachi\\dabbas-complete-platform\\backend")
        print("venv\\Scripts\\activate")
        print("flask run")
        return False
    
    # Test health
    print("\n❤️ Testing Health Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test database
    print("\n💾 Testing Database...")
    try:
        response = requests.get(f"{BASE_URL}/api/test")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test cities
    print("\n🏙️ Testing Cities...")
    try:
        response = requests.get(f"{BASE_URL}/api/cities")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return True

if __name__ == "__main__":
    print("🚀 Dabba API Test Script")
    print("=" * 50)
    
    # First check if server is running
    if not check_server():
        print("❌ Flask server is not running!")
        print("\n📋 Instructions:")
        print("1. Open a NEW terminal (Terminal 1)")
        print("2. Run these commands:")
        print("   cd C:\\Users\\nachi\\dabbas-complete-platform\\backend")
        print("   venv\\Scripts\\activate")
        print("   flask run")
        print("\n3. Wait for server to start (you'll see 'Running on http://127.0.0.1:5000')")
        print("4. Open ANOTHER terminal (Terminal 2)")
        print("5. Run this test script again")
        sys.exit(1)
    
    # Run tests
    test_api_endpoints()
    
    print("\n" + "=" * 50)
    print("✅ Testing complete!")