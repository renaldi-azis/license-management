# run_tests.py - Master test runner

from datetime import datetime
import json
import subprocess
import sys
import os
from pathlib import Path
import time

import requests


class TestRunner:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.test_files = [
            "test_integration.py",
            "test_security.py", 
            "test_logging.py"
        ]
    
    def check_prerequisites(self):
        """Check if all prerequisites are met."""
        print("🔍 Checking prerequisites...")
        
        issues = []
        
        # Check Python version
        result = subprocess.run(["python3", "--version"], capture_output=True, text=True)
        version = result.stdout.strip()
        if "3.8" not in version and "3.9" not in version and "3.10" not in version and "3.11" not in version:
            issues.append("Python 3.8+ required")
        
        # Check Redis
        result = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True)
        if "PONG" not in result.stdout:
            issues.append("Redis not running - start with 'brew services start redis'")
        
        # Check required files
        required_files = ["app.py", "requirements.txt", ".env", "models/database.py"]
        for file in required_files:
            if not os.path.exists(file):
                issues.append(f"Missing file: {file}")
        
        if issues:
            print("❌ Prerequisites issues:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        
        print("✅ All prerequisites met")
        return True
    
    def run_unit_tests(self):
        """Run Python unit tests."""
        print("\n🧪 Running unit tests...")
        result = subprocess.run(["pytest", "-v"], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        print(f"\n✅ Unit tests completed - Exit code: {result.returncode}")
        return result.returncode == 0
    
    def run_integration_tests(self):
        """Run integration tests against running server."""
        print("\n🔗 Running integration tests...")
        
        # Start server in background if not running
        if not self.is_server_running():
            print("🚀 Starting test server...")
            server_process = subprocess.Popen([
                sys.executable, "app.py"
            ])
            time.sleep(5)  # Wait for startup
        
        # Run integration tests
        for test_file in self.test_files:
            
            test_file = self.__dir__ + "/tests_cases/" + test_file
            test_file_path = os.path.join(self.__dir__, "tests_cases", test_file)
            print(f"\n--- {test_file_path} ---")
            if os.path.exists(test_file_path):
                print(f"\nRunning {test_file}...")
                result = subprocess.run([sys.executable, test_file], capture_output=True, text=True)
                
                print(result.stdout)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
                
                if result.returncode != 0:
                    print(f"❌ {test_file} failed")
                    return False
                else:
                    print(f"✅ {test_file} passed")
            else:
                print(f"⚠️  {test_file} not found - skipping")
        
        return True
    
    def is_server_running(self):
        """Check if Flask server is running."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def run_deployment_tests(self):
        """Run deployment readiness tests."""
        print("\n🚀 Running deployment tests...")
        
        if os.path.exists("test_deployment.sh"):
            result = subprocess.run(["./test_deployment.sh"], 
                                  capture_output=True, text=True, shell=True)
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return result.returncode == 0
        else:
            print("⚠️  test_deployment.sh not found - skipping")
            return True
    
    def generate_test_report(self):
        """Generate test report."""
        print("\n📋 Generating test report...")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "server_url": self.base_url,
            "tests": {
                "prerequisites": self.check_prerequisites(),
                "unit_tests": self.run_unit_tests(),
                "integration_tests": self.run_integration_tests(),
                "deployment_tests": self.run_deployment_tests()
            },
            "overall_status": "PASS"
        }
        
        # Check overall status
        all_passed = all(report["tests"].values())
        report["overall_status"] = "PASS" if all_passed else "FAIL"
        
        # Save report
        with open("test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(json.dumps(report, indent=2))
        print(f"\n📄 Test report saved to test_report.json")
        
        return all_passed
    
    def run_full_suite(self):
        """Run complete test suite."""
        print("🎯 License Server Complete Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            success = self.generate_test_report()
            
            duration = time.time() - start_time
            print(f"\n⏱️  Test suite completed in {duration:.1f} seconds")
            
            if success:
                print("\n🎉 ALL TESTS PASSED! 🚀")
                print("Your license server is ready for production!")
                return 0
            else:
                print("\n⚠️  SOME TESTS FAILED - Review the report above")
                return 1
                
        except KeyboardInterrupt:
            print("\n⏹️  Tests interrupted by user")
            return 130
        except Exception as e:
            print(f"\n💥 Unexpected test error: {e}")
            import traceback
            traceback.print_exc()
            return 1

if __name__ == "__main__":
    runner = TestRunner()
    sys.exit(runner.run_full_suite())