# 🚀 Quick Start Guide - Mission Control System

Complete reference for loading dummy data and testing the orchestrator-based system.

---

## 📦 Available Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| `generate_dummy_data.py` | Generate realistic test data | Interactive Python script |
| `load_dummy_data.py` | Load JSON data via API | `python load_dummy_data.py` |
| `test_api.sh` | Quick API testing | `./test_api.sh [command]` |
| `dummy_data.json` | Pre-made test data | Reference file |

---

## ⚡ Quick Start (3 Steps)

### Step 1: Start the Orchestrator

```bash
# Terminal 1: Start orchestrator
python main.py
```

### Step 2: Start the API Server

```bash
# Terminal 2: Start API server
uvicorn api_server:app --reload --port 8000
```

### Step 3: Load Dummy Data

**Option A - Quick Load (Fastest):**
```bash
python load_dummy_data.py
```

**Option B - Interactive Generator:**
```bash
python generate_dummy_data.py
# Choose preset: 1-4 or custom
```

**Option C - Test Script:**
```bash
chmod +x test_api.sh
./test_api.sh sample-vehicles
./test_api.sh survey
./test_api.sh test-basic
```

---

## 🎮 Usage Examples

### Generate Dummy Data (Interactive)

```bash
python generate_dummy_data.py
```

**Menu Options:**
1. Small Demo (3 vehicles, 2 missions, 2 geofences)
2. Medium Fleet (10 vehicles, 8 missions, 5 geofences) ⭐ Recommended
3. Large Operation (20 vehicles, 15 missions, 8 geofences)
4. Stress Test (50 vehicles, 30 missions, 10 geofences)
5. Custom (choose your numbers)

**Features:**
- ✅ Realistic locations (San Francisco Bay Area)
- ✅ Varied vehicle types and statuses
- ✅ Multiple mission types
- ✅ Geofence zones (keep-in, keep-out, warning)
- ✅ Real-time simulation option
- ✅ Sample alert generation

---

### Load Data via API

```bash
# Load predefined data
python load_dummy_data.py

# Load custom JSON file
python load_dummy_data.py my_data.json
```

**Output:**
```
📡 Loading 3 vehicles...
   ✓ V001: multi-rotor
   ✓ V002: fixed-wing
   ✓ V003: vtol

🛡️ Loading 2 geofences...
   ✓ Airport Restricted Zone: keep-out
   ✓ Operational Boundary: keep-in

✅ Total: 5 successful, 0 failed
```

---

### Use Test Script

```bash
# Make executable (first time only)
chmod +x test_api.sh

# Quick commands
./test_api.sh status              # Orchestrator status
./test_api.sh sample-vehicles     # Register 3 sample vehicles
./test_api.sh list-vehicles       # List all vehicles
./test_api.sh survey              # Create survey mission
./test_api.sh test-basic          # Run quick test

# Full help
./test_api.sh help
```

---

## 📊 Dummy Data Contents

### Vehicles (Sample)

| ID | Type | Location | Battery | Status |
|----|------|----------|---------|--------|
| V001 | Multi-Rotor | SF (37.7749, -122.4194) | 95% | idle |
| V002 | Fixed-Wing | Oakland (37.8044, -122.2712) | 88% | idle |
| V003 | VTOL | San Jose (37.3382, -121.8863) | 100% | idle |
| V004-V010 | Mixed | Various | 70-100% | Various |

### Mission Types

**Survey Missions:**
- Agricultural Field Survey
- Forest Fire Detection
- Urban Infrastructure Check

**Corridor Missions:**
- Pipeline Inspection Route
- Power Line Corridor Scan
- Highway Traffic Survey

**Structure Scans:**
- Bridge Inspection
- Tower Assessment
- Wind Farm Analysis

### Geofences

| Name | Type | Priority | Area |
|------|------|----------|------|
| Airport Restricted Zone | keep-out | 10 | SFO vicinity |
| Military Base No-Fly | keep-out | 10 | Various |
| Operational Boundary | keep-in | 5 | Bay Area |
| Downtown Warning Zone | warning | 3 | SF Downtown |

---

## 🧪 Testing Scenarios

### Scenario 1: Basic Flow Test

```bash
# 1. Load vehicles
python load_dummy_data.py

# 2. Check status
curl http://localhost:8000/api/orchestrator/status | jq .

# 3. List vehicles
curl http://localhost:8000/api/vehicles | jq .

# 4. Create mission
curl -X POST http://localhost:8000/api/missions/survey \
  -H "Content-Type: application/json" \
  -d @dummy_data.json | jq .missions.survey

# 5. Execute mission
curl -X POST http://localhost:8000/api/missions/execute \
  -H "Content-Type: application/json" \
  -d '{"mission_id": "M001", "vehicle_id": "V001"}' | jq .
```

### Scenario 2: Using Test Script

```bash
# Complete flow
./test_api.sh test-full

# Step by step
./test_api.sh sample-vehicles
./test_api.sh survey
./test_api.sh execute
# Enter M001 and V001 when prompted
```

### Scenario 3: Python Generator with Simulation

```bash
python generate_dummy_data.py
# Choose option 2 (Medium Fleet)
# Yes to real-time simulation
# Watch live updates for 30 seconds
# Yes to generate sample alerts
```

---

## 📋 API Quick Reference

### Orchestrator

```bash
# Status
curl http://localhost:8000/api/orchestrator/status

# Start
curl -X POST http://localhost:8000/api/orchestrator/start

# Recent events
curl http://localhost:8000/api/orchestrator/events?limit=10
```

### Vehicles

```bash
# List all
curl http://localhost:8000/api/vehicles

# Get specific
curl http://localhost:8000/api/vehicles/V001

# Register new
curl -X POST http://localhost:8000/api/vehicles \
  -H "Content-Type: application/json" \
  -d '{
    "id": "V999",
    "type": "multi-rotor",
    "location": {"lat": 37.7749, "lon": -122.4194, "alt": 0},
    "battery": 100.0
  }'

# Get telemetry
curl http://localhost:8000/api/vehicles/V001/telemetry
```

### Missions

```bash
# List all
curl http://localhost:8000/api/missions

# Create survey
curl -X POST http://localhost:8000/api/missions/survey \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Survey",
    "polygon": [
      {"lat": 37.7749, "lon": -122.4194, "alt": 0},
      {"lat": 37.7799, "lon": -122.4194, "alt": 0},
      {"lat": 37.7799, "lon": -122.4144, "alt": 0},
      {"lat": 37.7749, "lon": -122.4144, "alt": 0}
    ],
    "grid_spacing": 30,
    "altitude": 100,
    "overlap": 0.7
  }'

# Execute
curl -X POST http://localhost:8000/api/missions/execute \
  -H "Content-Type: application/json" \
  -d '{"mission_id": "M001", "vehicle_id": "V001"}'

# Monitor
curl http://localhost:8000/api/missions/M001/monitor
```

### Geofences

```bash
# List all
curl http://localhost:8000/api/geofences

# Create
curl -X POST http://localhost:8000/api/geofences \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Zone",
    "type": "keep-out",
    "polygon": [
      {"lat": 37.7800, "lon": -122.4200, "alt": 0},
      {"lat": 37.7850, "lon": -122.4200, "alt": 0},
      {"lat": 37.7850, "lon": -122.4150, "alt": 0},
      {"lat": 37.7800, "lon": -122.4150, "alt": 0}
    ],
    "priority": 5,
    "min_altitude": 0,
    "max_altitude": 500
  }'
```

### Monitoring

```bash
# Health
curl http://localhost:8000/api/health

# Metrics
curl http://localhost:8000/api/metrics

# Dashboard
curl http://localhost:8000/api/dashboard
```

---

## 🎯 Common Use Cases

### Use Case 1: Demo for Stakeholders

```bash
# 1. Start system
python main.py &
uvicorn api_server:app --reload &

# 2. Load impressive dataset
python generate_dummy_data.py
# Choose "3. Large Operation"

# 3. Open dashboard
open http://localhost:8000

# 4. Show real-time updates
python generate_dummy_data.py
# Choose real-time simulation
```

### Use Case 2: Development Testing

```bash
# Quick reset and reload
pkill -f "python main.py"
pkill -f "uvicorn"

# Start fresh
python main.py &
sleep 2
uvicorn api_server:app --reload &
sleep 2

# Load test data
python load_dummy_data.py

# Run tests
./test_api.sh test-full
```

### Use Case 3: API Integration Testing

```bash
# Load baseline data
./test_api.sh sample-vehicles

# Test each endpoint
./test_api.sh list-vehicles
./test_api.sh survey
./test_api.sh corridor
./test_api.sh create-geofence
./test_api.sh status
```

---

## 🔧 Troubleshooting

### Server Not Running

```bash
# Check if server is running
curl http://localhost:8000/health

# If not, start it
uvicorn api_server:app --reload --port 8000
```

### Data Already Exists

```bash
# Vehicles already registered
# Error: "Vehicle already exists"

# Solution: Use different vehicle IDs or restart orchestrator
pkill -f "python main.py"
python main.py
```

### Import Errors

```bash
# If imports fail
# Make sure all files are in the same directory:
# - main.py
# - api_server.py
# - generate_dummy_data.py
# - load_dummy_data.py

# Install dependencies
pip install fastapi uvicorn pydantic requests
```

---

## 📈 Performance Tips

### For Large Datasets

```bash
# Use stress test preset
python generate_dummy_data.py
# Choose "4. Stress Test"

# Monitor performance
curl http://localhost:8000/api/metrics

# Check system resources
curl http://localhost:8000/api/health
```

### For Quick Iterations

```bash
# Use small demo
python generate_dummy_data.py
# Choose "1. Small Demo"

# Or minimal load
python load_dummy_data.py
```

---

## 🎨 Web Interface

Once data is loaded, access:

- **Main Dashboard**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc

**Dashboard Features:**
- Real-time vehicle status
- Mission progress tracking
- System health monitoring
- Event stream

---

## 📝 Custom Data

### Create Custom JSON

```json
{
  "vehicles": [
    {
      "id": "CUSTOM-001",
      "type": "multi-rotor",
      "location": {"lat": YOUR_LAT, "lon": YOUR_LON, "alt": 0},
      "battery": 100.0
    }
  ],
  "geofences": [
    {
      "name": "My Custom Zone",
      "type": "keep-out",
      "polygon": [YOUR_POLYGON],
      "priority": 5,
      "min_altitude": 0,
      "max_altitude": 500
    }
  ]
}
```

Load it:
```bash
python load_dummy_data.py my_custom_data.json
```

---

## 🚦 System Status Check

```bash
# Quick health check
curl http://localhost:8000/health | jq .

# Full status
curl http://localhost:8000/api/orchestrator/status | jq .

# Should show:
# - status: "running"
# - vehicles: number of registered vehicles
# - missions: number of created missions
# - events_processed: growing number
```

---

## 💡 Pro Tips

1. **Use test script for speed**: `./test_api.sh test-basic` runs a complete test in seconds

2. **Generate data programmatically**: Use `generate_dummy_data.py` for realistic scenarios

3. **Real-time monitoring**: Enable simulation in generator to see live updates

4. **Reset quickly**: Restart `main.py` to clear all data

5. **Check logs**: Monitor `main.py` terminal for event processing

6. **Use jq**: Pipe curl output to `jq .` for pretty JSON

7. **Save mission IDs**: Note mission IDs from creation to use in execution

---

## ✅ Verification Checklist

After loading data, verify:

- [ ] Orchestrator shows "running" status
- [ ] Vehicles appear in list
- [ ] Missions created successfully
- [ ] Geofences are active
- [ ] Dashboard displays data
- [ ] API docs accessible
- [ ] Health check returns "healthy"

---

## 📞 Quick Help

**Problem**: Data won't load
**Solution**: Check if API server is running on port 8000

**Problem**: Permission denied on test script
**Solution**: Run `chmod +x test_api.sh`

**Problem**: Module not found
**Solution**: Run `pip install -r requirements.txt`

**Problem**: Port already in use
**Solution**: Kill existing process or use different port

---

**Ready to test! 🎉**

Choose your method:
1. **Fastest**: `python load_dummy_data.py`
2. **Most Realistic**: `python generate_dummy_data.py`
3. **Most Flexible**: `./test_api.sh test-full`