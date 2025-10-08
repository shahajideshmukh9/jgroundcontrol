#!/usr/bin/env python3
"""
Quick test with force arm - bypasses all pre-arm checks
Use this if test_mission_simple.py still has arming issues

⚠️  WARNING: Force arm bypasses safety checks!
⚠️  ONLY USE IN SIMULATION - NEVER ON REAL HARDWARE!

Usage:
    python3 test_force_arm.py
"""

import logging
from simulation.gazebo_integration import GazeboSimulatorController, SimulatorConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    print("\n⚠️  FORCE ARM MODE - Bypassing pre-arm checks\n")
    
    # Connect
    config = SimulatorConfig(connection_url="udp:127.0.0.1:14540")
    sim = GazeboSimulatorController(config)
    
    if not sim.connect():
        print("✗ Connection failed!")
        return 1
    print("✓ Connected")
    
    # Wait for GPS
    if not sim.wait_for_position(timeout=30):
        print("✗ GPS timeout!")
        return 1
    print("✓ GPS locked")
    
    # Upload mission
    waypoints = [
        {"lat": 47.397742, "lon": 8.545594, "alt": 50},
        {"lat": 47.398042, "lon": 8.545794, "alt": 50},
        {"lat": 47.398342, "lon": 8.545994, "alt": 50},
    ]
    
    if not sim.upload_mission(waypoints):
        print("✗ Mission upload failed!")
        return 1
    print("✓ Mission uploaded")
    
    # Arm with force (bypasses pre-arm checks)
    print("\n⚠️  Force arming (bypassing safety checks)...")
    if not sim.arm_and_takeoff(50, force_arm=True):
        print("✗ Even force arm failed!")
        return 1
    print("✓ Armed and airborne")
    
    # Start mission
    if not sim.start_mission():
        print("✗ Mission start failed!")
        return 1
    print("✓ Mission started")
    
    # Monitor
    sim.monitor_mission()
    print("✓ Mission complete")
    
    # RTL
    sim.return_to_launch()
    print("✓ Landed")
    
    sim.disconnect()
    print("\n✓ Test successful!\n")
    
    return 0

if __name__ == "__main__":
    exit(main())