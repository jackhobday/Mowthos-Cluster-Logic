import requests
import json
import time
from typing import Dict, List

BASE_URL = "http://localhost:8000"

class MowthosCLI:
    def __init__(self):
        # Remove all CLI options and functions except test_road_aware_adjacency
        pass
        
    def clear_screen(self):
        """Clear the terminal screen."""
        print("\n" * 50)
        
    def print_header(self):
        """Print the Mowthos header."""
        print("""
╔══════════════════════════════════════════════════════════════╗
║                        MOWTHOS                               ║
║                    Cluster Management                        ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
    def print_menu(self):
        """Print the main menu."""
        print("""
Options:
1. Test Road-Aware Adjacency (NEW)
2. Exit

Enter your choice (1-2): """, end="")
        
    def test_road_aware_adjacency(self):
        """Handle option 4: Test Road-Aware Adjacency."""
        self.clear_screen()
        self.print_header()
        
        print("🛣️ ROAD-AWARE ADJACENCY TESTING")
        print("=" * 50)
        print("This tests if two homes can be connected without crossing roads.")
        print("Perfect for homes with contiguous backyards on different streets.\n")
        
        # Get two addresses from user
        address1 = input("Enter first address: ").strip()
        if not address1:
            print("❌ Address cannot be empty!")
            input("Press Enter to continue...")
            return
            
        address2 = input("Enter second address: ").strip()
        if not address2:
            print("❌ Address cannot be empty!")
            input("Press Enter to continue...")
            return
        
        print(f"\n🔍 Testing adjacency between:")
        print(f"   Address 1: {address1}")
        print(f"   Address 2: {address2}")
        print("\n⏳ Processing...")
        
        # Test adjacency with road detection
        result = self.test_adjacency_with_road_detection(address1, address2)
        
        print(f"\n📊 RESULTS:")
        print(f"   Distance: {result.get('distance_miles', 0):.4f} miles")
        print(f"   Same side of street: {'✅ Yes' if result.get('same_side_of_street') else '❌ No'}")
        print(f"   No road crossing: {'✅ Yes' if result.get('no_road_crossing') else '❌ No'}")
        print(f"   Final Result: {'✅ ADJACENT' if result.get('adjacent') else '❌ NOT ADJACENT'}")
        print(f"   Details: {result.get('message', 'No details available')}")
        
        input("\nPress Enter to continue...")
        
    def test_adjacency_with_road_detection(self, host_address: str, neighbor_address: str) -> dict:
        """Test if two addresses are adjacent with road-aware detection using our API."""
        resp = requests.post(f"{BASE_URL}/clusters/test_adjacency_with_road_detection", json={
            "address1": host_address,
            "address2": neighbor_address
        })
        
        if resp.status_code == 200:
            return resp.json()
        return {"adjacent": False, "message": "API error"}
        
    def run(self):
        """Main application loop."""
        while True:
            try:
                self.clear_screen()
                self.print_header()
                self.print_menu()
                
                choice = input().strip()
                
                if choice == "1":
                    self.test_road_aware_adjacency()
                elif choice == "2":
                    print("\n👋 Thank you for using Mowthos Cluster Management!")
                    print("   Goodbye!")
                    break
                else:
                    print("\n❌ Invalid choice. Please enter 1 or 2.")
                    input("Press Enter to continue...")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ An error occurred: {str(e)}")
                input("Press Enter to continue...")

if __name__ == "__main__":
    print("🚀 Starting Mowthos CLI...")
    print("   Make sure the FastAPI server is running on http://localhost:8000")
    print("   Press Ctrl+C to exit at any time.\n")
    
    cli = MowthosCLI()
    cli.run() 