"""
gazebo_integration.py

Gazebo Simulator Integration using PyMAVLink
Connects mission planning system with PX4/ArduPilot SITL in Gazebo

Author: Your Project
License: MIT
Version: 2.0.0 (PyMAVLink)
"""

import time
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import math

from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink


class SimulatorType(Enum):
    """Supported simulator types"""
    PX4_GAZEBO = "px4_gazebo"
    ARDUPILOT_GAZEBO = "ardupilot_gazebo"


@dataclass
class SimulatorConfig:
    """Configuration for Gazebo simulator connection"""
    connection_url: str = "udp:127.0.0.1:14540"  # Default PX4 SITL
    vehicle_model: str = "iris"
    simulator_type: SimulatorType = SimulatorType.PX4_GAZEBO
    timeout_seconds: int = 60
    source_system: int = 255  # GCS system ID
    source_component: int = 0  # GCS component ID


class GazeboSimulatorController:
    """
    Controller for connecting mission planner to Gazebo simulator using PyMAVLink
    Provides low-level MAVLink control over SITL drone
    
    Usage:
        config = SimulatorConfig(connection_url="udp:127.0.0.1:14540")
        sim = GazeboSimulatorController(config)
        sim.connect()
        sim.wait_for_position()
        sim.upload_mission(waypoints)
        sim.arm_and_takeoff(50)
        sim.start_mission()
        sim.monitor_mission()
        sim.return_to_launch()
        sim.disconnect()
    """
    
    def __init__(self, config: SimulatorConfig):
        """
        Initialize simulator controller with PyMAVLink
        
        Args:
            config: SimulatorConfig object with connection parameters
        """
        self.config = config
        self.mav_connection = None
        self.logger = logging.getLogger(__name__)
        self._is_connected = False
        self._mission_active = False
        self.target_system = 1  # Target drone system ID
        self.target_component = 1  # Target autopilot component ID
        
        # Telemetry data cache
        self._position = None
        self._attitude = None
        self._velocity = None
        self._battery = None
        self._gps = None
        self._heartbeat = None
        self._mission_current = 0
        self._mission_count = 0
        
    def connect(self) -> bool:
        """
        Connect to Gazebo SITL simulator using PyMAVLink
        
        Returns:
            bool: True if connection successful
        """
        try:
            self.logger.info(f"Connecting to simulator at {self.config.connection_url}")
            
            # Create MAVLink connection
            self.mav_connection = mavutil.mavlink_connection(
                self.config.connection_url,
                source_system=self.config.source_system,
                source_component=self.config.source_component
            )
            
            # Wait for heartbeat to confirm connection
            self.logger.info("Waiting for heartbeat...")
            heartbeat = self.mav_connection.wait_heartbeat(timeout=self.config.timeout_seconds)
            
            if heartbeat:
                self.target_system = self.mav_connection.target_system
                self.target_component = self.mav_connection.target_component
                self._is_connected = True
                self.logger.info(f"Heartbeat received from system {self.target_system}")
                self.logger.info(f"Autopilot type: {heartbeat.autopilot}, Vehicle type: {heartbeat.type}")
                return True
            else:
                self.logger.error("No heartbeat received")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to simulator: {e}")
            self._is_connected = False
            return False
    
    def wait_for_position(self, timeout: int = 30) -> bool:
        """
        Wait for valid GPS position
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            bool: True if valid position obtained
        """
        self.logger.info("Waiting for GPS position...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            msg = self.mav_connection.recv_match(
                type='GLOBAL_POSITION_INT',
                blocking=True,
                timeout=1
            )
            
            if msg:
                self._position = msg
                self.logger.info(
                    f"GPS position received: "
                    f"Lat={msg.lat/1e7:.6f}, Lon={msg.lon/1e7:.6f}, Alt={msg.relative_alt/1000:.1f}m"
                )
                return True
        
        self.logger.error("Timeout waiting for GPS position")
        return False
    
    def upload_mission(self, waypoints: List[Dict[str, Any]]) -> bool:
        """
        Upload mission waypoints to drone using MAVLink mission protocol
        
        Args:
            waypoints: List of waypoint dictionaries
            
        Returns:
            bool: True if upload successful
        """
        if not self._is_connected:
            self.logger.error("Not connected to simulator")
            return False
        
        try:
            num_waypoints = len(waypoints)
            self.logger.info(f"Uploading mission with {num_waypoints} waypoints...")
            
            # Send mission count
            self.mav_connection.mav.mission_count_send(
                self.target_system,
                self.target_component,
                num_waypoints,
                mavutil.mavlink.MAV_MISSION_TYPE_MISSION
            )
            
            # Wait for mission request
            for i in range(num_waypoints):
                msg = self.mav_connection.recv_match(
                    type=['MISSION_REQUEST', 'MISSION_REQUEST_INT'],
                    blocking=True,
                    timeout=5
                )
                
                if not msg:
                    self.logger.error(f"Timeout waiting for mission request {i}")
                    return False
                
                if msg.seq != i:
                    self.logger.error(f"Expected request for item {i}, got {msg.seq}")
                    return False
                
                # Get waypoint data
                wp = waypoints[i]
                
                # Determine mission item command
                if i == 0:
                    # First item is typically takeoff or home
                    command = mavutil.mavlink.MAV_CMD_NAV_WAYPOINT
                else:
                    command = mavutil.mavlink.MAV_CMD_NAV_WAYPOINT
                
                # Send mission item
                self.mav_connection.mav.mission_item_int_send(
                    self.target_system,
                    self.target_component,
                    i,  # seq
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                    command,
                    0 if i > 0 else 1,  # current (1 for first item)
                    1,  # autocontinue
                    0,  # param1
                    0,  # param2
                    0,  # param3
                    0,  # param4
                    int(wp['lat'] * 1e7),  # x (latitude)
                    int(wp['lon'] * 1e7),  # y (longitude)
                    wp['alt'],  # z (altitude)
                    mavutil.mavlink.MAV_MISSION_TYPE_MISSION
                )
                
                self.logger.debug(f"Sent waypoint {i}/{num_waypoints}")
            
            # Wait for mission ACK
            ack = self.mav_connection.recv_match(
                type='MISSION_ACK',
                blocking=True,
                timeout=5
            )
            
            if ack and ack.type == mavutil.mavlink.MAV_MISSION_ACCEPTED:
                self.logger.info("✓ Mission upload successful")
                self._mission_count = num_waypoints
                return True
            else:
                self.logger.error(f"Mission upload failed: {ack.type if ack else 'timeout'}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to upload mission: {e}")
            return False
    
    def arm(self) -> bool:
        """
        Arm the drone
        
        Returns:
            bool: True if armed successfully
        """
        if not self._is_connected:
            self.logger.error("Not connected to simulator")
            return False
        
        try:
            self.logger.info("Arming drone...")
            
            # Send arm command
            self.mav_connection.mav.command_long_send(
                self.target_system,
                self.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,  # confirmation
                1,  # arm (0=disarm, 1=arm)
                0, 0, 0, 0, 0, 0
            )
            
            # Wait for command ACK
            ack = self.mav_connection.recv_match(
                type='COMMAND_ACK',
                blocking=True,
                timeout=5
            )
            
            if ack and ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
                self.logger.info("✓ Drone armed")
                return True
            else:
                self.logger.error(f"Arm failed: {ack.result if ack else 'timeout'}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to arm: {e}")
            return False
    
    def takeoff(self, altitude: float) -> bool:
        """
        Takeoff to specified altitude
        
        Args:
            altitude: Takeoff altitude in meters
            
        Returns:
            bool: True if takeoff command sent successfully
        """
        if not self._is_connected:
            self.logger.error("Not connected to simulator")
            return False
        
        try:
            self.logger.info(f"Taking off to {altitude}m...")
            
            # Get current position
            if not self._position:
                self.wait_for_position(timeout=5)
            
            if not self._position:
                self.logger.error("No position data available")
                return False
            
            # Send takeoff command
            self.mav_connection.mav.command_long_send(
                self.target_system,
                self.target_component,
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                0,  # confirmation
                0,  # param1
                0,  # param2
                0,  # param3
                0,  # param4 (yaw)
                self._position.lat / 1e7,  # latitude
                self._position.lon / 1e7,  # longitude
                altitude  # altitude
            )
            
            # Wait for command ACK
            ack = self.mav_connection.recv_match(
                type='COMMAND_ACK',
                blocking=True,
                timeout=5
            )
            
            if ack and ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
                self.logger.info("✓ Takeoff command accepted")
                return True
            else:
                self.logger.error(f"Takeoff failed: {ack.result if ack else 'timeout'}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to takeoff: {e}")
            return False
    
    def arm_and_takeoff(self, altitude: float = 10.0) -> bool:
        """
        Arm and takeoff to specified altitude
        
        Args:
            altitude: Takeoff altitude in meters
            
        Returns:
            bool: True if successful
        """
        # Arm the drone
        if not self.arm():
            return False
        
        time.sleep(1)  # Brief pause after arming
        
        # Takeoff
        if not self.takeoff(altitude):
            return False
        
        # Wait until drone reaches target altitude
        self.logger.info("Waiting for drone to reach target altitude...")
        target_reached = False
        timeout = 60
        start_time = time.time()
        
        while time.time() - start_time < timeout and not target_reached:
            msg = self.mav_connection.recv_match(
                type='GLOBAL_POSITION_INT',
                blocking=True,
                timeout=1
            )
            
            if msg:
                current_alt = msg.relative_alt / 1000.0
                if current_alt >= altitude * 0.95:
                    self.logger.info(f"✓ Reached target altitude: {current_alt:.1f}m")
                    target_reached = True
                else:
                    self.logger.debug(f"Current altitude: {current_alt:.1f}m")
        
        return target_reached
    
    def set_mode(self, mode: str) -> bool:
        """
        Set flight mode
        
        Args:
            mode: Flight mode (e.g., 'GUIDED', 'AUTO', 'RTL')
            
        Returns:
            bool: True if mode set successfully
        """
        if not self._is_connected:
            self.logger.error("Not connected to simulator")
            return False
        
        try:
            # Get mode ID
            if mode not in self.mav_connection.mode_mapping():
                self.logger.error(f"Unknown mode: {mode}")
                return False
            
            mode_id = self.mav_connection.mode_mapping()[mode]
            
            self.logger.info(f"Setting mode to {mode}...")
            
            # Send mode command
            self.mav_connection.mav.set_mode_send(
                self.target_system,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                mode_id
            )
            
            # Wait for mode change
            timeout = 5
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                msg = self.mav_connection.recv_match(
                    type='HEARTBEAT',
                    blocking=True,
                    timeout=1
                )
                
                if msg and msg.custom_mode == mode_id:
                    self.logger.info(f"✓ Mode changed to {mode}")
                    return True
            
            self.logger.error(f"Timeout waiting for mode change to {mode}")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to set mode: {e}")
            return False
    
    def start_mission(self) -> bool:
        """
        Start the uploaded mission (set to AUTO mode)
        
        Returns:
            bool: True if mission started
        """
        if not self._is_connected:
            self.logger.error("Not connected to simulator")
            return False
        
        try:
            self.logger.info("Starting mission...")
            
            # Set to AUTO mode to start mission
            if self.set_mode('AUTO'):
                self._mission_active = True
                self.logger.info("✓ Mission started")
                return True
            else:
                self.logger.error("Failed to set AUTO mode")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start mission: {e}")
            return False
    
    def monitor_mission(self) -> bool:
        """
        Monitor mission progress until completion
        
        Returns:
            bool: True if mission completed successfully
        """
        if not self._is_connected:
            self.logger.error("Not connected to simulator")
            return False
        
        try:
            self.logger.info("Monitoring mission progress...")
            
            while self._mission_active:
                msg = self.mav_connection.recv_match(
                    type='MISSION_CURRENT',
                    blocking=True,
                    timeout=1
                )
                
                if msg:
                    self._mission_current = msg.seq
                    progress = (self._mission_current / self._mission_count * 100) \
                              if self._mission_count > 0 else 0
                    
                    self.logger.info(
                        f"Mission progress: {self._mission_current}/{self._mission_count} "
                        f"({progress:.1f}%)"
                    )
                    
                    # Check if mission complete
                    if self._mission_current >= self._mission_count - 1:
                        self.logger.info("✓ Mission complete!")
                        self._mission_active = False
                        return True
                
                # Also check heartbeat for mode changes
                hb = self.mav_connection.recv_match(
                    type='HEARTBEAT',
                    blocking=False
                )
                if hb:
                    self._heartbeat = hb
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error monitoring mission: {e}")
            return False
    
    def get_telemetry(self) -> Dict[str, Any]:
        """
        Get current telemetry data
        
        Returns:
            Dict with telemetry data
        """
        if not self._is_connected:
            return {}
        
        telemetry_data = {}
        
        try:
            # Update telemetry cache
            self._update_telemetry()
            
            # Position
            if self._position:
                telemetry_data["position"] = {
                    "latitude": self._position.lat / 1e7,
                    "longitude": self._position.lon / 1e7,
                    "altitude": self._position.relative_alt / 1000.0,
                    "absolute_altitude": self._position.alt / 1000.0
                }
            
            # Velocity
            if self._position:
                telemetry_data["velocity"] = {
                    "north": self._position.vx / 100.0,
                    "east": self._position.vy / 100.0,
                    "down": self._position.vz / 100.0
                }
            
            # Attitude
            if self._attitude:
                telemetry_data["attitude"] = {
                    "roll": math.degrees(self._attitude.roll),
                    "pitch": math.degrees(self._attitude.pitch),
                    "yaw": math.degrees(self._attitude.yaw)
                }
            
            # Battery
            if self._battery:
                telemetry_data["battery"] = {
                    "voltage": self._battery.voltages[0] / 1000.0 if self._battery.voltages else 0,
                    "remaining": self._battery.battery_remaining
                }
            
            # GPS
            if self._gps:
                telemetry_data["gps"] = {
                    "num_satellites": self._gps.satellites_visible,
                    "fix_type": self._gps.fix_type
                }
            
            # Flight mode
            if self._heartbeat:
                telemetry_data["flight_mode"] = self._get_mode_name(self._heartbeat.custom_mode)
                
        except Exception as e:
            self.logger.error(f"Error getting telemetry: {e}")
        
        return telemetry_data
    
    def _update_telemetry(self):
        """Update telemetry data cache"""
        # Non-blocking receive to update cache
        while True:
            msg = self.mav_connection.recv_match(blocking=False)
            if not msg:
                break
            
            msg_type = msg.get_type()
            
            if msg_type == 'GLOBAL_POSITION_INT':
                self._position = msg
            elif msg_type == 'ATTITUDE':
                self._attitude = msg
            elif msg_type == 'BATTERY_STATUS':
                self._battery = msg
            elif msg_type == 'GPS_RAW_INT':
                self._gps = msg
            elif msg_type == 'HEARTBEAT':
                self._heartbeat = msg
    
    def _get_mode_name(self, mode_id: int) -> str:
        """Get mode name from mode ID"""
        mode_mapping = self.mav_connection.mode_mapping()
        for name, id in mode_mapping.items():
            if id == mode_id:
                return name
        return f"UNKNOWN({mode_id})"
    
    def return_to_launch(self) -> bool:
        """
        Return to launch position
        
        Returns:
            bool: True if RTL successful
        """
        if not self._is_connected:
            self.logger.error("Not connected to simulator")
            return False
        
        try:
            self.logger.info("Returning to launch...")
            
            # Set RTL mode
            if not self.set_mode('RTL'):
                return False
            
            # Wait for landing
            self.logger.info("Waiting for landing...")
            timeout = 120
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                msg = self.mav_connection.recv_match(
                    type='GLOBAL_POSITION_INT',
                    blocking=True,
                    timeout=1
                )
                
                if msg:
                    alt = msg.relative_alt / 1000.0
                    if alt < 1.0:
                        self.logger.info("✓ Drone has landed")
                        return True
                    
                    self.logger.debug(f"Descending... altitude: {alt:.1f}m")
            
            self.logger.error("Timeout waiting for landing")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to return to launch: {e}")
            return False
    
    def emergency_land(self) -> bool:
        """
        Emergency land at current position
        
        Returns:
            bool: True if land command sent successfully
        """
        if not self._is_connected:
            self.logger.error("Not connected to simulator")
            return False
        
        try:
            self.logger.info("Emergency landing...")
            
            # Send land command
            self.mav_connection.mav.command_long_send(
                self.target_system,
                self.target_component,
                mavutil.mavlink.MAV_CMD_NAV_LAND,
                0,  # confirmation
                0, 0, 0, 0, 0, 0, 0
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to land: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from simulator"""
        if self.mav_connection:
            self.mav_connection.close()
        self._is_connected = False
        self._mission_active = False
        self.logger.info("Disconnected from simulator")


# Example usage
def main():
    """Example usage of Gazebo simulator integration with PyMAVLink"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure simulator
    config = SimulatorConfig(
        connection_url="udp:127.0.0.1:14540",
        simulator_type=SimulatorType.PX4_GAZEBO
    )
    
    # Create controller
    sim = GazeboSimulatorController(config)
    
    # Connect
    if not sim.connect():
        print("Failed to connect")
        return
    
    # Wait for position
    if not sim.wait_for_position():
        print("Failed to get position")
        return
    
    # Example waypoints
    waypoints = [
        {"lat": 47.397742, "lon": 8.545594, "alt": 50},
        {"lat": 47.398042, "lon": 8.545794, "alt": 50},
        {"lat": 47.398342, "lon": 8.545994, "alt": 50},
        {"lat": 47.398642, "lon": 8.546194, "alt": 50},
    ]
    
    # Upload mission
    if not sim.upload_mission(waypoints):
        print("Failed to upload mission")
        return
    
    # Arm and takeoff
    if not sim.arm_and_takeoff(50):
        print("Failed to arm and takeoff")
        return
    
    # Start mission
    if not sim.start_mission():
        print("Failed to start mission")
        return
    
    # Monitor mission
    sim.monitor_mission()
    
    # Get telemetry
    telemetry = sim.get_telemetry()
    print(f"Final telemetry: {telemetry}")
    
    # Return to launch
    sim.return_to_launch()
    
    # Disconnect
    sim.disconnect()


if __name__ == "__main__":
    main()