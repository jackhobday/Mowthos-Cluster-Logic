import requests
import json
import time
from typing import Dict, List
import sys
sys.path.append('.')
from app.services.cluster_engine import discover_neighbors_for_host, find_qualified_host_for_neighbor

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
1. Register Host Home
2. Register Neighbor Home
3. Discover Neighbors for Host Home
4. Test Road-Aware Adjacency (NEW)
5. Check if Neighbor Qualifies for Host Home
6. Exit

Enter your choice (1-6): """, end="")
        
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
        
    def discover_neighbors_cli(self):
        self.clear_screen()
        self.print_header()
        print("\U0001F50D DISCOVER NEIGHBORS FOR HOST HOME (REGISTERED ONLY)")
        print("=" * 50)
        print("Note: Only homes registered as hosts (in host_homes.csv) are considered as host homes.")
        address = input("Enter the full host home address (street, city, state): ").strip()
        if not address:
            print("❌ Address cannot be empty!")
            input("Press Enter to continue...")
            return
        print(f"\n🔍 Discovering qualified neighbors for: {address}\n")
        neighbors = discover_neighbors_for_host(address)
        print(f"\n✅ Found {len(neighbors)} qualified neighbors:")
        for i, n in enumerate(neighbors, 1):
            print(f"   {i}. {n}")
        input("\nPress Enter to continue...")
        
    def check_neighbor_qualification_cli(self):
        self.clear_screen()
        self.print_header()
        print("\U0001F50D CHECK IF NEIGHBOR QUALIFIES FOR REGISTERED HOST HOME")
        print("=" * 50)
        print("Note: Only homes registered as hosts (in host_homes.csv) are considered as host homes.")
        address = input("Enter the full neighbor address (street, city, state): ").strip()
        if not address:
            print("❌ Address cannot be empty!")
            input("Press Enter to continue...")
            return
        print(f"\n🔍 Checking qualification for: {address}\n")
        qualified_hosts = find_qualified_host_for_neighbor(address)
        if qualified_hosts:
            print(f"\n✅ This address qualifies for {len(qualified_hosts)} registered host home(s):")
            for i, h in enumerate(qualified_hosts, 1):
                print(f"   {i}. {h}")
        else:
            print("\n❌ This address does not qualify for any registered host home within 80 meters and road connectivity.")
        input("\nPress Enter to continue...")
        
    def register_host_home_cli(self):
        self.clear_screen()
        self.print_header()
        print("\U0001F3E0 REGISTER HOST HOME")
        print("=" * 50)
        address = input("Enter street address: ").strip()
        city = input("Enter city: ").strip()
        state = input("Enter state: ").strip()
        lat = input("Enter latitude (optional): ").strip()
        lon = input("Enter longitude (optional): ").strip()
        lat = float(lat) if lat else None
        lon = float(lon) if lon else None
        print("\n⏳ Registering host home...")
        resp = requests.post(f"{BASE_URL}/clusters/register_host_home_csv", json={
            "address": address,
            "city": city,
            "state": state,
            "latitude": lat,
            "longitude": lon
        })
        if resp.status_code == 200:
            result = resp.json()
            if result.get("success"):
                print(f"\n✅ Registered host home: {result.get('full_address')} ({result.get('latitude')}, {result.get('longitude')})")
            else:
                print(f"\n❌ Failed: {result.get('message')}")
        else:
            print(f"\n❌ API error: {resp.text}")
        input("\nPress Enter to continue...")

    def register_neighbor_home_cli(self):
        self.clear_screen()
        self.print_header()
        print("\U0001F465 REGISTER NEIGHBOR HOME")
        print("=" * 50)
        address = input("Enter street address: ").strip()
        city = input("Enter city: ").strip()
        state = input("Enter state: ").strip()
        lat = input("Enter latitude (optional): ").strip()
        lon = input("Enter longitude (optional): ").strip()
        lat = float(lat) if lat else None
        lon = float(lon) if lon else None
        print("\n⏳ Registering neighbor home...")
        resp = requests.post(f"{BASE_URL}/clusters/register_neighbor_home_csv", json={
            "address": address,
            "city": city,
            "state": state,
            "latitude": lat,
            "longitude": lon
        })
        if resp.status_code == 200:
            result = resp.json()
            if result.get("success"):
                print(f"\n✅ Registered neighbor home: {result.get('full_address')} ({result.get('latitude')}, {result.get('longitude')})")
            else:
                print(f"\n❌ Failed: {result.get('message')}")
        else:
            print(f"\n❌ API error: {resp.text}")
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
                    self.register_host_home_cli()
                elif choice == "2":
                    self.register_neighbor_home_cli()
                elif choice == "3":
                    self.discover_neighbors_cli()
                elif choice == "4":
                    self.test_road_aware_adjacency()
                elif choice == "5":
                    self.check_neighbor_qualification_cli()
                elif choice == "6":
                    print("\n👋 Thank you for using Mowthos Cluster Management!")
                    print("   Goodbye!")
                    break
                else:
                    print("\n❌ Invalid choice. Please enter 1-6.")
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