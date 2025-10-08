"""
gazebo_integration.py

Gazebo Simulator Integration using PyMAVLink
Connects mission planning system with PX4/ArduPilot SITL in Gazebo

Author: Your Project
License: MIT
Version: 2.1.0 (PyMAVLink - Fixed PX4 Mode Switching)

Usage:
    from gazebo_integration import GazeboSimulatorController, SimulatorConfig
    
    config = SimulatorConfig(connection_url="udp:127.0.0.1:14540")
    sim = GazeboSimulatorController(config)
    sim.connect()
"""

import time
import logging
import math
import threading
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from pymavlink import mavutil


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
    """
    
    def __init__(self, config: SimulatorConfig):
        """Initialize simulator controller with PyMAVLink"""
        self.config = config
        self.mav_connection = None
        self.logger = logging.getLogger(__name__)
        self._is_connected = False
        self._mission_active = False
        self.target_system = 1
        self.target_component = 1
        
        # Telemetry cache
        self._position = None
        self._attitude = None
        self._velocity = None
        self._battery = None
        self._gps = None
        self._heartbeat = None
        self._mission_current = 0
        self._mission_count = 0
        
    def connect(self) -> bool:
        """Connect to Gazebo SITL simulator"""
        try:
            self.logger.info(f"Connecting to simulator at {self.config.connection_url}")
            
            self.mav_connection = mavutil.mavlink_connection(
                self.config.connection_url,
                source_system=self.config.source_system,
                source_component=self.config.source_component
            )
            
            self.logger.info("Waiting for heartbeat...")
            heartbeat = self.mav_connection.wait_heartbeat(timeout=self.config.timeout_seconds)
            
            if heartbeat:
                self.target_system = self.mav_connection.target_system
                self.target_component = self.mav_connection.target_component
                self._is_connected = True
                self.logger.info(f"✓ Heartbeat received from system {self.target_system}")
                self.logger.info(f"  Autopilot: {heartbeat.autopilot}, Vehicle: {heartbeat.type}")
                
                # Start sending GCS heartbeats to satisfy pre-arm checks
                self._start_gcs_heartbeat()
                
                return True
            else:
                self.logger.error("No heartbeat received")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            self._is_connected = False
            return False
    
    def _start_gcs_heartbeat(self):
        """Start sending GCS heartbeats to satisfy pre-arm checks"""
        import threading
        
        def send_heartbeat():
            while self._is_connected:
                try:
                    self.mav_connection.mav.heartbeat_send(
                        mavutil.mavlink.MAV_TYPE_GCS,
                        mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                        0, 0, 0
                    )
                except Exception as e:
                    self.logger.debug(f"Heartbeat send error: {e}")
                time.sleep(1)  # Send every 1 second
        
        heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
        heartbeat_thread.start()
        self.logger.info("✓ Started sending GCS heartbeats")
    
    def wait_for_position(self, timeout: int = 30) -> bool:
        """Wait for valid GPS position"""
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
                    f"✓ GPS position: Lat={msg.lat/1e7:.6f}, "
                    f"Lon={msg.lon/1e7:.6f}, Alt={msg.relative_alt/1000:.1f}m"
                )
                return True
        
        self.logger.error("Timeout waiting for GPS position")
        return False
    
    def wait_until_ready_to_arm(self, timeout: int = 60) -> bool:
        """Wait until drone is ready to arm (all pre-arm checks pass)"""
        self.logger.info("Waiting for drone to be ready to arm...")
        start_time = time.time()
        
        health_ok = False
        home_position_ok = False
        global_position_ok = False
        
        while time.time() - start_time < timeout:
            # Check SYS_STATUS for health
            sys_status = self.mav_connection.recv_match(
                type='SYS_STATUS',
                blocking=False
            )
            
            # Check HEARTBEAT
            heartbeat = self.mav_connection.recv_match(
                type='HEARTBEAT',
                blocking=False
            )
            
            # Check GPS
            gps = self.mav_connection.recv_match(
                type='GPS_RAW_INT',
                blocking=False
            )
            
            # Check HOME_POSITION
            home = self.mav_connection.recv_match(
                type='HOME_POSITION',
                blocking=False
            )
            
            # Check GLOBAL_POSITION_INT
            pos = self.mav_connection.recv_match(
                type='GLOBAL_POSITION_INT',
                blocking=False
            )
            
            # Check EKF status
            ekf = self.mav_connection.recv_match(
                type='EKF_STATUS_REPORT',
                blocking=False
            )
            
            # Update flags
            if sys_status:
                health_ok = True
            
            if home:
                home_position_ok = True
                self.logger.info("✓ Home position set")
            
            if pos and gps:
                if gps.fix_type >= 3:  # 3D fix
                    global_position_ok = True
                    self.logger.info(f"✓ GPS 3D fix ({gps.satellites_visible} satellites)")
            
            # Check if all conditions met
            if health_ok and home_position_ok and global_position_ok:
                self.logger.info("✓ All pre-arm checks passed")
                return True
            
            time.sleep(0.5)
        
        # Log what's missing
        if not health_ok:
            self.logger.error("✗ System health not OK")
        if not home_position_ok:
            self.logger.error("✗ Home position not set")
        if not global_position_ok:
            self.logger.error("✗ GPS position not valid")
        
        self.logger.error("Timeout waiting for pre-arm checks")
        return False
    
    def upload_mission(self, waypoints: List[Dict[str, Any]]) -> bool:
        """Upload mission waypoints using MAVLink protocol"""
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
            
            # Upload each waypoint
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
                
                wp = waypoints[i]
                command = mavutil.mavlink.MAV_CMD_NAV_WAYPOINT
                
                self.mav_connection.mav.mission_item_int_send(
                    self.target_system,
                    self.target_component,
                    i,
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                    command,
                    0 if i > 0 else 1,
                    1,
                    0, 0, 0, 0,
                    int(wp['lat'] * 1e7),
                    int(wp['lon'] * 1e7),
                    wp['alt'],
                    mavutil.mavlink.MAV_MISSION_TYPE_MISSION
                )
            
            # Wait for ACK
            ack = self.mav_connection.recv_match(
                type='MISSION_ACK',
                blocking=True,
                timeout=5
            )
            
            if ack and ack.type == mavutil.mavlink.MAV_MISSION_ACCEPTED:
                self.logger.info("✓ Mission uploaded successfully")
                self._mission_count = num_waypoints
                return True
            else:
                self.logger.error(f"Mission upload failed: {ack.type if ack else 'timeout'}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to upload mission: {e}")
            return False
    
    def arm(self, force: bool = False, retry_count: int = 3) -> bool:
        """Arm the drone with retry logic
        
        Args:
            force: If True, force arm (skip pre-arm checks) - use with caution!
            retry_count: Number of times to retry if temporarily rejected
        """
        if not self._is_connected:
            return False
        
        try:
            self.logger.info("Arming drone..." + (" (forced)" if force else ""))
            
            # Force arm parameter: 0 = normal, 21196 = force
            force_param = 21196 if force else 0
            
            for attempt in range(retry_count):
                if attempt > 0:
                    self.logger.info(f"Retry attempt {attempt + 1}/{retry_count}...")
                    time.sleep(2)  # Wait before retry
                
                self.mav_connection.mav.command_long_send(
                    self.target_system,
                    self.target_component,
                    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                    0,
                    1,  # arm
                    force_param,  # force arm
                    0, 0, 0, 0, 0
                )
                
                ack = self.mav_connection.recv_match(
                    type='COMMAND_ACK',
                    blocking=True,
                    timeout=5
                )
                
                if ack:
                    if ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
                        self.logger.info("✓ Drone armed")
                        return True
                    elif ack.result == mavutil.mavlink.MAV_RESULT_TEMPORARILY_REJECTED:
                        self.logger.warning(f"Arming temporarily rejected (attempt {attempt + 1}/{retry_count})")
                        if attempt < retry_count - 1:
                            self.logger.info("  Waiting for system to be ready...")
                            continue
                    elif ack.result == mavutil.mavlink.MAV_RESULT_DENIED:
                        self.logger.error("Arming denied - pre-arm checks failed!")
                        self.logger.error("  Run: python3 px4_arm_helper.py --check")
                        self.logger.error("  Or use: force=True (simulation only!)")
                        return False
                    else:
                        self.logger.error(f"Arming failed with result code: {ack.result}")
                        return False
                else:
                    self.logger.error("No response from autopilot")
                    return False
            
            self.logger.error(f"Arming failed after {retry_count} attempts")
            return False
                
        except Exception as e:
            self.logger.error(f"Failed to arm: {e}")
            return False
    
    def takeoff(self, altitude: float) -> bool:
        """Takeoff to specified altitude"""
        if not self._is_connected:
            return False
        
        try:
            self.logger.info(f"Taking off to {altitude}m...")
            
            if not self._position:
                self.wait_for_position(timeout=5)
            
            if not self._position:
                self.logger.error("No position data")
                return False
            
            self.mav_connection.mav.command_long_send(
                self.target_system,
                self.target_component,
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                0, 0, 0, 0, 0,
                self._position.lat / 1e7,
                self._position.lon / 1e7,
                altitude
            )
            
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
    
    def arm_and_takeoff(self, altitude: float = 10.0, force_arm: bool = False, wait_ready: bool = True) -> bool:
        """Arm and takeoff to specified altitude
        
        Args:
            altitude: Takeoff altitude in meters
            force_arm: If True, force arm (skip pre-arm checks)
            wait_ready: If True, wait for system to be ready before arming
        """
        # Wait for system to be ready (unless force arming or explicitly disabled)
        if wait_ready and not force_arm:
            self.logger.info("Waiting for system to be ready to arm...")
            if not self.wait_until_ready_to_arm(timeout=60):
                self.logger.warning("Pre-arm checks did not pass completely")
                self.logger.info("Attempting to arm anyway (with retries)...")
        
        # Arm the drone (with retries)
        if not self.arm(force=force_arm, retry_count=5):
            return False
        
        time.sleep(2)  # Wait a bit after arming
        
        if not self.takeoff(altitude):
            return False
        
        self.logger.info("Waiting for drone to reach target altitude...")
        target_reached = False
        timeout = 60
        start_time = time.time()
        last_log_time = start_time
        
        while time.time() - start_time < timeout and not target_reached:
            msg = self.mav_connection.recv_match(
                type='GLOBAL_POSITION_INT',
                blocking=True,
                timeout=1
            )
            
            if msg:
                current_alt = msg.relative_alt / 1000.0
                
                # Log progress every 3 seconds
                if time.time() - last_log_time >= 3:
                    self.logger.info(f"  Climbing... {current_alt:.1f}m / {altitude:.1f}m")
                    last_log_time = time.time()
                
                if current_alt >= altitude * 0.95:
                    self.logger.info(f"✓ Reached target altitude: {current_alt:.1f}m")
                    target_reached = True
        
        if not target_reached:
            self.logger.warning(f"Did not reach target altitude within {timeout}s")
        
        return target_reached
    
    def set_mode(self, mode: str) -> bool:
        """Set flight mode using MAV_CMD_DO_SET_MODE for PX4
        
        Args:
            mode: Flight mode string (e.g., 'MISSION', 'LOITER', 'RTL')
        """
        if not self._is_connected:
            return False
        
        try:
            # Get available modes
            available_modes = self.mav_connection.mode_mapping()
            self.logger.debug(f"Available modes: {list(available_modes.keys())}")
            
            # Find the mode (case-insensitive)
            mode_found = None
            mode_data = None
            
            for available_mode, mode_value in available_modes.items():
                if available_mode.upper() == mode.upper():
                    mode_found = available_mode
                    mode_data = mode_value
                    break
            
            if mode_found is None:
                self.logger.error(f"Mode '{mode}' not found")
                self.logger.info(f"Available modes: {list(available_modes.keys())}")
                return False
            
            self.logger.info(f"Setting mode to {mode_found}...")
            self.logger.debug(f"Mode data: {mode_data}")
            
            # Handle PX4 tuple format: (mav_mode, main_mode, sub_mode)
            if isinstance(mode_data, tuple):
                if len(mode_data) == 3:
                    mav_mode, main_mode, sub_mode = mode_data
                    self.logger.debug(f"PX4 tuple: mav={mav_mode}, main={main_mode}, sub={sub_mode}")
                else:
                    self.logger.error(f"Unexpected tuple length: {len(mode_data)}")
                    return False
            else:
                # Single integer - shouldn't happen with PX4
                main_mode = mode_data
                sub_mode = 0
                self.logger.debug(f"Single mode ID: {mode_data}")
            
            # Use MAV_CMD_DO_SET_MODE (most reliable for PX4)
            self.logger.debug(f"Sending DO_SET_MODE: base=1, main={main_mode}, sub={sub_mode}")
            
            self.mav_connection.mav.command_long_send(
                self.target_system,
                self.target_component,
                mavutil.mavlink.MAV_CMD_DO_SET_MODE,
                0,  # confirmation
                1.0,  # param1: MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
                float(main_mode),  # param2: main mode
                float(sub_mode),   # param3: sub mode  
                0.0, 0.0, 0.0, 0.0
            )
            
            # Wait for ACK
            ack = self.mav_connection.recv_match(
                type='COMMAND_ACK',
                blocking=True,
                timeout=3
            )
            
            if ack and ack.command == mavutil.mavlink.MAV_CMD_DO_SET_MODE:
                if ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
                    self.logger.debug("✓ Mode command accepted")
                else:
                    self.logger.error(f"Mode command rejected: code {ack.result}")
                    return False
            else:
                self.logger.warning("No ACK received for mode change")
            
            # Wait for actual mode change in HEARTBEAT
            timeout = 5
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                msg = self.mav_connection.recv_match(
                    type='HEARTBEAT',
                    blocking=True,
                    timeout=0.5
                )
                
                if msg:
                    current_mode = msg.custom_mode
                    current_main = (current_mode >> 16) & 0xFF
                    current_sub = current_mode & 0xFFFF
                    
                    if current_main == main_mode and current_sub == sub_mode:
                        self.logger.info(f"✓ Mode changed to {mode_found}")
                        return True
                    
                    self.logger.debug(f"Waiting... current: main={current_main}, sub={current_sub}")
            
            # Timeout
            self.logger.error(f"Timeout waiting for {mode_found}")
            msg = self.mav_connection.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
            if msg:
                curr = msg.custom_mode
                curr_main = (curr >> 16) & 0xFF
                curr_sub = curr & 0xFFFF
                self.logger.error(f"  Target: main={main_mode}, sub={sub_mode}")
                self.logger.error(f"  Current: main={curr_main}, sub={curr_sub}")
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to set mode: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def start_mission(self) -> bool:
        """Start the uploaded mission"""
        if not self._is_connected:
            return False
        
        try:
            self.logger.info("Starting mission...")
            
            # Step 1: Set current mission item to 0
            self.logger.info("Setting current mission item to 0...")
            self.mav_connection.mav.mission_set_current_send(
                self.target_system,
                self.target_component,
                0
            )
            
            time.sleep(0.5)
            
            # Check for confirmation
            msg = self.mav_connection.recv_match(
                type='MISSION_CURRENT',
                blocking=True,
                timeout=2
            )
            
            if msg:
                self.logger.info(f"✓ Current mission item: {msg.seq}")
            else:
                self.logger.warning("No MISSION_CURRENT confirmation")
            
            # Step 2: Switch to MISSION mode
            self.logger.info("Switching to MISSION mode...")
            if self.set_mode('MISSION'):
                self._mission_active = True
                self.logger.info("✓ Mission started successfully!")
                time.sleep(1.0)
                return True
            else:
                self.logger.error("Failed to set MISSION mode")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start mission: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def monitor_mission(self) -> bool:
        """Monitor mission progress until completion"""
        if not self._is_connected:
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
                    
                    if self._mission_current >= self._mission_count - 1:
                        self.logger.info("✓ Mission complete!")
                        self._mission_active = False
                        return True
                
                hb = self.mav_connection.recv_match(type='HEARTBEAT', blocking=False)
                if hb:
                    self._heartbeat = hb
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error monitoring mission: {e}")
            return False
    
    def get_telemetry(self) -> Dict[str, Any]:
        """Get current telemetry data"""
        if not self._is_connected:
            return {}
        
        telemetry_data = {}
        
        try:
            self._update_telemetry()
            
            if self._position:
                telemetry_data["position"] = {
                    "latitude": self._position.lat / 1e7,
                    "longitude": self._position.lon / 1e7,
                    "altitude": self._position.relative_alt / 1000.0,
                    "absolute_altitude": self._position.alt / 1000.0
                }
            
            if self._position:
                telemetry_data["velocity"] = {
                    "north": self._position.vx / 100.0,
                    "east": self._position.vy / 100.0,
                    "down": self._position.vz / 100.0
                }
            
            if self._attitude:
                telemetry_data["attitude"] = {
                    "roll": math.degrees(self._attitude.roll),
                    "pitch": math.degrees(self._attitude.pitch),
                    "yaw": math.degrees(self._attitude.yaw)
                }
            
            if self._battery:
                telemetry_data["battery"] = {
                    "voltage": self._battery.voltages[0] / 1000.0 if self._battery.voltages else 0,
                    "remaining": self._battery.battery_remaining
                }
            
            if self._gps:
                telemetry_data["gps"] = {
                    "num_satellites": self._gps.satellites_visible,
                    "fix_type": self._gps.fix_type
                }
            
            if self._heartbeat:
                telemetry_data["flight_mode"] = self._get_mode_name(self._heartbeat.custom_mode)
                
        except Exception as e:
            self.logger.error(f"Error getting telemetry: {e}")
        
        return telemetry_data
    
    def _update_telemetry(self):
        """Update telemetry data cache"""
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
    
    def _get_mode_name(self, custom_mode: int) -> str:
        """Get mode name from custom_mode ID"""
        mode_mapping = self.mav_connection.mode_mapping()
        
        for name, mode_data in mode_mapping.items():
            if isinstance(mode_data, tuple):
                if len(mode_data) == 3:
                    _, main, sub = mode_data
                    mode_id = (main << 16) | sub
                    if mode_id == custom_mode:
                        return name
            else:
                if mode_data == custom_mode:
                    return name
        
        return f"UNKNOWN({custom_mode})"
    
    def return_to_launch(self) -> bool:
        """Return to launch position"""
        if not self._is_connected:
            return False
        
        try:
            self.logger.info("Returning to launch...")
            
            if not self.set_mode('RTL'):
                return False
            
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
            
            self.logger.error("Timeout waiting for landing")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to return to launch: {e}")
            return False
    
    def emergency_land(self) -> bool:
        """Emergency land at current position"""
        if not self._is_connected:
            return False
        
        try:
            self.logger.info("Emergency landing...")
            
            self.mav_connection.mav.command_long_send(
                self.target_system,
                self.target_component,
                mavutil.mavlink.MAV_CMD_NAV_LAND,
                0, 0, 0, 0, 0, 0, 0, 0
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


def main():
    """Example usage"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    config = SimulatorConfig(
        connection_url="udp:127.0.0.1:14540",
        simulator_type=SimulatorType.PX4_GAZEBO
    )
    
    sim = GazeboSimulatorController(config)
    
    if not sim.connect():
        print("Failed to connect")
        return
    
    if not sim.wait_for_position():
        print("Failed to get position")
        return
    
    waypoints = [
        {"lat": 47.397742, "lon": 8.545594, "alt": 50},
        {"lat": 47.398042, "lon": 8.545794, "alt": 50},
        {"lat": 47.398342, "lon": 8.545994, "alt": 50},
    ]
    
    if not sim.upload_mission(waypoints):
        print("Failed to upload mission")
        return
    
    if not sim.arm_and_takeoff(50, force_arm=True):
        print("Failed to arm and takeoff")
        return
    
    if not sim.start_mission():
        print("Failed to start mission")
        return
    
    sim.monitor_mission()
    telemetry = sim.get_telemetry()
    print(f"Final telemetry: {telemetry}")
    sim.return_to_launch()
    sim.disconnect()


if __name__ == "__main__":
    main()