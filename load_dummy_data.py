#!/usr/bin/env python3
# Quick Data Loader - Load dummy data from JSON
# File: load_dummy_data.py

"""
Load dummy data from JSON file or predefined data into the orchestrator
Usage: python load_dummy_data.py [json_file]
"""

import json
import sys
import requests
from typing import Dict, Any

# API Configuration
BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

# Predefined dummy data (if no JSON file provided)
PREDEFINED_DATA = {
    "vehicles": [
        {
            "id": "V001",
            "type": "multi-rotor",
            "location": {"lat": 37.7749, "lon": -122.4194, "alt": 0},
            "battery": 95.0
        },
        {
            "id": "V002",
            "type": "fixed-wing",
            "location": {"lat": 37.8044, "lon": -122.2712, "alt": 0},
            "battery": 88.0
        },
        {
            "id": "V003",
            "type": "vtol",
            "location": {"lat": 37.3382, "lon": -121.8863, "alt": 0},
            "battery": 100.0
        }
    ],
    "geofences": [
        {
            "name": "Airport Restricted Zone",
            "type": "keep-out",
            "polygon": [
                {"lat": 37.6200, "lon": -122.3800, "alt": 0},
                {"lat": 37.6250, "lon": -122.3800, "alt": 0},
                {"lat": 37.6250, "lon": -122.3700, "alt": 0},
                {"lat": 37.6200, "lon": -122.3700, "alt": 0}
            ],
            "priority": 10,
            "min_altitude": 0,
            "max_altitude": 10000
        },
        {
            "name": "Operational Boundary",
            "type": "keep-in",
            "polygon": [
                {"lat": 37.7000, "lon": -122.5000, "alt": 0},
                {"lat": 37.9000, "lon": -122.5000, "alt": 0},
                {"lat": 37.9000, "lon": -122.1000, "alt": 0},
                {"lat": 37.7000, "lon": -122.1000, "alt": 0}
            ],
            "priority": 5,
            "min_altitude": 0,
            "max_altitude": 500
        }
    ],
    "survey_missions": [
        {
            "name": "Agricultural Survey Alpha",
            "polygon": [
                {"lat": 37.7749, "lon": -122.4194, "alt": 0},
                {"lat": 37.7799, "lon": -122.4194, "alt": 0},
                {"lat": 37.7799, "lon": -122.4144, "alt": 0},
                {"lat": 37.7749, "lon": -122.4144, "alt": 0}
            ],
            "grid_spacing": 30,
            "altitude": 100,
            "overlap": 0.7
        }
    ],
    "corridor_missions": [
        {
            "name": "Pipeline Inspection",
            "start": {"lat": 37.8044, "lon": -122.2712, "alt": 0},
            "end": {"lat": 37.8244, "lon": -122.2512, "alt": 0},
            "width": 100,
            "altitude": 80,
            "segments": 3
        }
    ]
}

class DataLoader:
    """Load dummy data into orchestrator via API"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.stats = {
            'vehicles': {'success': 0, 'failed': 0},
            'geofences': {'success': 0, 'failed': 0},
            'missions': {'success': 0, 'failed': 0}
        }
    
    def check_server(self) -> bool:
        """Check if API server is running"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def load_vehicles(self, vehicles: list):
        """Load vehicles"""
        print(f"\n📡 Loading {len(vehicles)} vehicles...")
        
        for vehicle in vehicles:
            try:
                response = requests.post(
                    f"{self.base_url}/api/vehicles",
                    headers=HEADERS,
                    json=vehicle
                )
                
                if response.status_code == 200:
                    print(f"   ✓ {vehicle['id']}: {vehicle['type']}")
                    self.stats['vehicles']['success'] += 1
                else:
                    print(f"   ✗ {vehicle['id']}: {response.json().get('detail', 'Error')}")
                    self.stats['vehicles']['failed'] += 1
                    
            except Exception as e:
                print(f"   ✗ {vehicle['id']}: {str(e)}")
                self.stats['vehicles']['failed'] += 1
    
    def load_geofences(self, geofences: list):
        """Load geofences"""
        print(f"\n🛡️ Loading {len(geofences)} geofences...")
        
        for geofence in geofences:
            try:
                response = requests.post(
                    f"{self.base_url}/api/geofences",
                    headers=HEADERS,
                    json=geofence
                )
                
                if response.status_code == 200:
                    print(f"   ✓ {geofence['name']}: {geofence['type']}")
                    self.stats['geofences']['success'] += 1
                else:
                    print(f"   ✗ {geofence['name']}: {response.json().get('detail', 'Error')}")
                    self.stats['geofences']['failed'] += 1
                    
            except Exception as e:
                print(f"   ✗ {geofence['name']}: {str(e)}")
                self.stats['geofences']['failed'] += 1
    
    def load_survey_missions(self, missions: list):
        """Load survey missions"""
        if not missions:
            return
        
        print(f"\n🗺️ Loading {len(missions)} survey missions...")
        
        for mission in missions:
            try:
                response = requests.post(
                    f"{self.base_url}/api/missions/survey",
                    headers=HEADERS,
                    json=mission
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✓ {mission['name']}: {result.get('waypoint_count', 0)} waypoints")
                    self.stats['missions']['success'] += 1
                else:
                    print(f"   ✗ {mission['name']}: {response.json().get('detail', 'Error')}")
                    self.stats['missions']['failed'] += 1
                    
            except Exception as e:
                print(f"   ✗ {mission['name']}: {str(e)}")
                self.stats['missions']['failed'] += 1
    
    def load_corridor_missions(self, missions: list):
        """Load corridor missions"""
        if not missions:
            return
        
        print(f"\n🗺️ Loading {len(missions)} corridor missions...")
        
        for mission in missions:
            try:
                response = requests.post(
                    f"{self.base_url}/api/missions/corridor",
                    headers=HEADERS,
                    json=mission
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✓ {mission['name']}: {result.get('waypoint_count', 0)} waypoints")
                    self.stats['missions']['success'] += 1
                else:
                    print(f"   ✗ {mission['name']}: {response.json().get('detail', 'Error')}")
                    self.stats['missions']['failed'] += 1
                    
            except Exception as e:
                print(f"   ✗ {mission['name']}: {str(e)}")
                self.stats['missions']['failed'] += 1
    
    def load_structure_missions(self, missions: list):
        """Load structure scan missions"""
        if not missions:
            return
        
        print(f"\n🗺️ Loading {len(missions)} structure scan missions...")
        
        for mission in missions:
            try:
                response = requests.post(
                    f"{self.base_url}/api/missions/structure-scan",
                    headers=HEADERS,
                    json=mission
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✓ {mission['name']}: {result.get('waypoint_count', 0)} waypoints")
                    self.stats['missions']['success'] += 1
                else:
                    print(f"   ✗ {mission['name']}: {response.json().get('detail', 'Error')}")
                    self.stats['missions']['failed'] += 1
                    
            except Exception as e:
                print(f"   ✗ {mission['name']}: {str(e)}")
                self.stats['missions']['failed'] += 1
    
    def load_all(self, data: Dict[str, Any]):
        """Load all data from dictionary"""
        print("\n" + "="*70)
        print("LOADING DUMMY DATA INTO ORCHESTRATOR")
        print("="*70)
        
        # Load vehicles
        if 'vehicles' in data:
            self.load_vehicles(data['vehicles'])
        
        # Load geofences
        if 'geofences' in data:
            self.load_geofences(data['geofences'])
        
        # Load missions
        if 'survey_missions' in data:
            self.load_survey_missions(data['survey_missions'])
        
        if 'corridor_missions' in data:
            self.load_corridor_missions(data['corridor_missions'])
        
        if 'structure_missions' in data:
            self.load_structure_missions(data['structure_missions'])
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print loading summary"""
        print("\n" + "="*70)
        print("LOADING SUMMARY")
        print("="*70)
        
        total_success = sum(s['success'] for s in self.stats.values())
        total_failed = sum(s['failed'] for s in self.stats.values())
        
        print(f"\n✅ Vehicles: {self.stats['vehicles']['success']} loaded, "
              f"{self.stats['vehicles']['failed']} failed")
        print(f"✅ Geofences: {self.stats['geofences']['success']} loaded, "
              f"{self.stats['geofences']['failed']} failed")
        print(f"✅ Missions: {self.stats['missions']['success']} loaded, "
              f"{self.stats['missions']['failed']} failed")
        
        print(f"\n📊 Total: {total_success} successful, {total_failed} failed")
        print("="*70)

def main():
    """Main entry point"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║         Dummy Data Loader for Mission Control System        ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Check if server is running
    loader = DataLoader()
    
    print("🔍 Checking API server...")
    if not loader.check_server():
        print("❌ API server is not running!")
        print("\nPlease start the server first:")
        print("   uvicorn api_server:app --reload --port 8000")
        sys.exit(1)
    
    print("✅ API server is running\n")
    
    # Load data
    if len(sys.argv) > 1:
        # Load from JSON file
        json_file = sys.argv[1]
        print(f"📄 Loading data from: {json_file}")
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            loader.load_all(data)
        except FileNotFoundError:
            print(f"❌ File not found: {json_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            sys.exit(1)
    else:
        # Load predefined data
        print("📦 Loading predefined dummy data")
        loader.load_all(PREDEFINED_DATA)
    
    # Show next steps
    print("\n💡 Next steps:")
    print("   1. View dashboard: http://localhost:8000")
    print("   2. View API docs: http://localhost:8000/docs")
    print("   3. Check status: curl http://localhost:8000/api/orchestrator/status")
    print("   4. List vehicles: curl http://localhost:8000/api/vehicles")
    print("   5. Use test script: ./test_api.sh list-vehicles")
    print("\n👋 Data loading complete!")

if __name__ == "__main__":
    main()