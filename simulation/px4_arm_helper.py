#!/usr/bin/env python3
"""
px4_arm_helper.py

PX4 Arming Helper Script - Diagnose and fix arming issues

This script helps diagnose and fix arming issues with PX4 SITL.
It checks system status and can configure parameters for easier simulation testing.

Usage:
    python3 px4_arm_helper.py --check          # Check system status
    python3 px4_arm_helper.py --fix            # Apply simulation-friendly parameters
    python3 px4_arm_helper.py --force-arm      # Test with force arm
    python3 px4_arm_helper.py --all            # Check, fix, and test
"""

import argparse
import logging
import time
import sys
from pymavlink import mavutil

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def connect_to_px4(connection_url="udp:127.0.0.1:14540"):
    """Connect to PX4 SITL"""
    logger.info(f"Connecting to {connection_url}...")
    
    try:
        mav = mavutil.mavlink_connection(connection_url, source_system=255)
        
        logger.info("Waiting for heartbeat...")
        heartbeat = mav.wait_heartbeat(timeout=10)
        
        if heartbeat:
            logger.info(f"✓ Connected to system {mav.target_system}")
            logger.info(f"  Autopilot: {heartbeat.autopilot}, Vehicle type: {heartbeat.type}")
            return mav
        else:
            logger.error("✗ No heartbeat received")
            return None
    except Exception as e:
        logger.error(f"✗ Connection failed: {e}")
        return None


def check_system_status(mav):
    """Check all system status for arming readiness"""
    logger.info("\n" + "="*60)
    logger.info("SYSTEM STATUS CHECK")
    logger.info("="*60)
    
    checks = {
        "GPS Fix": False,
        "Home Position": False,
        "Global Position": False,
        "EKF OK": False,
        "Sensors OK": False,
        "Battery OK": False
    }
    
    details = {}
    
    # Wait and collect messages
    logger.info("\nCollecting system status (10 seconds)...")
    start_time = time.time()
    
    while time.time() - start_time < 10:
        msg = mav.recv_match(blocking=False)
        
        if not msg:
            time.sleep(0.1)
            continue
        
        msg_type = msg.get_type()
        
        if msg_type == 'GPS_RAW_INT':
            if msg.fix_type >= 3:
                checks["GPS Fix"] = True
                details["GPS"] = f"{msg.fix_type} fix, {msg.satellites_visible} satellites"
                logger.info(f"✓ GPS: {details['GPS']}")
        
        elif msg_type == 'HOME_POSITION':
            checks["Home Position"] = True
            details["Home"] = f"Lat={msg.latitude/1e7:.6f}, Lon={msg.longitude/1e7:.6f}"
            logger.info(f"✓ Home Position: {details['Home']}")
        
        elif msg_type == 'GLOBAL_POSITION_INT':
            checks["Global Position"] = True
            if "Global Pos" not in details:
                details["Global Pos"] = f"Alt={msg.relative_alt/1000:.1f}m"
        
        elif msg_type == 'EKF_STATUS_REPORT':
            if msg.flags & 0x01:
                checks["EKF OK"] = True
                logger.info(f"✓ EKF: Status OK (flags={msg.flags})")
        
        elif msg_type == 'SYS_STATUS':
            checks["Sensors OK"] = True
            if msg.voltage_battery > 0:
                checks["Battery OK"] = True
                details["Battery"] = f"{msg.voltage_battery/1000:.2f}V"
        
        elif msg_type == 'HEARTBEAT':
            if "Heartbeat" not in details:
                details["Heartbeat"] = f"Mode={msg.custom_mode}, Armed={msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED}"
    
    # Print summary
    logger.info("\n" + "-"*60)
    logger.info("PRE-ARM CHECK SUMMARY:")
    logger.info("-"*60)
    
    all_ok = True
    for check_name, status in checks.items():
        icon = "✓" if status else "✗"
        status_text = "PASS" if status else "FAIL"
        logger.info(f"  {icon} {check_name}: {status_text}")
        if not status:
            all_ok = False
    
    logger.info("-"*60)
    
    if all_ok:
        logger.info("\n✓ All checks passed - Ready to arm!")
        logger.info("  You can arm normally without force arm")
    else:
        logger.warning("\n✗ Some checks failed - Arming may be denied")
        logger.info("\nSuggested fixes:")
        logger.info("  1. Wait longer (30-60 seconds after starting PX4)")
        logger.info("  2. Run: python3 px4_arm_helper.py --fix")
        logger.info("  3. Use force arm in your test script")
        logger.info("  4. Restart PX4 and wait before testing")
    
    # Print additional details
    if details:
        logger.info("\nAdditional Information:")
        for key, value in details.items():
            logger.info(f"  {key}: {value}")
    
    return all_ok


def disable_arming_checks(mav):
    """Disable strict arming checks for simulation (DANGEROUS - SIM ONLY!)"""
    logger.info("\n" + "="*60)
    logger.info("CONFIGURING SIMULATION-FRIENDLY PARAMETERS")
    logger.info("="*60)
    logger.warning("\n⚠️  WARNING: These settings disable safety checks!")
    logger.warning("⚠️  ONLY USE IN SIMULATION - NEVER ON REAL HARDWARE!\n")
    
    # Parameters to modify for easier simulation
    params = {
        'COM_ARM_WO_GPS': 1,        # Allow arming without GPS
        'COM_ARM_MAG_STR': 0,       # Disable magnetometer strength check
        'EKF2_REQ_GPS_H': 0.0,      # Disable GPS horizontal accuracy requirement
        'COM_RC_IN_MODE': 1,        # RC not required
        'NAV_RCL_ACT': 0,           # Disable RC loss failsafe
        'NAV_DLL_ACT': 0,           # Disable data link loss failsafe
        'COM_ARM_EKF_AB': 0.0022,   # Relax EKF accel bias check
        'COM_ARM_EKF_GB': 0.0011,   # Relax EKF gyro bias check
    }
    
    logger.info("Setting parameters...")
    
    success_count = 0
    for param_name, param_value in params.items():
        try:
            logger.info(f"  Setting {param_name} = {param_value}")
            
            # Set parameter
            mav.mav.param_set_send(
                mav.target_system,
                mav.target_component,
                param_name.encode('utf-8'),
                param_value,
                mavutil.mavlink.MAV_PARAM_TYPE_REAL32
            )
            
            time.sleep(0.2)
            success_count += 1
            
        except Exception as e:
            logger.error(f"  ✗ Failed to set {param_name}: {e}")
    
    logger.info(f"\n✓ Set {success_count}/{len(params)} parameters successfully")
    logger.warning("\n⚠️  IMPORTANT: Restart PX4 for changes to take effect!")
    logger.info("\nRestart steps:")
    logger.info("  1. Stop PX4 (Ctrl+C in Terminal 1)")
    logger.info("  2. Run: make px4_sitl gazebo-classic")
    logger.info("  3. Wait 30 seconds, then test again")


def test_force_arm(mav):
    """Test force arming"""
    logger.info("\n" + "="*60)
    logger.info("TESTING FORCE ARM")
    logger.info("="*60)
    
    logger.info("\n⚠️  Attempting to force arm (bypassing pre-arm checks)...")
    
    # Try to arm with force flag
    mav.mav.command_long_send(
        mav.target_system,
        mav.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        1,      # arm
        21196,  # force arm magic number
        0, 0, 0, 0, 0
    )
    
    # Wait for response
    ack = mav.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
    
    if ack:
        if ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            logger.info("✓ Force arm SUCCESSFUL!")
            logger.info("  Your test scripts should work with force_arm=True")
            
            # Disarm after test
            time.sleep(2)
            logger.info("\nDisarming...")
            mav.mav.command_long_send(
                mav.target_system,
                mav.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,
                0, 0, 0, 0, 0, 0, 0
            )
            
            logger.info("✓ Disarmed - test complete")
            return True
        else:
            logger.error(f"✗ Force arm FAILED: Result code {ack.result}")
            logger.error("  Even force arm doesn't work - check PX4 console for errors")
            return False
    else:
        logger.error("✗ No response from autopilot (timeout)")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='PX4 Arming Helper - Diagnose and fix arming issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 px4_arm_helper.py --check        # Check what's wrong
  python3 px4_arm_helper.py --fix          # Fix parameters for simulation
  python3 px4_arm_helper.py --force-arm    # Test if force arm works
  python3 px4_arm_helper.py --all          # Do everything
        """
    )
    
    parser.add_argument('--check', action='store_true', 
                       help='Check system status and pre-arm checks')
    parser.add_argument('--fix', action='store_true', 
                       help='Apply simulation-friendly parameters')
    parser.add_argument('--force-arm', action='store_true', 
                       help='Test force arm capability')
    parser.add_argument('--all', action='store_true',
                       help='Run all checks and fixes')
    parser.add_argument('--url', default='udp:127.0.0.1:14540', 
                       help='Connection URL (default: udp:127.0.0.1:14540)')
    
    args = parser.parse_args()
    
    # If no arguments, show help
    if not (args.check or args.fix or args.force_arm or args.all):
        parser.print_help()
        return 1
    
    # Connect
    mav = connect_to_px4(args.url)
    if not mav:
        logger.error("\n✗ Failed to connect to PX4")
        logger.error("Make sure PX4 SITL is running:")
        logger.error("  cd ~/PX4-Autopilot")
        logger.error("  make px4_sitl gazebo-classic")
        return 1
    
    # Run requested actions
    if args.all or args.check:
        check_system_status(mav)
    
    if args.all or args.fix:
        disable_arming_checks(mav)
    
    if args.all or args.force_arm:
        test_force_arm(mav)
    
    # Close connection
    mav.close()
    
    logger.info("\n" + "="*60)
    logger.info("DONE")
    logger.info("="*60 + "\n")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)