#!/usr/bin/env python3
"""Test basic MAVLink connection to simulator"""

import logging
from simulation.gazebo_integration import GazeboSimulatorController, SimulatorConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configure for PX4
config = SimulatorConfig(
    connection_url="udp:127.0.0.1:14540"
)

# Create controller
sim = GazeboSimulatorController(config)

# Test connection
print("Testing connection to simulator...")
if sim.connect():
    print("✓ Connected successfully!")
    
    # Wait for position
    if sim.wait_for_position():
        print("✓ GPS position acquired!")
        
        # Get telemetry
        telemetry = sim.get_telemetry()
        print(f"\nTelemetry:")
        print(f"  Position: {telemetry.get('position', {})}")
        print(f"  Battery: {telemetry.get('battery', {})}")
        print(f"  Flight Mode: {telemetry.get('flight_mode', 'UNKNOWN')}")
    
    sim.disconnect()
else:
    print("✗ Connection failed!")