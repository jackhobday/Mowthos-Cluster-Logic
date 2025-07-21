import requests
import json
import time
from typing import Dict, List

BASE_URL = "http://localhost:8000"

class MowthosCLI:
    def __init__(self):
        self.host_homes: Dict[str, List[str]] = {}  # host_address -> neighbor_addresses
        
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
1. Input Host Home Address
2. View Neighbor Addresses for each Host Home
3. Check if Address Qualifies for Existing Cluster
4. Test Road-Aware Adjacency (NEW)
5. Exit

Enter your choice (1-5): """, end="")
        
    def input_host_home(self):
        """Handle option 1: Input Host Home Address."""
        self.clear_screen()
        self.print_header()
        
        print("🏠 HOST HOME REGISTRATION")
        print("=" * 50)
        
        # Get host address from user
        host_address = input("Enter the host home address: ").strip()
        
        if not host_address:
            print("❌ Address cannot be empty!")
            input("Press Enter to continue...")
            return
            
        print(f"\n🔍 Processing host home: {host_address}")
        print("⏳ Discovering qualified neighbors...")
        
        try:
            # Discover neighbors using our logic
            qualified_neighbors = self.discover_neighbors_for_host(host_address)
            
            if qualified_neighbors:
                # Store the results
                self.host_homes[host_address] = qualified_neighbors
                
                print(f"\n✅ SUCCESS! Found {len(qualified_neighbors)} qualified neighbors:")
                for i, neighbor in enumerate(qualified_neighbors, 1):
                    print(f"   {i}. {neighbor}")
                    
                print(f"\n💾 Host home '{host_address}' has been registered with {len(qualified_neighbors)} neighbors.")
            else:
                print(f"\n⚠️  No qualified neighbors found for '{host_address}'.")
                print("   This host home will be stored but has no neighbors yet.")
                self.host_homes[host_address] = []
                
        except Exception as e:
            print(f"\n❌ Error processing host home: {str(e)}")
            
        input("\nPress Enter to continue...")
        
    def check_address_qualification(self):
        """Handle option 3: Check if Address Qualifies for Existing Cluster."""
        self.clear_screen()
        self.print_header()
        
        print("🔍 ADDRESS QUALIFICATION CHECK")
        print("=" * 50)
        
        if not self.host_homes:
            print("❌ No host homes have been registered yet.")
            print("   Please add some host homes first (Option 1).")
            input("\nPress Enter to continue...")
            return
        
        # Get address to check from user
        address_to_check = input("Enter the address to check: ").strip()
        
        if not address_to_check:
            print("❌ Address cannot be empty!")
            input("Press Enter to continue...")
            return
            
        print(f"\n🔍 Checking qualification for: {address_to_check}")
        print("⏳ Analyzing against existing host homes...")
        
        try:
            # Geocode the address to check
            check_lat, check_lng = self.geocode_address(address_to_check)
            if not check_lat or not check_lng:
                print("❌ Could not geocode the address to check.")
                input("Press Enter to continue...")
                return
                
            # Check against each host home
            qualifying_hosts = []
            
            for host_address, neighbors in self.host_homes.items():
                print(f"\n📋 Checking against host: {host_address}")
                
                # Geocode the host home
                host_lat, host_lng = self.geocode_address(host_address)
                if not host_lat or not host_lng:
                    print("   ⚠️  Could not geocode host address, skipping...")
                    continue
                
                # Check proximity (0.05 miles)
                distance = self.calculate_distance(host_lat, host_lng, check_lat, check_lng)
                if distance > 0.05:
                    print(f"   ❌ Too far away ({distance:.3f} miles)")
                    continue
                
                # Test adjacency using new API endpoint that includes side-of-street logic
                if self.test_adjacency_with_street(host_address, address_to_check):
                    print("   ✅ QUALIFIED!")
                    qualifying_hosts.append({
                        'host_address': host_address,
                        'distance': distance,
                        'neighbors': neighbors
                    })
                else:
                    print("   ❌ Not adjacent (different side of street or other issue)")
                
                # Rate limiting
                time.sleep(0.1)
            
            # Display results
            print(f"\n" + "=" * 50)
            print("📊 QUALIFICATION RESULTS")
            print("=" * 50)
            
            if qualifying_hosts:
                print(f"✅ ADDRESS QUALIFIES for {len(qualifying_hosts)} cluster(s)!")
                print("\nQualifying host homes:")
                
                for i, qualifier in enumerate(qualifying_hosts, 1):
                    print(f"\n🏠 {i}. {qualifier['host_address']}")
                    print(f"   📏 Distance: {qualifier['distance']:.3f} miles")
                    print(f"   👥 Current neighbors: {len(qualifier['neighbors'])}")
                    if qualifier['neighbors']:
                        print("   📍 Neighbors:")
                        for j, neighbor in enumerate(qualifier['neighbors'], 1):
                            print(f"      {j}. {neighbor}")
            else:
                print("❌ ADDRESS DOES NOT QUALIFY for any existing cluster.")
                print("\nPossible reasons:")
                print("   • Too far from host homes (> 0.05 miles)")
                print("   • Different side of street")
                print("   • Road barriers between properties")
                print("   • No host homes registered yet")
                
        except Exception as e:
            print(f"\n❌ Error checking qualification: {str(e)}")
            
        input("\nPress Enter to continue...")
        
    def discover_neighbors_for_host(self, host_address: str) -> List[str]:
        """Discover qualified neighbors for a given host address."""
        qualified_neighbors = []
        
        # Geocode the host address
        host_lat, host_lng = self.geocode_address(host_address)
        if host_lat is None or host_lng is None:
            print(f"❌ Could not geocode host address: {host_address}")
            return []
        
        # Generate potential nearby addresses
        nearby_addresses = self.generate_nearby_addresses(host_lat, host_lng, host_address)
        
        print(f"🔍 Testing {len(nearby_addresses)} potential neighbors...")
        
        for neighbor_address in nearby_addresses:
            # Geocode the neighbor address
            neighbor_lat, neighbor_lng = self.geocode_address(neighbor_address)
            if neighbor_lat is None or neighbor_lng is None:
                continue
                
            # Check proximity (0.05 miles)
            distance = self.calculate_distance(host_lat, host_lng, neighbor_lat, neighbor_lng)
            if distance > 0.05:
                continue
                
            # Test adjacency using new API endpoint that includes side-of-street logic
            if self.test_adjacency_with_street(host_address, neighbor_address):
                qualified_neighbors.append(neighbor_address)
                
            # Rate limiting
            time.sleep(0.1)
            
        return qualified_neighbors
        
    def geocode_address(self, address: str) -> tuple:
        """Geocode an address using our API."""
        resp = requests.post(f"{BASE_URL}/clusters/geocode", json={"address": address})
        if resp.status_code == 200:
            data = resp.json()
            return data["latitude"], data["longitude"]
        return None, None
        
    def generate_nearby_addresses(self, host_lat: float, host_lng: float, host_address: str) -> List[str]:
        """Generate potential nearby addresses based on the host address pattern."""
        nearby_addresses = []
        
        # Extract street info from host address
        parts = host_address.split()
        if len(parts) >= 4:
            house_num = int(parts[0])
            street_name = " ".join(parts[1:-2])
            street_type = parts[-2]
            direction = parts[-1]
            
            # Generate addresses on the same street within reasonable range
            for offset in range(-10, 11):
                if offset == 0:  # Skip the host home itself
                    continue
                    
                new_num = house_num + offset
                if new_num > 0:
                    new_address = f"{new_num} {street_name} {street_type} {direction}"
                    nearby_addresses.append(new_address)
        
        return nearby_addresses
        
    def is_same_side_of_street(self, host_address: str, neighbor_address: str) -> bool:
        """Check if two addresses are on the same side of the street using odd/even parity."""
        host_number = self.extract_house_number(host_address)
        neighbor_number = self.extract_house_number(neighbor_address)
        
        if host_number is None or neighbor_number is None:
            return False
        
        # Check if both numbers have the same parity (both odd or both even)
        host_parity = host_number % 2
        neighbor_parity = neighbor_number % 2
        
        return host_parity == neighbor_parity
        
    def extract_house_number(self, address: str) -> int:
        """Extract house number from address string."""
        parts = address.split()
        if parts and parts[0].isdigit():
            return int(parts[0])
        return None
        
    def calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points in miles."""
        from geopy.distance import geodesic
        return geodesic((lat1, lng1), (lat2, lng2)).miles
        
    def test_adjacency(self, host_lat: float, host_lng: float, neighbor_lat: float, neighbor_lng: float) -> bool:
        """Test if two addresses are adjacent using our API."""
        resp = requests.post(f"{BASE_URL}/clusters/test_adjacency", json={
            "lat1": host_lat,
            "lng1": host_lng,
            "lat2": neighbor_lat,
            "lng2": neighbor_lng
        })
        
        if resp.status_code == 200:
            data = resp.json()
            return data.get("adjacent", False)
        return False
        
    def test_adjacency_with_street(self, host_address: str, neighbor_address: str) -> bool:
        """Test if two addresses are adjacent including side-of-street logic using our API."""
        resp = requests.post(f"{BASE_URL}/clusters/test_adjacency_with_street", json={
            "address1": host_address,
            "address2": neighbor_address
        })
        
        if resp.status_code == 200:
            data = resp.json()
            return data.get("adjacent", False)
        return False
        
    def test_adjacency_with_road_detection(self, host_address: str, neighbor_address: str) -> dict:
        """Test if two addresses are adjacent with road-aware detection using our API."""
        resp = requests.post(f"{BASE_URL}/clusters/test_adjacency_with_road_detection", json={
            "address1": host_address,
            "address2": neighbor_address
        })
        
        if resp.status_code == 200:
            return resp.json()
        return {"adjacent": False, "message": "API error"}
        
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
        
    def view_neighbor_addresses(self):
        """Handle option 2: View Neighbor Addresses for each Host Home."""
        self.clear_screen()
        self.print_header()
        
        print("👥 NEIGHBOR ADDRESSES BY HOST HOME")
        print("=" * 50)
        
        if not self.host_homes:
            print("❌ No host homes have been registered yet.")
            print("   Please add some host homes first (Option 1).")
        else:
            for i, (host_address, neighbors) in enumerate(self.host_homes.items(), 1):
                print(f"\n🏠 HOST HOME #{i}: {host_address}")
                print("-" * 40)
                
                if neighbors:
                    print(f"✅ Found {len(neighbors)} qualified neighbors:")
                    for j, neighbor in enumerate(neighbors, 1):
                        print(f"   {j}. {neighbor}")
                else:
                    print("⚠️  No qualified neighbors found.")
                    
        input("\nPress Enter to continue...")
        
    def run(self):
        """Main application loop."""
        while True:
            try:
                self.clear_screen()
                self.print_header()
                self.print_menu()
                
                choice = input().strip()
                
                if choice == "1":
                    self.input_host_home()
                elif choice == "2":
                    self.view_neighbor_addresses()
                elif choice == "3":
                    self.check_address_qualification()
                elif choice == "4":
                    self.test_road_aware_adjacency()
                elif choice == "5":
                    print("\n👋 Thank you for using Mowthos Cluster Management!")
                    print("   Goodbye!")
                    break
                else:
                    print("\n❌ Invalid choice. Please enter 1, 2, 3, or 4.")
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