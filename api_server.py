# FastAPI Web Server for Orchestrator-Based Mission Control
# File: api_server.py

"""
Run with: uvicorn api_server:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import asyncio
import json
from datetime import datetime

# Import from main orchestrator module
# In production: from main import OrchestratorEngine, Vehicle, Mission, etc.
# For this example, we'll define the app structure

app = FastAPI(
    title="Ground Controller Mission Control API",
    description="Orchestrator-based mission control system",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance (initialized in lifespan)
orchestrator = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class LocationModel(BaseModel):
    lat: float
    lon: float
    alt: float = 0.0

class VehicleCreateRequest(BaseModel):
    id: str
    type: str  # multi-rotor, fixed-wing, vtol
    location: LocationModel
    battery: float = 100.0

class VehicleUpdateRequest(BaseModel):
    status: Optional[str] = None
    location: Optional[LocationModel] = None
    battery: Optional[float] = None

class SurveyMissionRequest(BaseModel):
    name: str
    polygon: List[LocationModel]
    grid_spacing: float = 50.0
    altitude: float = 100.0
    overlap: float = 0.7

class CorridorMissionRequest(BaseModel):
    name: str
    start: LocationModel
    end: LocationModel
    width: float = 100.0
    altitude: float = 100.0
    segments: int = 3

class StructureScanRequest(BaseModel):
    name: str
    center: LocationModel
    radius: float = 50.0
    altitude_min: float = 30.0
    altitude_max: float = 70.0
    orbits: int = 3
    points_per_orbit: int = 24

class MissionExecuteRequest(BaseModel):
    mission_id: str
    vehicle_id: str

class GeofenceCreateRequest(BaseModel):
    name: str
    type: str  # keep-in, keep-out, warning
    polygon: List[LocationModel]
    priority: int = 1
    min_altitude: float = 0.0
    max_altitude: float = 1000.0

# ============================================================================
# LIFECYCLE EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator on startup"""
    global orchestrator
    
    # Import here to avoid circular imports
    from main import OrchestratorEngine, VehicleFactory, VehicleType, Location, Geofence
    
    orchestrator = OrchestratorEngine()
    orchestrator.start()
    
    # Add sample data
    sample_vehicle = VehicleFactory.create_vehicle(
        "V001",
        VehicleType.MULTI_ROTOR,
        Location(37.7749, -122.4194, 0)
    )
    orchestrator.vehicle_manager.register_vehicle(sample_vehicle)
    
    sample_vehicle2 = VehicleFactory.create_vehicle(
        "V002",
        VehicleType.FIXED_WING,
        Location(37.7849, -122.4094, 0)
    )
    orchestrator.vehicle_manager.register_vehicle(sample_vehicle2)
    
    # Add sample geofence
    sample_geofence = Geofence(
        id="GF001",
        name="Restricted Airspace",
        type="keep-out",
        polygon=[
            Location(37.7800, -122.4200),
            Location(37.7850, -122.4200),
            Location(37.7850, -122.4150),
            Location(37.7800, -122.4150),
            Location(37.7800, -122.4200)
        ]
    )
    orchestrator.geofencing.add_zone(sample_geofence)
    
    print("✅ Orchestrator API Server Started")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown orchestrator"""
    if orchestrator:
        orchestrator.stop()
    print("🛑 Orchestrator API Server Stopped")

# ============================================================================
# ORCHESTRATOR ENDPOINTS
# ============================================================================

@app.get("/api/orchestrator/status")
async def get_orchestrator_status():
    """Get orchestrator status and metrics"""
    return orchestrator.get_status()

@app.post("/api/orchestrator/start")
async def start_orchestrator():
    """Start orchestrator engine"""
    orchestrator.start()
    return {"status": "started", "message": "Orchestrator engine started"}

@app.post("/api/orchestrator/stop")
async def stop_orchestrator():
    """Stop orchestrator engine"""
    orchestrator.stop()
    return {"status": "stopped", "message": "Orchestrator engine stopped"}

@app.get("/api/orchestrator/events")
async def get_recent_events(limit: int = 50):
    """Get recent events from event router"""
    events = list(orchestrator.event_router.event_history)[-limit:]
    return {
        "count": len(events),
        "events": [
            {
                "id": e.id,
                "type": e.type,
                "priority": e.priority.name,
                "timestamp": e.timestamp.isoformat(),
                "source": e.source,
                "data": e.data,
                "processed": e.processed
            }
            for e in events
        ]
    }

@app.get("/api/orchestrator/state")
async def get_global_state():
    """Get global state snapshot"""
    return orchestrator.state_manager.snapshot()

# ============================================================================
# VEHICLE ENDPOINTS (Task 1.12, 2.C.1)
# ============================================================================

@app.get("/api/vehicles")
async def list_vehicles():
    """List all vehicles"""
    vehicles = orchestrator.vehicle_manager.get_all_vehicles()
    return {
        "count": len(vehicles),
        "vehicles": [
            {
                "id": v.id,
                "type": v.type.value,
                "status": v.status.value,
                "location": {
                    "lat": v.location.lat,
                    "lon": v.location.lon,
                    "alt": v.location.alt
                },
                "battery": v.battery,
                "mission_id": v.mission_id,
                "mission_progress": v.mission_progress,
                "capabilities": {
                    "max_speed": v.capabilities.max_speed,
                    "max_altitude": v.capabilities.max_altitude,
                    "max_range": v.capabilities.max_range,
                    "endurance": v.capabilities.endurance,
                    "sensors": v.capabilities.sensors
                },
                "last_update": v.last_update.isoformat()
            }
            for v in vehicles
        ]
    }

@app.get("/api/vehicles/{vehicle_id}")
async def get_vehicle(vehicle_id: str):
    """Get vehicle details"""
    vehicle = orchestrator.vehicle_manager.get_vehicle(vehicle_id)
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    return {
        "id": vehicle.id,
        "type": vehicle.type.value,
        "status": vehicle.status.value,
        "location": {
            "lat": vehicle.location.lat,
            "lon": vehicle.location.lon,
            "alt": vehicle.location.alt
        },
        "battery": vehicle.battery,
        "mission_id": vehicle.mission_id,
        "mission_progress": vehicle.mission_progress,
        "capabilities": {
            "max_speed": vehicle.capabilities.max_speed,
            "max_altitude": vehicle.capabilities.max_altitude,
            "max_range": vehicle.capabilities.max_range,
            "cruise_speed": vehicle.capabilities.cruise_speed,
            "endurance": vehicle.capabilities.endurance,
            "payload_capacity": vehicle.capabilities.payload_capacity,
            "sensors": vehicle.capabilities.sensors
        },
        "metadata": vehicle.metadata,
        "last_update": vehicle.last_update.isoformat()
    }

@app.post("/api/vehicles")
async def create_vehicle(request: VehicleCreateRequest):
    """Register new vehicle"""
    from main import VehicleFactory, VehicleType, Location
    
    vehicle = VehicleFactory.create_vehicle(
        request.id,
        VehicleType(request.type),
        Location(request.location.lat, request.location.lon, request.location.alt)
    )
    vehicle.battery = request.battery
    
    if not orchestrator.vehicle_manager.register_vehicle(vehicle):
        raise HTTPException(status_code=400, detail="Vehicle already exists")
    
    return {"message": "Vehicle registered successfully", "vehicle_id": vehicle.id}

@app.patch("/api/vehicles/{vehicle_id}")
async def update_vehicle(vehicle_id: str, request: VehicleUpdateRequest):
    """Update vehicle status/location"""
    from main import VehicleStatus, Location
    
    vehicle = orchestrator.vehicle_manager.get_vehicle(vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    if request.status:
        orchestrator.vehicle_manager.update_status(vehicle_id, VehicleStatus(request.status))
    
    if request.location:
        orchestrator.vehicle_manager.update_location(
            vehicle_id,
            Location(request.location.lat, request.location.lon, request.location.alt)
        )
    
    if request.battery is not None:
        vehicle.battery = request.battery
    
    return {"message": "Vehicle updated successfully"}

@app.get("/api/vehicles/{vehicle_id}/telemetry")
async def get_vehicle_telemetry(vehicle_id: str):
    """Get real-time vehicle telemetry"""
    vehicle = orchestrator.vehicle_manager.get_vehicle(vehicle_id)
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Check for geofence breaches
    breaches = orchestrator.geofencing.check_breach(vehicle.location, vehicle_id)
    
    return {
        "vehicle_id": vehicle.id,
        "status": vehicle.status.value,
        "location": {
            "lat": vehicle.location.lat,
            "lon": vehicle.location.lon,
            "alt": vehicle.location.alt
        },
        "battery": vehicle.battery,
        "mission_progress": vehicle.mission_progress,
        "geofence_breaches": breaches,
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# MISSION ENDPOINTS (Task 3.9, 3.C.1)
# ============================================================================

@app.get("/api/missions")
async def list_missions():
    """List all missions"""
    missions = list(orchestrator.missions.values())
    return {
        "count": len(missions),
        "missions": [
            {
                "id": m.id,
                "name": m.name,
                "type": m.type.value,
                "status": m.status.value,
                "vehicle_id": m.vehicle_id,
                "progress": m.progress,
                "waypoint_count": len(m.waypoints),
                "created_at": m.created_at.isoformat(),
                "metadata": m.metadata
            }
            for m in missions
        ]
    }

@app.get("/api/missions/{mission_id}")
async def get_mission(mission_id: str):
    """Get mission details"""
    mission = orchestrator.missions.get(mission_id)
    
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    return {
        "id": mission.id,
        "name": mission.name,
        "type": mission.type.value,
        "status": mission.status.value,
        "vehicle_id": mission.vehicle_id,
        "progress": mission.progress,
        "waypoints": [
            {
                "sequence": wp.sequence,
                "lat": wp.lat,
                "lon": wp.lon,
                "alt": wp.alt,
                "command": wp.command,
                "params": wp.params
            }
            for wp in mission.waypoints
        ],
        "created_at": mission.created_at.isoformat(),
        "started_at": mission.started_at.isoformat() if mission.started_at else None,
        "completed_at": mission.completed_at.isoformat() if mission.completed_at else None,
        "metadata": mission.metadata
    }

@app.post("/api/missions/survey")
async def create_survey_mission(request: SurveyMissionRequest):
    """Create survey mission"""
    from main import Location
    
    polygon = [Location(p.lat, p.lon, p.alt) for p in request.polygon]
    
    mission = orchestrator.mission_planner.create_survey_mission(
        aoi_polygon=polygon,
        grid_spacing=request.grid_spacing,
        altitude=request.altitude,
        overlap=request.overlap
    )
    mission.name = request.name
    
    orchestrator.missions[mission.id] = mission
    orchestrator.state_manager.set(f'missions.{mission.id}', {
        'id': mission.id,
        'name': mission.name,
        'type': mission.type.value,
        'status': mission.status.value
    })
    
    return {
        "message": "Survey mission created",
        "mission_id": mission.id,
        "waypoint_count": len(mission.waypoints),
        "metadata": mission.metadata
    }

@app.post("/api/missions/corridor")
async def create_corridor_mission(request: CorridorMissionRequest):
    """Create corridor mission"""
    from main import Location
    
    mission = orchestrator.mission_planner.create_corridor_mission(
        start=Location(request.start.lat, request.start.lon, request.start.alt),
        end=Location(request.end.lat, request.end.lon, request.end.alt),
        width=request.width,
        altitude=request.altitude,
        segments=request.segments
    )
    mission.name = request.name
    
    orchestrator.missions[mission.id] = mission
    orchestrator.state_manager.set(f'missions.{mission.id}', {
        'id': mission.id,
        'name': mission.name,
        'type': mission.type.value,
        'status': mission.status.value
    })
    
    return {
        "message": "Corridor mission created",
        "mission_id": mission.id,
        "waypoint_count": len(mission.waypoints),
        "metadata": mission.metadata
    }

@app.post("/api/missions/structure-scan")
async def create_structure_scan(request: StructureScanRequest):
    """Create structure scan mission"""
    from main import Location
    
    mission = orchestrator.mission_planner.create_structure_scan(
        center=Location(request.center.lat, request.center.lon, request.center.alt),
        radius=request.radius,
        altitude_min=request.altitude_min,
        altitude_max=request.altitude_max,
        orbits=request.orbits,
        points_per_orbit=request.points_per_orbit
    )
    mission.name = request.name
    
    orchestrator.missions[mission.id] = mission
    orchestrator.state_manager.set(f'missions.{mission.id}', {
        'id': mission.id,
        'name': mission.name,
        'type': mission.type.value,
        'status': mission.status.value
    })
    
    return {
        "message": "Structure scan created",
        "mission_id": mission.id,
        "waypoint_count": len(mission.waypoints),
        "metadata": mission.metadata
    }

@app.post("/api/missions/{mission_id}/validate")
async def validate_mission(mission_id: str, vehicle_id: str):
    """Validate mission against vehicle capabilities"""
    mission = orchestrator.missions.get(mission_id)
    vehicle = orchestrator.vehicle_manager.get_vehicle(vehicle_id)
    
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    validation = orchestrator.mission_planner.validate_mission(mission, vehicle)
    
    return {
        "mission_id": mission_id,
        "vehicle_id": vehicle_id,
        "valid": validation['valid'],
        "issues": validation['issues'],
        "warnings": validation['warnings'],
        "estimated_time": validation['estimated_time'],
        "total_distance": validation['total_distance'],
        "required_battery": validation['required_battery']
    }

@app.post("/api/missions/execute")
async def execute_mission(request: MissionExecuteRequest):
    """Execute mission workflow"""
    result = await orchestrator.execute_mission_workflow(
        request.mission_id,
        request.vehicle_id
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    return {
        "message": "Mission execution started",
        "workflow_id": result.get('workflow_id'),
        "validation": result.get('validation')
    }

@app.get("/api/missions/{mission_id}/monitor")
async def monitor_mission(mission_id: str):
    """Monitor mission progress"""
    mission = orchestrator.missions.get(mission_id)
    
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    vehicle = None
    breaches = []
    
    if mission.vehicle_id:
        vehicle = orchestrator.vehicle_manager.get_vehicle(mission.vehicle_id)
        if vehicle:
            breaches = orchestrator.geofencing.check_breach(vehicle.location)
    
    return {
        "mission_id": mission_id,
        "name": mission.name,
        "status": mission.status.value,
        "progress": mission.progress,
        "vehicle": {
            "id": vehicle.id,
            "status": vehicle.status.value,
            "battery": vehicle.battery,
            "location": {
                "lat": vehicle.location.lat,
                "lon": vehicle.location.lon,
                "alt": vehicle.location.alt
            }
        } if vehicle else None,
        "geofence_breaches": breaches,
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# GEOFENCE ENDPOINTS (Task 5.19, 5.C.1)
# ============================================================================

@app.get("/api/geofences")
async def list_geofences():
    """List all geofences"""
    geofences = list(orchestrator.geofencing.zones.values())
    return {
        "count": len(geofences),
        "geofences": [
            {
                "id": gf.id,
                "name": gf.name,
                "type": gf.type,
                "active": gf.active,
                "priority": gf.priority,
                "polygon": [
                    {"lat": p.lat, "lon": p.lon, "alt": p.alt}
                    for p in gf.polygon
                ],
                "min_altitude": gf.min_altitude,
                "max_altitude": gf.max_altitude
            }
            for gf in geofences
        ]
    }

@app.post("/api/geofences")
async def create_geofence(request: GeofenceCreateRequest):
    """Create geofence"""
    from main import Geofence, Location
    import uuid
    
    geofence = Geofence(
        id=f"GF-{uuid.uuid4().hex[:8].upper()}",
        name=request.name,
        type=request.type,
        polygon=[Location(p.lat, p.lon, p.alt) for p in request.polygon],
        priority=request.priority,
        min_altitude=request.min_altitude,
        max_altitude=request.max_altitude
    )
    
    if not orchestrator.geofencing.add_zone(geofence):
        raise HTTPException(status_code=400, detail="Invalid geofence polygon")
    
    return {
        "message": "Geofence created successfully",
        "geofence_id": geofence.id
    }

@app.post("/api/geofences/{geofence_id}/toggle")
async def toggle_geofence(geofence_id: str):
    """Activate/deactivate geofence"""
    geofence = orchestrator.geofencing.zones.get(geofence_id)
    
    if not geofence:
        raise HTTPException(status_code=404, detail="Geofence not found")
    
    geofence.active = not geofence.active
    
    return {
        "geofence_id": geofence_id,
        "active": geofence.active
    }

# ============================================================================
# WORKFLOW ENDPOINTS (Task 3.C.2)
# ============================================================================

@app.get("/api/workflows")
async def list_workflows():
    """List all workflows"""
    workflows = list(orchestrator.workflow_coordinator.workflows.values())
    return {
        "count": len(workflows),
        "workflows": [
            {
                "id": w.id,
                "name": w.name,
                "status": w.status.value,
                "steps": [
                    {
                        "name": s.name,
                        "status": s.status
                    }
                    for s in w.steps
                ],
                "created_at": w.created_at.isoformat(),
                "started_at": w.started_at.isoformat() if w.started_at else None,
                "completed_at": w.completed_at.isoformat() if w.completed_at else None
            }
            for w in workflows
        ]
    }

@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get workflow details"""
    workflow = orchestrator.workflow_coordinator.workflows.get(workflow_id)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {
        "id": workflow.id,
        "name": workflow.name,
        "status": workflow.status.value,
        "steps": [
            {
                "name": step.name,
                "status": step.status,
                "result": step.result,
                "error": step.error
            }
            for step in workflow.steps
        ],
        "context": workflow.context,
        "created_at": workflow.created_at.isoformat(),
        "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
        "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None
    }

# ============================================================================
# WEBSOCKET ENDPOINTS (Task 2.16)
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Send system status
            status = orchestrator.get_status()
            vehicles = orchestrator.vehicle_manager.get_all_vehicles()
            missions = list(orchestrator.missions.values())
            
            update = {
                "type": "system_update",
                "timestamp": datetime.now().isoformat(),
                "orchestrator": status,
                "vehicles": [
                    {
                        "id": v.id,
                        "status": v.status.value,
                        "battery": v.battery,
                        "location": {
                            "lat": v.location.lat,
                            "lon": v.location.lon,
                            "alt": v.location.alt
                        },
                        "mission_id": v.mission_id,
                        "mission_progress": v.mission_progress
                    }
                    for v in vehicles
                ],
                "missions": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "status": m.status.value,
                        "progress": m.progress
                    }
                    for m in missions
                ]
            }
            
            await websocket.send_json(update)
            await asyncio.sleep(1)  # Update every second
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "Ground Controller Mission Control API",
        "version": "2.0.0",
        "status": "operational",
        "orchestrator": orchestrator.status if orchestrator else "not_initialized",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "orchestrator": orchestrator.status if orchestrator else "not_initialized",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)