#!/usr/bin/env python3
"""
test_force.py

Quick test with force arm - bypasses all pre-arm checks
This is the fastest way to test the simulation

⚠️  WARNING: Force arm bypasses safety checks!
⚠️  ONLY USE IN SIMULATION - NEVER ON REAL HARDWARE!

Usage:
    cd /home/digambar/shahaji/jgroundcontrol/simulation
    python3 test_force.py
"""

import logging
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gazebo_integration import GazeboSimulatorController, SimulatorConfig

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    print("\n" + "="*70)
    print("  ⚠️  FORCE ARM MODE - Bypassing pre-arm checks")
    print("  (Safe for simulation only!)")
    print("="*70 + "\n")
    
    # Configure connection
    config = SimulatorConfig(connection_url="udp:127.0.0.1:14540")
    sim = GazeboSimulatorController(config)
    
    # Step 1: Connect
    logger.info("[1/7] Connecting to PX4 SITL...")
    if not sim.connect():
        print("✗ Connection failed!")
        print("Make sure PX4 is running: make px4_sitl gazebo-classic")
        return 1
    print("✓ Connected to PX4\n")
    
    # Step 2: Wait for GPS
    logger.info("[2/7] Waiting for GPS lock...")
    if not sim.wait_for_position(timeout=30):
        print("✗ GPS timeout!")
        return 1
    print("✓ GPS locked\n")
    
    # Step 3: Define waypoints
    logger.info("[3/7] Defining mission waypoints...")
    waypoints = [
        {"lat": 47.397742, "lon": 8.545594, "alt": 50},
        {"lat": 47.398042, "lon": 8.545794, "alt": 50},
        {"lat": 47.398342, "lon": 8.545994, "alt": 50},
    ]
    print(f"✓ Mission: {len(waypoints)} waypoints\n")
    
    # Step 4: Upload mission
    logger.info("[4/7] Uploading mission to autopilot...")
    if not sim.upload_mission(waypoints):
        print("✗ Mission upload failed!")
        return 1
    print("✓ Mission uploaded\n")
    
    # Step 5: Force arm and takeoff
    logger.info("[5/7] Force arming and taking off...")
    print("⚠️  Using FORCE ARM to bypass pre-arm checks")
    
    if not sim.arm_and_takeoff(50, force_arm=True):
        print("✗ Even force arm failed!")
        print("Check PX4 console (Terminal 1) for specific errors")
        sim.disconnect()
        return 1
    print("✓ Armed and airborne!\n")
    
    # Step 6: Start mission
    logger.info("[6/7] Starting mission (AUTO mode)...")
    if not sim.start_mission():
        print("✗ Mission start failed!")
        sim.disconnect()
        return 1
    print("✓ Mission started\n")
    
    # Step 7: Monitor mission
    logger.info("[7/7] Monitoring mission progress...")
    sim.monitor_mission()
    print("✓ Mission complete!\n")
    
    # Return to launch
    logger.info("Returning to launch position...")
    sim.return_to_launch()
    print("✓ Landed safely\n")
    
    # Disconnect
    sim.disconnect()
    
    print("="*70)
    print("  ✅ TEST COMPLETED SUCCESSFULLY!")
    print("="*70 + "\n")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)