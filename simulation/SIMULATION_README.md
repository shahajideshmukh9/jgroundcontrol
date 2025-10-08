# Gazebo Simulation Integration - Complete Guide

## 📁 Files Overview

```
simulation/
├── __init__.py                    # Python package marker
├── gazebo_integration.py          # Core PyMAVLink integration
├── mission_sim_adapter.py         # Mission format adapter
├── test_mission_simple.py         # Main test script (use this!)
├── test_force_arm.py              # Backup test with force arm
└── px4_arm_helper.py              # Diagnostic tool
```

## 🚀 Quick Start

### Step 1: Start PX4 Simulator

```bash
# Terminal 1
cd ~/PX4-Autopilot
make px4_sitl gazebo-classic

# Wait for this message:
# INFO [simulator_mavlink] Simulator connected on UDP port 14540
```

### Step 2: Run Test (Wait 30 seconds after PX4 starts!)

```bash
# Terminal 2 - Wait 30 seconds, then:
cd /home/digambar/shahaji/jgroundcontrol
python3 simulation/test_mission_simple.py
```

### Expected Output:

```
======================================================================
  PX4 GAZEBO SIMULATION TEST
======================================================================

INFO: [1/8] Configuring simulator connection...
✓ Configuration ready

INFO: [2/8] Connecting to PX4 SITL...
✓ Connected to PX4

INFO: [3/8] Waiting for GPS lock...
✓ GPS locked

INFO: [4/8] Defining mission waypoints...
✓ Mission: 4 waypoints

INFO: [5/8] Uploading mission to autopilot...
✓ Mission uploaded

INFO: [6/8] Arming and taking off to 50m...
INFO: Waiting for system to be ready to arm...
INFO: ✓ All pre-arm checks passed
INFO: Arming drone...
INFO: ✓ Drone armed
INFO: Taking off to 50m...
INFO: ✓ Takeoff command accepted
✓ Airborne!

INFO: [7/8] Starting mission (AUTO mode)...
✓ Mission started

INFO: [8/8] Monitoring mission progress...
INFO: Mission progress: 0/4 (0.0%)
INFO: Mission progress: 1/4 (25.0%)
INFO: Mission progress: 2/4 (50.0%)
INFO: Mission progress: 3/4 (75.0%)
INFO: ✓ Mission complete!
✓ Mission complete!

INFO: Returning to launch position...
✓ Landed safely

======================================================================
  ✓ TEST COMPLETED SUCCESSFULLY!
======================================================================
```

## ⚠️ If Arming Still Fails

### Option 1: Use Force Arm (Quickest)

```bash
python3 simulation/test_force_arm.py
```

### Option 2: Fix PX4 Parameters (Best for repeated testing)

```bash
# Diagnose the issue
python3 simulation/px4_arm_helper.py --check

# Apply simulation-friendly settings
python3 simulation/px4_arm_helper.py --fix

# Restart PX4 (Terminal 1)
# Ctrl+C, then: make px4_sitl gazebo-classic

# Try again (Terminal 2)
python3 simulation/test_mission_simple.py
```

### Option 3: Wait Longer

Sometimes PX4 just needs more time to initialize:

```bash
# Start PX4
make px4_sitl gazebo-classic

# Wait 60 seconds (yes, really!)
sleep 60

# Then run test
python3 simulation/test_mission_simple.py
```

## 🔧 What Was Fixed

### Problem: Arming Error Code 1
**Error:** `Arm failed: 1` (MAV_RESULT_TEMPORARILY_REJECTED)

### Solutions Implemented:

1. **Retry Logic** (5 attempts with 2s delay)
   ```python
   # Now automatically retries 5 times
   sim.arm_and_takeoff(50)
   ```

2. **Pre-arm Check Waiting**
   ```python
   # Waits up to 60s for system to be ready
   sim.wait_until_ready_to_arm(timeout=60)
   ```

3. **Better Error Messages**
   ```python
   # Now shows specific error codes and suggestions
   ERROR: Arming denied - pre-arm checks failed!
   ERROR:   Run: python3 px4_arm_helper.py --check
   ```

4. **Force Arm Option**
   ```python
   # Bypass pre-arm checks (simulation only!)
   sim.arm_and_takeoff(50, force_arm=True)
   ```

## 📊 Error Code Reference

| Code | Meaning | Solution |
|------|---------|----------|
| 0 | ACCEPTED | ✓ Success! |
| 1 | TEMPORARILY_REJECTED | Wait and retry (auto-handled) |
| 2 | DENIED | Run `px4_arm_helper.py --fix` |
| 4 | UNSUPPORTED | Check PX4 version |
| 5 | FAILED | Check PX4 console logs |

## 🐛 Common Issues

### Issue: "No heartbeat received"
**Cause:** PX4 not running or wrong port  
**Fix:**
```bash
# Check if PX4 is running
ps aux | grep px4

# Check correct port
netstat -tuln | grep 14540

# Restart PX4
cd ~/PX4-Autopilot
make px4_sitl gazebo-classic
```

### Issue: "GPS position timeout"
**Cause:** PX4 not fully initialized  
**Fix:** Wait 30-60 seconds after starting PX4 before running test

### Issue: "Mission upload failed"
**Cause:** Not connected or mission format error  
**Fix:** Check waypoint format:
```python
waypoints = [
    {"lat": 47.397742, "lon": 8.545594, "alt": 50},  # ✓ Correct
    # Not: (47.397742, 8.545594, 50)  # ✗ Wrong
]
```

### Issue: "Arming denied after 5 retries"
**Cause:** Pre-arm checks failing  
**Fix:**
```bash
# Option A: Diagnose
python3 simulation/px4_arm_helper.py --check

# Option B: Fix parameters
python3 simulation/px4_arm_helper.py --fix
# Then restart PX4

# Option C: Use force arm
python3 simulation/test_force_arm.py
```

## 📝 Integration with Your jGCS Mission Controller

```python
# In your mission controller module
from simulation.mission_sim_adapter import run_jgcs_mission_simulation

# Test your mission in simulation
def test_mission_in_sim(mission_data):
    # Save mission to temp file
    import json
    with open('/tmp/test_mission.json', 'w') as f:
        json.dump(mission_data, f)
    
    # Run simulation
    results = run_jgcs_mission_simulation(
        mission_json_path='/tmp/test_mission.json',
        simulator_type='px4_gazebo',
        output_path='/tmp/sim_results.json',
        force_arm=False  # Set True if arming issues
    )
    
    if results['status'] == 'success':
        print(f"✓ Simulation passed in {results['duration_seconds']:.1f}s")
        return True
    else:
        print(f"✗ Simulation failed: {results['errors']}")
        return False
```

## 🎯 Test Checklist

Before running tests, verify:

- [ ] PX4 SITL is running (`make px4_sitl gazebo-classic`)
- [ ] Gazebo window is visible with drone
- [ ] Waited 30+ seconds after PX4 started
- [ ] No other programs using port 14540
- [ ] Python dependencies installed (`pip install pymavlink`)

## 🎓 Next Steps

1. ✅ Test basic mission with `test_mission_simple.py`
2. ✅ Integrate with your mission controller
3. ✅ Test your actual jGCS missions
4. ✅ Add custom validation logic
5. ✅ Deploy to production

## 📞 Getting Help

If you're still having issues:

1. **Check PX4 console** (Terminal 1) for specific errors
2. **Run diagnostic:** `python3 px4_arm_helper.py --check`
3. **Enable debug logging:**
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```
4. **Check PX4 logs:**
   ```bash
   cd ~/PX4-Autopilot/build/px4_sitl_default/logs
   ls -lt  # Find latest log
   ```

## ✅ Success Indicators

You'll know it's working when you see:
- ✓ Heartbeat received
- ✓ GPS locked
- ✓ Mission uploaded
- ✓ Drone armed
- ✓ Takeoff complete
- ✓ Mission started
- ✓ Mission progress updates
- ✓ Mission complete
- ✓ Landed safely

Congratulations! Your simulation is working! 🎉