# Complete Example: Orchestrator-Based Mission Control System
# File: example_usage.py

"""
This example demonstrates the complete workflow of the orchestrator-based system:
1. Initialize orchestrator
2. Register vehicles
3. Create geofences
4. Create missions
5. Execute mission workflows
6. Monitor in real-time
"""

import asyncio
import sys
from datetime import datetime

# Import from main orchestrator module
from main import (
    OrchestratorEngine,
    VehicleFactory,
    VehicleType,
    Location,
    Geofence,
    Event,
    EventPriority
)

async def main():
    """Main example execution"""
    
    print("="*70)
    print("Ground Controller Mission Control System")
    print("Complete Orchestrator-Based Example")
    print("="*70)
    print()
    
    # ========================================================================
    # STEP 1: Initialize Orchestrator
    # ========================================================================
    print("📡 Step 1: Initializing Orchestrator Engine...")
    orchestrator = OrchestratorEngine()
    orchestrator.start()
    
    # Subscribe to events for monitoring
    def event_logger(event: Event):
        print(f"  🔔 Event: {event.type} [{event.priority.name}]")
    
    orchestrator.event_router.subscribe('*', event_logger)
    
    print("✅ Orchestrator started")
    print(f"   Status: {orchestrator.status}")
    print()
    
    await asyncio.sleep(1)
    
    # ========================================================================
    # STEP 2: Register Vehicles
    # ========================================================================
    print("🚁 Step 2: Registering Vehicle Fleet...")
    
    # Register multi-rotor drone
    vehicle1 = VehicleFactory.create_vehicle(
        "DRONE-001",
        VehicleType.MULTI_ROTOR,
        Location(37.7749, -122.4194, 0)
    )
    vehicle1.battery = 95.0
    orchestrator.vehicle_manager.register_vehicle(vehicle1)
    print(f"✅ Registered: {vehicle1.id} ({vehicle1.type.value})")
    print(f"   Battery: {vehicle1.battery}%")
    print(f"   Max Range: {vehicle1.capabilities.max_range}m")
    print(f"   Sensors: {', '.join(vehicle1.capabilities.sensors)}")
    
    # Register fixed-wing drone
    vehicle2 = VehicleFactory.create_vehicle(
        "PLANE-001",
        VehicleType.FIXED_WING,
        Location(37.7849, -122.4094, 0)
    )
    vehicle2.battery = 100.0
    orchestrator.vehicle_manager.register_vehicle(vehicle2)
    print(f"✅ Registered: {vehicle2.id} ({vehicle2.type.value})")
    print(f"   Battery: {vehicle2.battery}%")
    print(f"   Max Range: {vehicle2.capabilities.max_range}m")
    print(f"   Endurance: {vehicle2.capabilities.endurance} min")
    
    # Register VTOL
    vehicle3 = VehicleFactory.create_vehicle(
        "VTOL-001",
        VehicleType.VTOL,
        Location(37.7649, -122.4294, 0)
    )
    vehicle3.battery = 88.0
    orchestrator.vehicle_manager.register_vehicle(vehicle3)
    print(f"✅ Registered: {vehicle3.id} ({vehicle3.type.value})")
    print(f"   Battery: {vehicle3.battery}%")
    print()
    
    await asyncio.sleep(1)
    
    # ========================================================================
    # STEP 3: Create Geofences
    # ========================================================================
    print("🛡️ Step 3: Setting up Geofences...")
    
    # Create keep-out zone (restricted airspace)
    restricted_zone = Geofence(
        id="GF-RESTRICTED-001",
        name="Airport Restricted Zone",
        type="keep-out",
        polygon=[
            Location(37.7800, -122.4200),
            Location(37.7850, -122.4200),
            Location(37.7850, -122.4150),
            Location(37.7800, -122.4150),
            Location(37.7800, -122.4200)
        ],
        priority=10,
        min_altitude=0,
        max_altitude=1000
    )
    orchestrator.geofencing.add_zone(restricted_zone)
    print(f"✅ Created: {restricted_zone.name}")
    print(f"   Type: {restricted_zone.type}")
    print(f"   Priority: {restricted_zone.priority}")
    
    # Create keep-in zone (operational boundary)
    operational_zone = Geofence(
        id="GF-KEEPIN-001",
        name="Operational Boundary",
        type="keep-in",
        polygon=[
            Location(37.7700, -122.4300),
            Location(37.7900, -122.4300),
            Location(37.7900, -122.4000),
            Location(37.7700, -122.4000),
            Location(37.7700, -122.4300)
        ],
        priority=5,
        min_altitude=0,
        max_altitude=500
    )
    orchestrator.geofencing.add_zone(operational_zone)
    print(f"✅ Created: {operational_zone.name}")
    print(f"   Type: {operational_zone.type}")
    
    # Create warning zone
    warning_zone = Geofence(
        id="GF-WARNING-001",
        name="High Traffic Area",
        type="warning",
        polygon=[
            Location(37.7750, -122.4250),
            Location(37.7780, -122.4250),
            Location(37.7780, -122.4180),
            Location(37.7750, -122.4180),
            Location(37.7750, -122.4250)
        ],
        priority=3,
        min_altitude=0,
        max_altitude=300
    )
    orchestrator.geofencing.add_zone(warning_zone)
    print(f"✅ Created: {warning_zone.name}")
    print(f"   Type: {warning_zone.type}")
    print()
    
    await asyncio.sleep(1)
    
    # ========================================================================
    # STEP 4: Create Missions
    # ========================================================================
    print("🗺️ Step 4: Planning Missions...")
    
    # Create survey mission
    print("\n📋 Creating Survey Mission...")
    survey_aoi = [
        Location(37.7749, -122.4194),
        Location(37.7779, -122.4194),
        Location(37.7779, -122.4164),
        Location(37.7749, -122.4164),
        Location(37.7749, -122.4194)
    ]
    
    survey_mission = orchestrator.mission_planner.create_survey_mission(
        aoi_polygon=survey_aoi,
        grid_spacing=30,
        altitude=80,
        overlap=0.7
    )
    survey_mission.name = "Agricultural Field Survey"
    orchestrator.missions[survey_mission.id] = survey_mission
    
    print(f"✅ Survey Mission Created: {survey_mission.id}")
    print(f"   Name: {survey_mission.name}")
    print(f"   Waypoints: {len(survey_mission.waypoints)}")
    print(f"   Coverage: {survey_mission.metadata['coverage_area']:.0f} m²")
    print(f"   Distance: {survey_mission.metadata['total_distance']:.0f} m")
    print(f"   Est. Time: {survey_mission.metadata['estimated_time']:.0f} sec")
    
    # Create corridor mission
    print("\n📋 Creating Corridor Mission...")
    corridor_mission = orchestrator.mission_planner.create_corridor_mission(
        start=Location(37.7749, -122.4194),
        end=Location(37.7819, -122.4124),
        width=100,
        altitude=60,
        segments=3
    )
    corridor_mission.name = "Pipeline Inspection Route"
    orchestrator.missions[corridor_mission.id] = corridor_mission
    
    print(f"✅ Corridor Mission Created: {corridor_mission.id}")
    print(f"   Name: {corridor_mission.name}")
    print(f"   Waypoints: {len(corridor_mission.waypoints)}")
    print(f"   Distance: {corridor_mission.metadata['distance']:.0f} m")
    
    # Create structure scan mission
    print("\n📋 Creating Structure Scan Mission...")
    structure_mission = orchestrator.mission_planner.create_structure_scan(
        center=Location(37.7769, -122.4174),
        radius=50,
        altitude_min=30,
        altitude_max=70,
        orbits=3,
        points_per_orbit=24
    )
    structure_mission.name = "Tower Inspection Scan"
    orchestrator.missions[structure_mission.id] = structure_mission
    
    print(f"✅ Structure Scan Created: {structure_mission.id}")
    print(f"   Name: {structure_mission.name}")
    print(f"   Waypoints: {len(structure_mission.waypoints)}")
    print(f"   Orbits: {structure_mission.metadata['orbits']}")
    print(f"   Radius: {structure_mission.metadata['radius']}m")
    print()
    
    await asyncio.sleep(1)
    
    # ========================================================================
    # STEP 5: Validate Missions
    # ========================================================================
    print("✔️ Step 5: Validating Missions...")
    
    print(f"\n🔍 Validating {survey_mission.name} for {vehicle1.id}...")
    validation1 = orchestrator.mission_planner.validate_mission(
        survey_mission, 
        vehicle1
    )
    
    if validation1['valid']:
        print("✅ Mission validation PASSED")
        print(f"   Required Battery: {validation1['required_battery']:.1f}%")
        print(f"   Available Battery: {vehicle1.battery}%")
        print(f"   Est. Flight Time: {validation1['estimated_time']:.0f} sec")
    else:
        print("❌ Mission validation FAILED")
        for issue in validation1['issues']:
            print(f"   ⚠️ {issue}")
    
    if validation1['warnings']:
        print("   Warnings:")
        for warning in validation1['warnings']:
            print(f"   ⚠️ {warning}")
    
    print()
    await asyncio.sleep(1)
    
    # ========================================================================
    # STEP 6: Execute Mission Workflow
    # ========================================================================
    print("🚀 Step 6: Executing Mission Workflow...")
    
    if validation1['valid']:
        print(f"\n⚙️ Starting workflow for {survey_mission.name}...")
        print("   This will execute the following steps:")
        print("   1. Validate mission")
        print("   2. Assign vehicle")
        print("   3. Check geofences")
        print("   4. Arm vehicle")
        print("   5. Execute mission")
        print("   6. Monitor progress")
        print()
        
        # Execute workflow
        result = await orchestrator.execute_mission_workflow(
            survey_mission.id,
            vehicle1.id
        )
        
        if result['success']:
            print("✅ Mission workflow COMPLETED successfully!")
            print(f"   Workflow ID: {result.get('workflow_id')}")
            print(f"   Mission Status: {survey_mission.status.value}")
            print(f"   Vehicle Status: {vehicle1.status.value}")
        else:
            print("❌ Mission workflow FAILED")
            print(f"   Error: {result.get('error')}")
            if result.get('rollback'):
                print("   🔄 Rollback performed")
    
    print()
    await asyncio.sleep(1)
    
    # ========================================================================
    # STEP 7: Monitor System Status
    # ========================================================================
    print("📊 Step 7: System Status Report...")
    
    status = orchestrator.get_status()
    
    print(f"\n{'='*70}")
    print("ORCHESTRATOR STATUS")
    print(f"{'='*70}")
    print(f"Status: {status['status'].upper()}")
    print(f"Uptime: {status['uptime']}")
    print(f"Events Processed: {status['events_processed']}")
    print(f"Active Workflows: {status['active_workflows']}")
    
    print(f"\nFLEET STATISTICS:")
    print(f"Total Vehicles: {status['fleet_stats']['total']}")
    print(f"Active Missions: {status['fleet_stats']['active_missions']}")
    print(f"Average Battery: {status['fleet_stats']['average_battery']:.1f}%")
    
    print(f"\nBY STATUS:")
    for status_type, count in status['fleet_stats']['by_status'].items():
        print(f"  {status_type}: {count}")
    
    print(f"\nBY TYPE:")
    for vehicle_type, count in status['fleet_stats']['by_type'].items():
        print(f"  {vehicle_type}: {count}")
    
    print(f"\nRESOURCES:")
    print(f"Missions: {status['missions']}")
    print(f"Geofences: {status['geofences']}")
    print(f"{'='*70}")
    print()
    
    # ========================================================================
    # STEP 8: Test Geofence Breach Detection
    # ========================================================================
    print("🛡️ Step 8: Testing Geofence Breach Detection...")
    
    # Move vehicle to restricted zone
    print(f"\n⚠️ Moving {vehicle2.id} into restricted zone...")
    breach_location = Location(37.7825, -122.4175, 100)  # Inside restricted zone
    orchestrator.vehicle_manager.update_location(vehicle2.id, breach_location)
    
    # Check for breaches
    breaches = orchestrator.geofencing.check_breach(breach_location, vehicle2.id)
    
    if breaches:
        print(f"🚨 BREACH DETECTED!")
        for breach in breaches:
            print(f"   Zone: {breach['zone_name']}")
            print(f"   Type: {breach['type']}")
            print(f"   Severity: {breach['severity']}")
            print(f"   Action: {breach['action']}")
    else:
        print("✅ No breaches detected")
    
    print()
    await asyncio.sleep(1)
    
    # ========================================================================
    # STEP 9: View Workflows
    # ========================================================================
    print("📝 Step 9: Workflow History...")
    
    workflows = list(orchestrator.workflow_coordinator.workflows.values())
    
    print(f"\nTotal Workflows: {len(workflows)}")
    for wf in workflows:
        print(f"\n  Workflow: {wf.id}")
        print(f"  Name: {wf.name}")
        print(f"  Status: {wf.status.value}")
        print(f"  Steps:")
        for step in wf.steps:
            status_icon = "✅" if step.status == "completed" else "⏳"
            print(f"    {status_icon} {step.name}: {step.status}")
    
    print()
    
    # ========================================================================
    # STEP 10: Shutdown
    # ========================================================================
    print("🛑 Step 10: Shutting down orchestrator...")
    orchestrator.stop()
    print("✅ Orchestrator stopped successfully")
    print()
    
    print("="*70)
    print("Example completed successfully! 🎉")
    print("="*70)

if __name__ == "__main__":
    print("\nStarting orchestrator-based mission control example...\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExample interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nExample finished.\n")