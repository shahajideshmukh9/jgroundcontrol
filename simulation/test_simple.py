#!/usr/bin/env python3
"""Simple mission test with detailed mode debugging"""
import logging, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gazebo_integration import GazeboSimulatorController, SimulatorConfig
from pymavlink import mavutil

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

print("\n" + "="*70)
print("  SIMPLE MISSION TEST")
print("="*70 + "\n")

sim = GazeboSimulatorController(SimulatorConfig())

# Connect
print("[1] Connecting...")
if not sim.connect():
    print("✗ Failed!"); exit(1)
print("✓ Connected\n")

# GPS
print("[2] GPS...")
if not sim.wait_for_position():
    print("✗ Failed!"); exit(1)
print("✓ GPS ready\n")

# Mission
print("[3] Upload mission...")
waypoints = [
    {"lat": 47.397742, "lon": 8.545594, "alt": 50},
    {"lat": 47.398042, "lon": 8.545794, "alt": 50},
    {"lat": 47.398342, "lon": 8.545994, "alt": 50},
]
if not sim.upload_mission(waypoints):
    print("✗ Failed!"); exit(1)
print("✓ Uploaded\n")

# Arm & Takeoff
print("[4] Arm & Takeoff (force)...")
if not sim.arm_and_takeoff(50, force_arm=True):
    print("✗ Failed!"); exit(1)
print("✓ Airborne\n")

# Check current mode
print("[5] Current mode check...")
msg = sim.mav_connection.recv_match(type='HEARTBEAT', blocking=True, timeout=2)
if msg:
    curr = msg.custom_mode
    main = (curr >> 16) & 0xFF
    sub = curr & 0xFFFF
    print(f"Current: custom_mode={curr}, main={main}, sub={sub}\n")

# Start mission - the critical part
print("[6] Starting mission...")
print("Setting mission item to 0...")
sim.mav_connection.mav.mission_set_current_send(
    sim.target_system,
    sim.target_component,
    0
)
time.sleep(1)

print("Switching to MISSION mode...")
if sim.set_mode('MISSION'):
    print("✓ Mission started!\n")
    
    # Verify
    msg = sim.mav_connection.recv_match(type='HEARTBEAT', blocking=True, timeout=2)
    if msg:
        curr = msg.custom_mode
        main = (curr >> 16) & 0xFF
        sub = curr & 0xFFFF
        print(f"New mode: custom_mode={curr}, main={main}, sub={sub}")
        if main == 4 and sub == 4:
            print("✓ Confirmed in AUTO.MISSION mode!\n")
    
    print("[7] Monitoring...")
    try:
        sim.monitor_mission()
    except KeyboardInterrupt:
        print("\nInterrupted\n")
    
    print("[8] RTL...")
    sim.return_to_launch()
else:
    print("✗ Mode change failed!\n")
    print("Manual command to try in PX4 console (Terminal 1):")
    print("  commander mode auto:mission\n")

sim.disconnect()
print("="*70)
print("  DONE")
print("="*70 + "\n")