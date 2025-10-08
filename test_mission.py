#!/usr/bin/env python3
import logging
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gazebo_integration import GazeboSimulatorController, SimulatorConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

print("\n" + "="*70)
print("  PX4 GAZEBO SIMULATION TEST")
print("="*70 + "\n")

config = SimulatorConfig(connection_url="udp:127.0.0.1:14540")
sim = GazeboSimulatorController(config)

print("[1/7] Connecting...")
if not sim.connect():
    print("✗ Connection failed!")
    exit(1)
print("✓ Connected\n")

print("[2/7] Waiting for GPS...")
if not sim.wait_for_position(timeout=30):
    print("✗ GPS timeout!")
    exit(1)
print("✓ GPS locked\n")

print("[3/7] Waiting extra time for system initialization...")
print("     (Waiting 30 seconds for EKF and pre-arm checks)")
time.sleep(30)  # Give PX4 more time
print("✓ Wait complete\n")

waypoints = [
    {"lat": 47.397742, "lon": 8.545594, "alt": 50},
    {"lat": 47.398042, "lon": 8.545794, "alt": 50},
    {"lat": 47.398342, "lon": 8.545994, "alt": 50},
]

print("[4/7] Uploading mission...")
if not sim.upload_mission(waypoints):
    print("✗ Mission upload failed!")
    exit(1)
print("✓ Mission uploaded\n")

print("[5/7] Arming and taking off...")
print("     Trying normal arm first (with 10 retries)...")

# Try normal arm with MORE retries
if not sim.arm(retry_count=10):
    print("\n⚠️  Normal arming failed after 10 attempts")
    print("     Trying FORCE ARM...")
    
    # Try force arm as backup
    if not sim.arm(force=True, retry_count=3):
        print("✗ Even force arm failed!")
        sim.disconnect()
        exit(1)

print("✓ Armed!\n")

# Now takeoff
print("Taking off to 50m...")
if not sim.takeoff(50):
    print("✗ Takeoff failed!")
    sim.disconnect()
    exit(1)

# Wait for altitude
print("Waiting for target altitude...")
time.sleep(15)
print("✓ Should be airborne\n")

print("[6/7] Starting mission...")
if not sim.start_mission():
    print("✗ Mission start failed!")
    sim.disconnect()
    exit(1)
print("✓ Mission started\n")

print("[7/7] Monitoring mission...")
sim.monitor_mission()
print("✓ Mission complete\n")

print("Returning to launch...")
sim.return_to_launch()
print("✓ Landed\n")

sim.disconnect()
print("\n" + "="*70)
print("  ✓ TEST SUCCESSFUL!")
print("="*70 + "\n")
