# Dummy Data Generator for Mission Control System
# File: generate_dummy_data.py

"""
Generate comprehensive dummy data for testing the orchestrator system
Includes: vehicles, missions, geofences, telemetry, and simulated events
"""

import random
import time
from datetime import datetime, timedelta
from typing import List

# Import from main orchestrator
from main import (
    OrchestratorEngine,
    VehicleFactory,
    VehicleType,
    VehicleStatus,
    Location,
    Geofence,
    Mission,
    MissionStatus
)

# ============================================================================
# DUMMY DATA CONFIGURATION
# ============================================================================

# San Francisco Bay Area coordinates for realistic locations
BASE_LOCATIONS = {
    'san_francisco': {'lat': 37.7749, 'lon': -122.4194},
    'oakland': {'lat': 37.8044, 'lon': -122.2712},
    'san_jose': {'lat': 37.3382, 'lon': -121.8863},
    'berkeley': {'lat': 37.8715, 'lon': -122.2730},
    'palo_alto': {'lat': 37.4419, 'lon': -122.1430},
    'half_moon_bay': {'lat': 37.4636, 'lon': -122.4286},
    'livermore': {'lat': 37.6819, 'lon': -121.7680},
    'fremont': {'lat': 37.5485, 'lon': -121.9886}
}

VEHICLE_NAMES = [
    'Eagle-1', 'Hawk-2', 'Falcon-3', 'Raven-4', 'Swift-5',
    'Phoenix-6', 'Condor-7', 'Osprey-8', 'Albatross-9', 'Vulture-10',
    'Sparrow-11', 'Robin-12', 'Heron-13', 'Crane-14', 'Stork-15'
]

MISSION_NAMES = [
    'Agricultural Survey Alpha',
    'Pipeline Inspection Route',
    'Power Line Corridor Scan',
    'Wind Farm Assessment',
    'Coastal Monitoring Mission',
    'Urban Infrastructure Check',
    'Forest Fire Detection',
    'Highway Traffic Survey',
    'Bridge Inspection Delta',
    'Solar Farm Analysis',
    'Port Security Patrol',
    'Mountain Range Mapping',
    'River Basin Survey',
    'Construction Site Monitor',
    'Emergency Response Recon'
]

GEOFENCE_ZONES = [
    {'name': 'Airport Restricted Zone', 'type': 'keep-out', 'priority': 10},
    {'name': 'Military Base No-Fly', 'type': 'keep-out', 'priority': 10},
    {'name': 'Operational Boundary', 'type': 'keep-in', 'priority': 5},
    {'name': 'High Traffic Warning', 'type': 'warning', 'priority': 3},
    {'name': 'Hospital Vicinity', 'type': 'warning', 'priority': 4},
    {'name': 'School Zone Caution', 'type': 'warning', 'priority': 3},
    {'name': 'Nature Reserve', 'type': 'keep-out', 'priority': 6},
    {'name': 'Downtown Core', 'type': 'warning', 'priority': 2}
]

# ============================================================================
# DUMMY DATA GENERATOR
# ============================================================================

class DummyDataGenerator:
    """Generate realistic dummy data for testing"""
    
    def __init__(self, orchestrator: OrchestratorEngine):
        self.orchestrator = orchestrator
        self.created_vehicles = []
        self.created_missions = []
        self.created_geofences = []
    
    def generate_all(self, 
                     num_vehicles: int = 10,
                     num_missions: int = 8,
                     num_geofences: int = 5):
        """Generate all dummy data"""
        print("\n" + "="*70)
        print("GENERATING DUMMY DATA FOR MISSION CONTROL SYSTEM")
        print("="*70)
        
        self.generate_vehicles(num_vehicles)
        self.generate_geofences(num_geofences)
        self.generate_missions(num_missions)
        
        print("\n" + "="*70)
        print("DUMMY DATA GENERATION COMPLETE!")
        print("="*70)
        print(f"\n✅ Created {len(self.created_vehicles)} vehicles")
        print(f"✅ Created {len(self.created_missions)} missions")
        print(f"✅ Created {len(self.created_geofences)} geofences")
        print("\nSystem is ready for testing!")
    
    def generate_vehicles(self, count: int = 10):
        """Generate dummy vehicles"""
        print(f"\n📡 Generating {count} vehicles...")
        
        vehicle_types = [VehicleType.MULTI_ROTOR, VehicleType.FIXED_WING, VehicleType.VTOL]
        locations = list(BASE_LOCATIONS.values())
        
        for i in range(count):
            vehicle_id = f"V{i+1:03d}"
            vehicle_type = random.choice(vehicle_types)
            base_location = random.choice(locations)
            
            # Add some randomness to location
            location = Location(
                lat=base_location['lat'] + random.uniform(-0.01, 0.01),
                lon=base_location['lon'] + random.uniform(-0.01, 0.01),
                alt=0
            )
            
            # Create vehicle
            vehicle = VehicleFactory.create_vehicle(vehicle_id, vehicle_type, location)
            
            # Randomize battery
            vehicle.battery = random.randint(60, 100)
            
            # Set random status
            statuses = [VehicleStatus.IDLE, VehicleStatus.IDLE, VehicleStatus.IDLE,  # More idle
                       VehicleStatus.ARMED, VehicleStatus.FLYING]
            vehicle.status = random.choice(statuses)
            
            # Register vehicle
            self.orchestrator.vehicle_manager.register_vehicle(vehicle)
            self.created_vehicles.append(vehicle)
            
            print(f"   ✓ {vehicle_id}: {vehicle_type.value} at ({location.lat:.4f}, {location.lon:.4f}) - {vehicle.battery}% battery")
        
        print(f"✅ {count} vehicles created")
    
    def generate_missions(self, count: int = 8):
        """Generate dummy missions"""
        print(f"\n🗺️ Generating {count} missions...")
        
        mission_types = ['survey', 'corridor', 'structure']
        locations = list(BASE_LOCATIONS.values())
        
        for i in range(count):
            mission_name = random.choice(MISSION_NAMES)
            mission_type = random.choice(mission_types)
            base_location = random.choice(locations)
            
            if mission_type == 'survey':
                mission = self._create_survey_mission(mission_name, base_location)
            elif mission_type == 'corridor':
                mission = self._create_corridor_mission(mission_name, base_location)
            else:
                mission = self._create_structure_mission(mission_name, base_location)
            
            # Randomize status
            statuses = [MissionStatus.PLANNED, MissionStatus.PLANNED, MissionStatus.PLANNED,
                       MissionStatus.EXECUTING, MissionStatus.COMPLETED]
            mission.status = random.choice(statuses)
            
            # If executing, assign a vehicle and set progress
            if mission.status == MissionStatus.EXECUTING and self.created_vehicles:
                available_vehicles = [v for v in self.created_vehicles if not v.mission_id]
                if available_vehicles:
                    vehicle = random.choice(available_vehicles)
                    mission.vehicle_id = vehicle.id
                    vehicle.mission_id = mission.id
                    vehicle.status = VehicleStatus.FLYING
                    mission.progress = random.randint(10, 90)
                    vehicle.mission_progress = mission.progress
            
            self.orchestrator.missions[mission.id] = mission
            self.created_missions.append(mission)
            
            print(f"   ✓ {mission.id}: {mission.name} ({mission.type.value}) - {len(mission.waypoints)} waypoints - {mission.status.value}")
        
        print(f"✅ {count} missions created")
    
    def _create_survey_mission(self, name: str, base_location: dict) -> Mission:
        """Create survey mission"""
        # Create AOI polygon around base location
        offset = 0.005  # ~500m
        polygon = [
            Location(base_location['lat'] - offset, base_location['lon'] - offset),
            Location(base_location['lat'] + offset, base_location['lon'] - offset),
            Location(base_location['lat'] + offset, base_location['lon'] + offset),
            Location(base_location['lat'] - offset, base_location['lon'] + offset),
            Location(base_location['lat'] - offset, base_location['lon'] - offset)
        ]
        
        mission = self.orchestrator.mission_planner.create_survey_mission(
            aoi_polygon=polygon,
            grid_spacing=random.randint(30, 60),
            altitude=random.randint(80, 120)
        )
        mission.name = name
        return mission
    
    def _create_corridor_mission(self, name: str, base_location: dict) -> Mission:
        """Create corridor mission"""
        start = Location(
            base_location['lat'],
            base_location['lon'],
            0
        )
        end = Location(
            base_location['lat'] + random.uniform(0.01, 0.02),
            base_location['lon'] + random.uniform(0.01, 0.02),
            0
        )
        
        mission = self.orchestrator.mission_planner.create_corridor_mission(
            start=start,
            end=end,
            width=random.randint(80, 120),
            altitude=random.randint(60, 100)
        )
        mission.name = name
        return mission
    
    def _create_structure_mission(self, name: str, base_location: dict) -> Mission:
        """Create structure scan mission"""
        center = Location(
            base_location['lat'],
            base_location['lon'],
            0
        )
        
        mission = self.orchestrator.mission_planner.create_structure_scan(
            center=center,
            radius=random.randint(40, 70),
            altitude_min=random.randint(20, 40),
            altitude_max=random.randint(60, 90),
            orbits=random.randint(2, 4)
        )
        mission.name = name
        return mission
    
    def generate_geofences(self, count: int = 5):
        """Generate dummy geofences"""
        print(f"\n🛡️ Generating {count} geofences...")
        
        locations = list(BASE_LOCATIONS.values())
        
        for i in range(min(count, len(GEOFENCE_ZONES))):
            zone_config = GEOFENCE_ZONES[i]
            base_location = random.choice(locations)
            
            # Create polygon around location
            size = random.uniform(0.003, 0.008)  # ~300-800m
            polygon = self._create_polygon_around(base_location, size)
            
            geofence = Geofence(
                id=f"GF-{i+1:03d}",
                name=zone_config['name'],
                type=zone_config['type'],
                polygon=polygon,
                priority=zone_config['priority'],
                min_altitude=0,
                max_altitude=random.randint(300, 500)
            )
            
            self.orchestrator.geofencing.add_zone(geofence)
            self.created_geofences.append(geofence)
            
            print(f"   ✓ {geofence.id}: {geofence.name} ({geofence.type}) - Priority {geofence.priority}")
        
        print(f"✅ {count} geofences created")
    
    def _create_polygon_around(self, center: dict, size: float) -> List[Location]:
        """Create rectangular polygon around center point"""
        return [
            Location(center['lat'] - size, center['lon'] - size),
            Location(center['lat'] + size, center['lon'] - size),
            Location(center['lat'] + size, center['lon'] + size),
            Location(center['lat'] - size, center['lon'] + size),
            Location(center['lat'] - size, center['lon'] - size)
        ]
    
    def simulate_realtime_updates(self, duration_seconds: int = 30):
        """Simulate real-time vehicle updates"""
        print(f"\n📡 Simulating real-time updates for {duration_seconds} seconds...")
        print("   Press Ctrl+C to stop early\n")
        
        start_time = time.time()
        update_count = 0
        
        try:
            while time.time() - start_time < duration_seconds:
                # Update flying vehicles
                for vehicle in self.created_vehicles:
                    if vehicle.status == VehicleStatus.FLYING:
                        # Update location slightly
                        new_location = Location(
                            lat=vehicle.location.lat + random.uniform(-0.0001, 0.0001),
                            lon=vehicle.location.lon + random.uniform(-0.0001, 0.0001),
                            alt=vehicle.location.alt + random.uniform(-5, 5)
                        )
                        self.orchestrator.vehicle_manager.update_location(
                            vehicle.id,
                            new_location
                        )
                        
                        # Update battery (drain)
                        vehicle.battery = max(20, vehicle.battery - random.uniform(0.1, 0.3))
                        
                        # Update mission progress
                        if vehicle.mission_id:
                            mission = self.orchestrator.missions.get(vehicle.mission_id)
                            if mission and mission.progress < 100:
                                mission.progress = min(100, mission.progress + random.uniform(0.5, 2))
                                vehicle.mission_progress = mission.progress
                        
                        update_count += 1
                        print(f"   🔄 {vehicle.id}: Battery {vehicle.battery:.1f}% | "
                              f"Location ({new_location.lat:.6f}, {new_location.lon:.6f}) | "
                              f"Progress {vehicle.mission_progress:.1f}%")
                
                time.sleep(2)  # Update every 2 seconds
        
        except KeyboardInterrupt:
            print("\n   Simulation stopped by user")
        
        print(f"\n✅ Completed {update_count} real-time updates")
    
    def generate_sample_alerts(self):
        """Generate sample geofence breach alerts"""
        print("\n🚨 Generating sample alerts...")
        
        if not self.created_vehicles or not self.created_geofences:
            print("   No vehicles or geofences to test")
            return
        
        vehicle = random.choice(self.created_vehicles)
        geofence = random.choice([g for g in self.created_geofences if g.type == 'keep-out'])
        
        if not geofence:
            print("   No keep-out zones available")
            return
        
        # Move vehicle into geofence
        breach_location = geofence.polygon[0]
        print(f"   Moving {vehicle.id} into {geofence.name}...")
        
        self.orchestrator.vehicle_manager.update_location(vehicle.id, breach_location)
        
        # Check for breaches
        breaches = self.orchestrator.geofencing.check_breach(breach_location, vehicle.id)
        
        if breaches:
            print(f"   ✓ Breach detected: {breaches[0]['zone_name']}")
            print(f"   ✓ Severity: {breaches[0]['severity']}")
            print(f"   ✓ Action: {breaches[0]['action']}")
        else:
            print("   No breach detected (vehicle may be outside zone)")
    
    def print_summary(self):
        """Print summary of generated data"""
        print("\n" + "="*70)
        print("DUMMY DATA SUMMARY")
        print("="*70)
        
        print(f"\n📊 VEHICLES ({len(self.created_vehicles)}):")
        by_type = {}
        by_status = {}
        for v in self.created_vehicles:
            by_type[v.type.value] = by_type.get(v.type.value, 0) + 1
            by_status[v.status.value] = by_status.get(v.status.value, 0) + 1
        
        print("   By Type:")
        for vtype, count in by_type.items():
            print(f"      {vtype}: {count}")
        
        print("   By Status:")
        for status, count in by_status.items():
            print(f"      {status}: {count}")
        
        avg_battery = sum(v.battery for v in self.created_vehicles) / len(self.created_vehicles)
        print(f"   Average Battery: {avg_battery:.1f}%")
        
        print(f"\n📋 MISSIONS ({len(self.created_missions)}):")
        by_type = {}
        by_status = {}
        for m in self.created_missions:
            by_type[m.type.value] = by_type.get(m.type.value, 0) + 1
            by_status[m.status.value] = by_status.get(m.status.value, 0) + 1
        
        print("   By Type:")
        for mtype, count in by_type.items():
            print(f"      {mtype}: {count}")
        
        print("   By Status:")
        for status, count in by_status.items():
            print(f"      {status}: {count}")
        
        print(f"\n🛡️ GEOFENCES ({len(self.created_geofences)}):")
        by_type = {}
        for g in self.created_geofences:
            by_type[g.type] = by_type.get(g.type, 0) + 1
        
        for gtype, count in by_type.items():
            print(f"      {gtype}: {count}")
        
        print("\n" + "="*70)

# ============================================================================
# QUICK START PRESETS
# ============================================================================

class QuickStartPresets:
    """Predefined scenarios for quick testing"""
    
    @staticmethod
    def small_demo(orchestrator):
        """Small demo: 3 vehicles, 2 missions, 2 geofences"""
        gen = DummyDataGenerator(orchestrator)
        gen.generate_all(num_vehicles=3, num_missions=2, num_geofences=2)
        return gen
    
    @staticmethod
    def medium_fleet(orchestrator):
        """Medium fleet: 10 vehicles, 8 missions, 5 geofences"""
        gen = DummyDataGenerator(orchestrator)
        gen.generate_all(num_vehicles=10, num_missions=8, num_geofences=5)
        return gen
    
    @staticmethod
    def large_operation(orchestrator):
        """Large operation: 20 vehicles, 15 missions, 8 geofences"""
        gen = DummyDataGenerator(orchestrator)
        gen.generate_all(num_vehicles=20, num_missions=15, num_geofences=8)
        return gen
    
    @staticmethod
    def stress_test(orchestrator):
        """Stress test: 50 vehicles, 30 missions, 10 geofences"""
        gen = DummyDataGenerator(orchestrator)
        gen.generate_all(num_vehicles=50, num_missions=30, num_geofences=10)
        return gen

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import sys
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║         Dummy Data Generator for Mission Control            ║
    ║              Orchestrator Test Data Creation                 ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize orchestrator
    print("🚀 Initializing Orchestrator Engine...")
    orchestrator = OrchestratorEngine()
    orchestrator.start()
    
    # Choose preset or custom
    print("\n📋 Choose a preset:")
    print("   1. Small Demo (3 vehicles, 2 missions, 2 geofences)")
    print("   2. Medium Fleet (10 vehicles, 8 missions, 5 geofences)")
    print("   3. Large Operation (20 vehicles, 15 missions, 8 geofences)")
    print("   4. Stress Test (50 vehicles, 30 missions, 10 geofences)")
    print("   5. Custom")
    
    choice = input("\nEnter choice (1-5) [default: 2]: ").strip() or "2"
    
    if choice == "1":
        gen = QuickStartPresets.small_demo(orchestrator)
    elif choice == "2":
        gen = QuickStartPresets.medium_fleet(orchestrator)
    elif choice == "3":
        gen = QuickStartPresets.large_operation(orchestrator)
    elif choice == "4":
        gen = QuickStartPresets.stress_test(orchestrator)
    elif choice == "5":
        print("\n📝 Custom Configuration:")
        num_vehicles = int(input("   Number of vehicles: ") or "10")
        num_missions = int(input("   Number of missions: ") or "8")
        num_geofences = int(input("   Number of geofences: ") or "5")
        
        gen = DummyDataGenerator(orchestrator)
        gen.generate_all(num_vehicles, num_missions, num_geofences)
    else:
        print("Invalid choice, using medium fleet")
        gen = QuickStartPresets.medium_fleet(orchestrator)
    
    # Print summary
    gen.print_summary()
    
    # Ask if user wants real-time simulation
    print("\n🔄 Would you like to simulate real-time updates?")
    simulate = input("   (y/n) [default: n]: ").strip().lower()
    
    if simulate == 'y':
        duration = int(input("   Duration in seconds [default: 30]: ") or "30")
        gen.simulate_realtime_updates(duration)
    
    # Ask if user wants to generate sample alerts
    print("\n🚨 Generate sample geofence breach alerts?")
    alerts = input("   (y/n) [default: n]: ").strip().lower()
    
    if alerts == 'y':
        gen.generate_sample_alerts()
    
    # Show system status
    print("\n📊 Final System Status:")
    status = orchestrator.get_status()
    print(f"   Orchestrator: {status['status']}")
    print(f"   Vehicles: {status['vehicles']}")
    print(f"   Missions: {status['missions']}")
    print(f"   Geofences: {status['geofences']}")
    print(f"   Events Processed: {status['events_processed']}")
    
    print("\n✅ System is ready for testing!")
    print("\n💡 Next steps:")
    print("   1. Start API server: uvicorn api_server:app --reload")
    print("   2. Access dashboard: http://localhost:8000")
    print("   3. View API docs: http://localhost:8000/docs")
    print("   4. Use CLI: python main.py status")
    print("\n👋 Happy testing!")