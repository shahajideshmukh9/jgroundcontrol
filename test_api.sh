#!/bin/bash
# Quick API Testing Script for Mission Control System
# File: test_api.sh
# Usage: ./test_api.sh [command]

BASE_URL="http://localhost:8000"
HEADER="Content-Type: application/json"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

# ============================================================================
# Orchestrator Commands
# ============================================================================

orchestrator_status() {
    print_header "Orchestrator Status"
    curl -s "$BASE_URL/api/orchestrator/status" | jq .
}

orchestrator_start() {
    print_header "Start Orchestrator"
    curl -s -X POST "$BASE_URL/api/orchestrator/start" | jq .
}

orchestrator_events() {
    print_header "Recent Events"
    curl -s "$BASE_URL/api/orchestrator/events?limit=10" | jq .
}

# ============================================================================
# Vehicle Commands
# ============================================================================

list_vehicles() {
    print_header "List All Vehicles"
    curl -s "$BASE_URL/api/vehicles" | jq .
}

get_vehicle() {
    VEHICLE_ID=$1
    print_header "Get Vehicle: $VEHICLE_ID"
    curl -s "$BASE_URL/api/vehicles/$VEHICLE_ID" | jq .
}

register_vehicle() {
    print_header "Register Vehicle"
    
    read -p "Vehicle ID (e.g., V001): " VID
    read -p "Type (multi-rotor/fixed-wing/vtol): " VTYPE
    read -p "Latitude: " LAT
    read -p "Longitude: " LON
    read -p "Battery %: " BAT
    
    curl -s -X POST "$BASE_URL/api/vehicles" \
        -H "$HEADER" \
        -d "{
            \"id\": \"$VID\",
            \"type\": \"$VTYPE\",
            \"location\": {\"lat\": $LAT, \"lon\": $LON, \"alt\": 0},
            \"battery\": $BAT
        }" | jq .
}

register_sample_vehicles() {
    print_header "Registering Sample Vehicles"
    
    # Vehicle 1
    print_info "Registering V001 (multi-rotor)..."
    curl -s -X POST "$BASE_URL/api/vehicles" \
        -H "$HEADER" \
        -d '{
            "id": "V001",
            "type": "multi-rotor",
            "location": {"lat": 37.7749, "lon": -122.4194, "alt": 0},
            "battery": 95.0
        }' | jq -r '.message // "Already exists"'
    
    # Vehicle 2
    print_info "Registering V002 (fixed-wing)..."
    curl -s -X POST "$BASE_URL/api/vehicles" \
        -H "$HEADER" \
        -d '{
            "id": "V002",
            "type": "fixed-wing",
            "location": {"lat": 37.8044, "lon": -122.2712, "alt": 0},
            "battery": 88.0
        }' | jq -r '.message // "Already exists"'
    
    # Vehicle 3
    print_info "Registering V003 (vtol)..."
    curl -s -X POST "$BASE_URL/api/vehicles" \
        -H "$HEADER" \
        -d '{
            "id": "V003",
            "type": "vtol",
            "location": {"lat": 37.3382, "lon": -121.8863, "alt": 0},
            "battery": 100.0
        }' | jq -r '.message // "Already exists"'
    
    print_success "Sample vehicles registered!"
}

update_vehicle() {
    VEHICLE_ID=$1
    print_header "Update Vehicle: $VEHICLE_ID"
    
    curl -s -X PATCH "$BASE_URL/api/vehicles/$VEHICLE_ID" \
        -H "$HEADER" \
        -d '{
            "status": "armed",
            "battery": 90.0
        }' | jq .
}

# ============================================================================
# Mission Commands
# ============================================================================

list_missions() {
    print_header "List All Missions"
    curl -s "$BASE_URL/api/missions" | jq .
}

get_mission() {
    MISSION_ID=$1
    print_header "Get Mission: $MISSION_ID"
    curl -s "$BASE_URL/api/missions/$MISSION_ID" | jq .
}

create_survey_mission() {
    print_header "Create Survey Mission"
    
    curl -s -X POST "$BASE_URL/api/missions/survey" \
        -H "$HEADER" \
        -d '{
            "name": "Agricultural Field Survey",
            "polygon": [
                {"lat": 37.7749, "lon": -122.4194, "alt": 0},
                {"lat": 37.7799, "lon": -122.4194, "alt": 0},
                {"lat": 37.7799, "lon": -122.4144, "alt": 0},
                {"lat": 37.7749, "lon": -122.4144, "alt": 0}
            ],
            "grid_spacing": 30,
            "altitude": 100,
            "overlap": 0.7
        }' | jq .
}

create_corridor_mission() {
    print_header "Create Corridor Mission"
    
    curl -s -X POST "$BASE_URL/api/missions/corridor" \
        -H "$HEADER" \
        -d '{
            "name": "Pipeline Inspection Route",
            "start": {"lat": 37.8044, "lon": -122.2712, "alt": 0},
            "end": {"lat": 37.8244, "lon": -122.2512, "alt": 0},
            "width": 100,
            "altitude": 80,
            "segments": 3
        }' | jq .
}

create_structure_mission() {
    print_header "Create Structure Scan"
    
    curl -s -X POST "$BASE_URL/api/missions/structure-scan" \
        -H "$HEADER" \
        -d '{
            "name": "Bridge Inspection Alpha",
            "center": {"lat": 37.8715, "lon": -122.2730, "alt": 0},
            "radius": 50,
            "altitude_min": 30,
            "altitude_max": 70,
            "orbits": 3,
            "points_per_orbit": 24
        }' | jq .
}

execute_mission() {
    print_header "Execute Mission"
    
    read -p "Mission ID: " MID
    read -p "Vehicle ID: " VID
    
    curl -s -X POST "$BASE_URL/api/missions/execute" \
        -H "$HEADER" \
        -d "{
            \"mission_id\": \"$MID\",
            \"vehicle_id\": \"$VID\"
        }" | jq .
}

monitor_mission() {
    MISSION_ID=$1
    print_header "Monitor Mission: $MISSION_ID"
    curl -s "$BASE_URL/api/missions/$MISSION_ID/monitor" | jq .
}

validate_mission() {
    MISSION_ID=$1
    VEHICLE_ID=$2
    print_header "Validate Mission: $MISSION_ID with $VEHICLE_ID"
    curl -s -X POST "$BASE_URL/api/missions/$MISSION_ID/validate?vehicle_id=$VEHICLE_ID" | jq .
}

# ============================================================================
# Geofence Commands
# ============================================================================

list_geofences() {
    print_header "List All Geofences"
    curl -s "$BASE_URL/api/geofences" | jq .
}

create_geofence() {
    print_header "Create Geofence"
    
    curl -s -X POST "$BASE_URL/api/geofences" \
        -H "$HEADER" \
        -d '{
            "name": "Airport Restricted Zone",
            "type": "keep-out",
            "polygon": [
                {"lat": 37.6200, "lon": -122.3800, "alt": 0},
                {"lat": 37.6250, "lon": -122.3800, "alt": 0},
                {"lat": 37.6250, "lon": -122.3700, "alt": 0},
                {"lat": 37.6200, "lon": -122.3700, "alt": 0}
            ],
            "priority": 10,
            "min_altitude": 0,
            "max_altitude": 10000
        }' | jq .
}

# ============================================================================
# Workflow Commands
# ============================================================================

list_workflows() {
    print_header "List All Workflows"
    curl -s "$BASE_URL/api/workflows" | jq .
}

get_workflow() {
    WORKFLOW_ID=$1
    print_header "Get Workflow: $WORKFLOW_ID"
    curl -s "$BASE_URL/api/workflows/$WORKFLOW_ID" | jq .
}

# ============================================================================
# Monitoring Commands
# ============================================================================

get_health() {
    print_header "System Health"
    curl -s "$BASE_URL/api/health" | jq .
}

get_metrics() {
    print_header "System Metrics"
    curl -s "$BASE_URL/api/metrics" | jq .
}

get_dashboard() {
    print_header "Dashboard Data"
    curl -s "$BASE_URL/api/dashboard" | jq .
}

# ============================================================================
# Quick Test Scenarios
# ============================================================================

quick_test_basic() {
    print_header "Quick Test: Basic Flow"
    
    print_info "Step 1: Check orchestrator status"
    orchestrator_status
    sleep 1
    
    print_info "Step 2: Register sample vehicles"
    register_sample_vehicles
    sleep 1
    
    print_info "Step 3: List vehicles"
    list_vehicles
    sleep 1
    
    print_info "Step 4: Create survey mission"
    create_survey_mission
    sleep 1
    
    print_info "Step 5: List missions"
    list_missions
    
    print_success "Basic flow test completed!"
}

quick_test_full() {
    print_header "Quick Test: Full System"
    
    print_info "1. Registering vehicles..."
    register_sample_vehicles
    sleep 1
    
    print_info "2. Creating missions..."
    create_survey_mission
    sleep 1
    create_corridor_mission
    sleep 1
    
    print_info "3. Creating geofence..."
    create_geofence
    sleep 1
    
    print_info "4. Checking system status..."
    orchestrator_status
    sleep 1
    
    print_info "5. Getting health status..."
    get_health
    
    print_success "Full system test completed!"
}

stress_test() {
    print_header "Stress Test: Multiple Requests"
    
    print_info "Sending 10 rapid status requests..."
    for i in {1..10}; do
        curl -s "$BASE_URL/api/orchestrator/status" > /dev/null
        echo -n "."
    done
    echo ""
    
    print_success "Stress test completed!"
}

# ============================================================================
# Help / Menu
# ============================================================================

show_help() {
    cat << EOF

Mission Control API Test Script
================================

ORCHESTRATOR:
  ./test_api.sh status              - Get orchestrator status
  ./test_api.sh start               - Start orchestrator
  ./test_api.sh events              - Get recent events

VEHICLES:
  ./test_api.sh list-vehicles       - List all vehicles
  ./test_api.sh get-vehicle V001    - Get specific vehicle
  ./test_api.sh register-vehicle    - Register new vehicle (interactive)
  ./test_api.sh sample-vehicles     - Register sample vehicles
  ./test_api.sh update-vehicle V001 - Update vehicle status

MISSIONS:
  ./test_api.sh list-missions       - List all missions
  ./test_api.sh get-mission M001    - Get specific mission
  ./test_api.sh survey              - Create survey mission
  ./test_api.sh corridor            - Create corridor mission
  ./test_api.sh structure           - Create structure scan
  ./test_api.sh execute             - Execute mission (interactive)
  ./test_api.sh monitor M001        - Monitor mission progress
  ./test_api.sh validate M001 V001  - Validate mission

GEOFENCES:
  ./test_api.sh list-geofences      - List all geofences
  ./test_api.sh create-geofence     - Create sample geofence

WORKFLOWS:
  ./test_api.sh list-workflows      - List all workflows
  ./test_api.sh get-workflow WF001  - Get specific workflow

MONITORING:
  ./test_api.sh health              - Get system health
  ./test_api.sh metrics             - Get system metrics
  ./test_api.sh dashboard           - Get dashboard data

QUICK TESTS:
  ./test_api.sh test-basic          - Run basic flow test
  ./test_api.sh test-full           - Run full system test
  ./test_api.sh stress              - Run stress test

EXAMPLES:
  ./test_api.sh sample-vehicles     - Register 3 sample vehicles
  ./test_api.sh survey              - Create a survey mission
  ./test_api.sh test-basic          - Run quick basic test

EOF
}

# ============================================================================
# Main Script Logic
# ============================================================================

case "$1" in
    # Orchestrator
    status) orchestrator_status ;;
    start) orchestrator_start ;;
    events) orchestrator_events ;;
    
    # Vehicles
    list-vehicles) list_vehicles ;;
    get-vehicle) get_vehicle "$2" ;;
    register-vehicle) register_vehicle ;;
    sample-vehicles) register_sample_vehicles ;;
    update-vehicle) update_vehicle "$2" ;;
    
    # Missions
    list-missions) list_missions ;;
    get-mission) get_mission "$2" ;;
    survey) create_survey_mission ;;
    corridor) create_corridor_mission ;;
    structure) create_structure_mission ;;
    execute) execute_mission ;;
    monitor) monitor_mission "$2" ;;
    validate) validate_mission "$2" "$3" ;;
    
    # Geofences
    list-geofences) list_geofences ;;
    create-geofence) create_geofence ;;
    
    # Workflows
    list-workflows) list_workflows ;;
    get-workflow) get_workflow "$2" ;;
    
    # Monitoring
    health) get_health ;;
    metrics) get_metrics ;;
    dashboard) get_dashboard ;;
    
    # Quick Tests
    test-basic) quick_test_basic ;;
    test-full) quick_test_full ;;
    stress) stress_test ;;
    
    # Help
    help|--help|-h|"") show_help ;;
    
    *) 
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac