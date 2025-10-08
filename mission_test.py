#!/usr/bin/env python3
"""Test simple waypoint mission"""

import logging
from simulation.gazebo_integration import GazeboSimulatorController, SimulatorConfig

logging.basicConfig(level=logging.INFO)

config = SimulatorConfig(connection_url="udp:127.0.0.1:14540")
sim = GazeboSimulatorController(config)

# Simple square pattern
waypoints = [
    {"lat": 47.397742, "lon": 8.545594, "alt": 50},
    {"lat": 47.398042, "lon": 8.545594, "alt": 50},
    {"lat": 47.398042, "lon": 8.546094, "alt": 50},
    {"lat": 47.397742, "lon": 8.546094, "alt": 50},
]

if sim.connect() and sim.wait_for_position():
    print("Uploading mission...")
    if sim.upload_mission(waypoints):
        print("Arming and taking off...")
        if sim.arm_and_takeoff(50):
            print("Starting mission...")
            sim.start_mission()
            sim.monitor_mission()
            print("Mission complete! Returning to launch...")
            sim.return_to_launch()
    
    sim.disconnect()