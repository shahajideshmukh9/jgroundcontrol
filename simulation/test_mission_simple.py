#!/usr/bin/env python3
"""
Simple working test script for PX4 Gazebo mission simulation
Fixed imports for running from simulation directory

Usage:
    cd /home/digambar/shahaji/jgroundcontrol/simulation
    python3 test_mission.py
"""

import logging
import sys
import time
import os

# Add parent directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import with relative path (works when run from simulation/ directory)
from gazebo_integration import GazeboSimulatorController, SimulatorConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run a simple test mission"""
    
    print("\n" + "="*70)
    print("  PX4 GAZEBO SIMULATION TEST")
    print("="*70 + "\n")
    
    # Step 1: Configure connection
    logger.info("[1/8] Configuring simulator connection...")
    config = SimulatorConfig(
        connection_url="udp:127.0.0.1:14540",
    )
    sim = GazeboSimulatorController(config)
    print("✓ Configuration ready\n")
    
    # Step 2: Connect to simulator
    logger.info("[2/8] Connecting to PX4 SITL...")
    if not sim.connect():
        logger.error("✗ Failed to connect to simulator!")
        logger.error("Make sure PX4 SITL is running:")
        logger.error("  cd ~/PX4-Autopilot")
        logger.error("  make px4_sitl gazebo-classic")
        return 1
    print("✓ Connected to PX4\n")
    
    # Step 3: Wait for GPS position
    logger.info("[3/8] Waiting for GPS lock...")
    if not sim.wait_for_position(timeout=30):
        logger.error("✗ GPS position timeout!")
        return 1
    print("✓ GPS locked\n")
    
    # Step 4: Define mission waypoints
    logger.info("[4/8] Defining mission waypoints...")
    waypoints = [
        {"lat": 47.397742, "lon": 8.545594, "alt": 50},
        {"lat": 47.398042, "lon": 8.545794, "alt": 50},
        {"lat": 47.398342, "lon": 8.545994, "alt": 50},
        {"lat": 47.398642, "lon": 8.546194, "alt": 50},
    ]
    print(f"✓ Mission: {len(waypoints)} waypoints\n")
    
    # Step 5: Upload mission
    logger.info("[5/8] Uploading mission to autopilot...")
    if not sim.upload_mission(waypoints):
        logger.error("✗ Mission upload failed!")
        return 1
    print("✓ Mission uploaded\n")
    
    # Step 6: Arm and takeoff
    logger.info("[6/8] Arming and taking off to 50m...")
    logger.info("  (This will wait for pre-arm checks and retry if needed)")
    
    # The improved arm_and_takeoff now:
    # - Waits for system to be ready
    # - Retries up to 5 times if temporarily rejected
    # - Provides better error messages
    if not sim.arm_and_takeoff(altitude=50):
        logger.error("✗ Failed to arm and takeoff!")
        logger.error("\nTroubleshooting:")
        logger.error("  1. Wait longer (60s) after starting PX4")
        logger.error("  2. Try force arm: python3 test_force.py")
        logger.error("  3. Run diagnostic: python3 px4_arm_helper.py --check")
        sim.disconnect()
        return 1
    print("✓ Airborne!\n")
    
    # Step 7: Start mission
    logger.info("[7/8] Starting mission (AUTO mode)...")
    if not sim.start_mission():
        logger.error("✗ Failed to start mission!")
        return 1
    print("✓ Mission started\n")
    
    # Step 8: Monitor mission
    logger.info("[8/8] Monitoring mission progress...")
    sim.monitor_mission()
    print("✓ Mission complete!\n")
    
    # Return to launch
    logger.info("Returning to launch position...")
    sim.return_to_launch()
    print("✓ Landed safely\n")
    
    # Disconnect
    sim.disconnect()
    
    print("="*70)
    print("  ✓ TEST COMPLETED SUCCESSFULLY!")
    print("="*70 + "\n")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)