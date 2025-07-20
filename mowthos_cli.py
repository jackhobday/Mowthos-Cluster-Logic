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
3. Exit

Enter your choice (1-3): """, end="")
        
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
        
    def discover_neighbors_for_host(self, host_address: str) -> List[str]:
        """Discover qualified neighbors for a host home using our API."""
        qualified_neighbors = []
        
        # Geocode the host home
        host_lat, host_lng = self.geocode_address(host_address)
        if not host_lat or not host_lng:
            raise Exception("Could not geocode host address")
            
        # Generate potential nearby addresses
        potential_neighbors = self.generate_nearby_addresses(host_lat, host_lng, host_address)
        
        for neighbor_address in potential_neighbors:
            # Check same side of street first
            if not self.is_same_side_of_street(host_address, neighbor_address):
                continue
                
            # Geocode the neighbor
            neighbor_lat, neighbor_lng = self.geocode_address(neighbor_address)
            if not neighbor_lat or not neighbor_lng:
                continue
                
            # Check proximity (0.05 miles)
            distance = self.calculate_distance(host_lat, host_lng, neighbor_lat, neighbor_lng)
            if distance > 0.05:
                continue
                
            # Test adjacency using our API
            if self.test_adjacency(host_lat, host_lng, neighbor_lat, neighbor_lng):
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
                    print("\n👋 Thank you for using Mowthos Cluster Management!")
                    print("   Goodbye!")
                    break
                else:
                    print("\n❌ Invalid choice. Please enter 1, 2, or 3.")
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