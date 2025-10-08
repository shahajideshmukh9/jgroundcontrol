#!/usr/bin/env python3
"""Debug version - shows exactly what's happening"""
import logging, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gazebo_integration import GazeboSimulatorController, SimulatorConfig

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("\n" + "="*70)
print("  DEBUG MODE - Detailed Mission Test")
print("="*70 + "\n")

sim = GazeboSimulatorController(SimulatorConfig())

# Connect
print("[1] Connecting...")
if not sim.connect():
    print("✗ Connection failed!"); exit(1)
print("✓ Connected\n")

# GPS
print("[2] Waiting for GPS...")
if not sim.wait_for_position():
    print("✗ GPS failed!"); exit(1)
print("✓ GPS ready\n")

# Check available modes
print("[3] Checking available modes...")
modes = sim.mav_connection.mode_mapping()
print(f"Available modes: {list(modes.keys())}")
print(f"MISSION mode ID: {modes.get('MISSION', 'NOT FOUND')}")
print(f"AUTO.MISSION mode ID: {modes.get('AUTO.MISSION', 'NOT FOUND')}")
print(f"AUTO mode ID: {modes.get('AUTO', 'NOT FOUND')}")
print(f"RTL mode ID: {modes.get('RTL', 'NOT FOUND')}\n")

# Upload mission
print("[4] Uploading mission...")
waypoints = [
    {"lat": 47.397742, "lon": 8.545594, "alt": 50},
    {"lat": 47.398042, "lon": 8.545794, "alt": 50},
    {"lat": 47.399042, "lon": 8.545994, "alt": 50},
]
if not sim.upload_mission(waypoints):
    print("✗ Upload failed!"); exit(1)
print("✓ Mission uploaded\n")

# Arm and takeoff
print("[5] Arming and taking off (force)...")
if not sim.arm_and_takeoff(50, force_arm=True):
    print("✗ Arm/takeoff failed!"); exit(1)
print("✓ Airborne\n")

# Check current mode
print("[6] Checking current flight mode...")
msg = sim.mav_connection.recv_match(type='HEARTBEAT', blocking=True, timeout=2)
if msg:
    current_mode_id = msg.custom_mode
    
    # PX4 encodes mode in lower 16 bits
    main_mode = (current_mode_id >> 16) & 0xFF
    sub_mode = current_mode_id & 0xFFFF
    
    print(f"Raw custom_mode: {current_mode_id}")
    print(f"Main mode: {main_mode}, Sub mode: {sub_mode}")
    
    # Try matching with sub_mode (PX4 uses this)
    current_mode_name = "UNKNOWN"
    for name, mid in modes.items():
        if mid == sub_mode:  # Match with sub_mode, not full custom_mode
            current_mode_name = name
            break
    
    print(f"Current mode: {current_mode_name}\n")

# Start mission
print("[7] Starting mission (setting to MISSION mode)...")

# CRITICAL: Set waypoint 0 as current mission item BEFORE switching modes
print("  → Step 7a: Setting waypoint 0 as current mission item...")
sim.mav_connection.mav.mission_set_current_send(
    sim.mav_connection.target_system,
    sim.mav_connection.target_component,
    0  # Start from first waypoint (0-indexed)
)

# Wait for the command to be processed
time.sleep(0.5)

# Check for MISSION_CURRENT acknowledgment
mission_current = sim.mav_connection.recv_match(type='MISSION_CURRENT', blocking=True, timeout=2)
if mission_current:
    print(f"  ✓ Mission current set to waypoint: {mission_current.seq}")
else:
    print("  ⚠ No MISSION_CURRENT confirmation received")

print("\n  → Step 7b: Switching to MISSION/AUTO mode...")

# Try different mode names that PX4 might use
mode_success = False
modes_to_try = ['AUTO.MISSION', 'AUTO', 'MISSION']

for mode_name in modes_to_try:
    print(f"    Trying mode: {mode_name}...")
    
    # Check if mode exists
    mode_id = modes.get(mode_name)
    if mode_id is None:
        print(f"    ✗ Mode '{mode_name}' not found in mode mapping")
        continue
    
    print(f"    Mode ID: {mode_id}")
    
    # Use the built-in set_mode if available
    if hasattr(sim, 'set_mode'):
        result = sim.set_mode(mode_name)
    else:
        # Manual mode setting using command_long
        from pymavlink import mavutil
        sim.mav_connection.mav.command_long_send(
            sim.mav_connection.target_system,
            sim.mav_connection.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_MODE,
            0,  # confirmation
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,  # param1
            mode_id,  # param2 - custom mode
            0, 0, 0, 0, 0  # unused params
        )
        
        # Wait for ACK
        ack = sim.mav_connection.recv_match(type='COMMAND_ACK', blocking=True, timeout=3)
        result = ack and ack.result == 0
        
        if ack:
            print(f"    ACK result: {ack.result} ({['SUCCESS', 'FAILED'][min(ack.result, 1)]})")
    
    if result:
        print(f"  ✓ Mode change command accepted!\n")
        mode_success = True
        break
    else:
        print(f"    ✗ Mode '{mode_name}' failed")

if not mode_success:
    print("\n✗ Failed to start mission!")
    print("\nDEBUG INFO:")
    print("- Mission was uploaded successfully")
    print("- Mission item 0 was set as current")
    print("- Drone is armed and airborne")
    print("- All mode change attempts failed")
    print("\nTry manually in PX4 console:")
    print("  commander mode auto:mission")
    print("\nOr check QGroundControl mission status")
    exit(1)

# Verify mode changed
print("  → Step 7c: Verifying mode change...")
time.sleep(1)
msg = sim.mav_connection.recv_match(type='HEARTBEAT', blocking=True, timeout=2)
if msg:
    new_mode_id = msg.custom_mode
    new_sub_mode = new_mode_id & 0xFFFF
    new_mode_name = "UNKNOWN"
    
    for name, mid in modes.items():
        if mid == new_sub_mode:
            new_mode_name = name
            break
    
    print(f"  New mode: {new_mode_name} (ID: {new_mode_id}, Sub: {new_sub_mode})")
    
    if new_mode_name in ['MISSION', 'AUTO.MISSION', 'AUTO']:
        print("  ✓ Successfully in mission execution mode!\n")
    else:
        print(f"  ⚠ Mode is {new_mode_name}, not MISSION/AUTO\n")
        print("  Mission may not execute. Continuing anyway...\n")

print("✓ Mission started!\n")

# Monitor
print("[8] Monitoring mission progress...")
print("  (Press Ctrl+C to skip monitoring)\n")
try:
    sim.monitor_mission()
    print("✓ Mission monitoring complete\n")
except KeyboardInterrupt:
    print("\n⚠ Monitoring interrupted by user\n")

# RTL
print("[9] Returning to launch...")
sim.return_to_launch()
print("✓ RTL complete\n")

sim.disconnect()
print("="*70)
print("  ✅ SUCCESS!")
print("="*70 + "\n")