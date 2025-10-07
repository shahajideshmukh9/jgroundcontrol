# Ground Controller Mission Control System - Orchestrator Architecture
# Task-Mapped Implementation

"""
Installation Requirements:
pip install fastapi uvicorn pydantic kafka-python redis sqlalchemy websockets shapely geopy numpy
"""

import asyncio
import json
import math
import uuid
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
from queue import PriorityQueue
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# PART 1: CORE DATA MODELS (Tasks 1.5, 2.1, 3.8, 5.18)
# ============================================================================

class VehicleType(str, Enum):
    MULTI_ROTOR = "multi-rotor"
    FIXED_WING = "fixed-wing"
    VTOL = "vtol"

class VehicleStatus(str, Enum):
    IDLE = "idle"
    ARMED = "armed"
    FLYING = "flying"
    LANDING = "landing"
    EMERGENCY = "emergency"
    OFFLINE = "offline"

class MissionType(str, Enum):
    SURVEY = "survey"
    CORRIDOR = "corridor"
    STRUCTURE_SCAN = "structure"
    CUSTOM = "custom"

class MissionStatus(str, Enum):
    CREATED = "created"
    PLANNED = "planned"
    VALIDATING = "validating"
    VALIDATED = "validated"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkflowStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class EventPriority(int, Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5

@dataclass
class Location:
    lat: float
    lon: float
    alt: float = 0.0

@dataclass
class VehicleCapabilities:
    max_speed: float = 15.0  # m/s
    max_altitude: float = 500.0  # meters
    max_range: float = 10000.0  # meters
    cruise_speed: float = 10.0  # m/s
    endurance: float = 30.0  # minutes
    payload_capacity: float = 2.0  # kg
    sensors: List[str] = field(default_factory=list)

@dataclass
class Vehicle:
    id: str
    type: VehicleType
    status: VehicleStatus
    location: Location
    battery: float
    capabilities: VehicleCapabilities
    mission_id: Optional[str] = None
    mission_progress: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Waypoint:
    lat: float
    lon: float
    alt: float
    command: str = "WAYPOINT"
    params: Dict[str, float] = field(default_factory=dict)
    sequence: int = 0

@dataclass
class Mission:
    id: str
    name: str
    type: MissionType
    status: MissionStatus
    waypoints: List[Waypoint]
    vehicle_id: Optional[str] = None
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Geofence:
    id: str
    name: str
    type: str  # keep-in, keep-out, warning
    polygon: List[Location]
    priority: int = 1
    active: bool = True
    min_altitude: float = 0.0
    max_altitude: float = 1000.0
    temporal_rules: Optional[Dict] = None

# ============================================================================
# PART 2: EVENT SYSTEM (Tasks 1.O.2, 1.O.4)
# ============================================================================

@dataclass
class Event:
    id: str
    type: str
    priority: EventPriority
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    processed: bool = False

class EventRouter:
    """Event router with priority queue and error handling (Task 1.O.2)"""
    
    def __init__(self):
        self.event_queue = PriorityQueue()
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.event_history = deque(maxlen=1000)
        self.error_handlers: List[Callable] = []
        self.running = False
        self.worker_thread = None
        
    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to event type"""
        self.subscribers[event_type].append(handler)
        logger.info(f"Subscribed to {event_type}")
    
    def publish(self, event: Event):
        """Publish event to queue (Task 1.O.2)"""
        self.event_queue.put((event.priority.value, event.timestamp, event))
        self.event_history.append(event)
        logger.info(f"Event published: {event.type} [Priority: {event.priority.name}]")
    
    def start(self):
        """Start event processing"""
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_events, daemon=True)
        self.worker_thread.start()
        logger.info("Event Router started")
    
    def stop(self):
        """Stop event processing"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("Event Router stopped")
    
    def _process_events(self):
        """Process events from queue with error handling"""
        while self.running:
            try:
                if not self.event_queue.empty():
                    priority, timestamp, event = self.event_queue.get(timeout=1)
                    self._dispatch_event(event)
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Event processing error: {e}")
                self._handle_error(e)
    
    def _dispatch_event(self, event: Event):
        """Dispatch event to subscribers"""
        handlers = self.subscribers.get(event.type, [])
        handlers.extend(self.subscribers.get('*', []))  # Wildcard subscribers
        
        for handler in handlers:
            try:
                handler(event)
                event.processed = True
            except Exception as e:
                logger.error(f"Handler error for {event.type}: {e}")
                self._handle_error(e)
    
    def _handle_error(self, error: Exception):
        """Handle errors with registered handlers"""
        for handler in self.error_handlers:
            try:
                handler(error)
            except Exception as e:
                logger.error(f"Error handler failed: {e}")

# ============================================================================
# PART 3: GLOBAL STATE MANAGER (Task 1.O.3)
# ============================================================================

class GlobalStateManager:
    """Global state manager with persistence (Task 1.O.3)"""
    
    def __init__(self):
        self.state: Dict[str, Any] = {
            'vehicles': {},
            'missions': {},
            'geofences': {},
            'workflows': {},
            'system': {
                'status': 'initialized',
                'start_time': datetime.now(),
                'event_count': 0,
                'active_missions': 0
            }
        }
        self.state_lock = threading.Lock()
        self.state_history = deque(maxlen=100)
        self.persistence_enabled = False
        
    def get(self, key: str, default=None) -> Any:
        """Get state value"""
        with self.state_lock:
            keys = key.split('.')
            value = self.state
            for k in keys:
                value = value.get(k, default)
                if value is None:
                    return default
            return value
    
    def set(self, key: str, value: Any):
        """Set state value with history"""
        with self.state_lock:
            keys = key.split('.')
            state = self.state
            for k in keys[:-1]:
                if k not in state:
                    state[k] = {}
                state = state[k]
            
            old_value = state.get(keys[-1])
            state[keys[-1]] = value
            
            # Record state change
            self.state_history.append({
                'timestamp': datetime.now(),
                'key': key,
                'old_value': old_value,
                'new_value': value
            })
            
            if self.persistence_enabled:
                self._persist_state()
    
    def update(self, key: str, updates: Dict):
        """Update nested state"""
        current = self.get(key, {})
        if isinstance(current, dict):
            current.update(updates)
            self.set(key, current)
    
    def delete(self, key: str):
        """Delete state value"""
        with self.state_lock:
            keys = key.split('.')
            state = self.state
            for k in keys[:-1]:
                state = state.get(k, {})
            if keys[-1] in state:
                del state[keys[-1]]
    
    def snapshot(self) -> Dict:
        """Get state snapshot"""
        with self.state_lock:
            return json.loads(json.dumps(self.state, default=str))
    
    def _persist_state(self):
        """Persist state to storage (Task 1.O.3)"""
        # Implement persistence to file/database
        try:
            with open('orchestrator_state.json', 'w') as f:
                json.dump(self.state, f, default=str, indent=2)
        except Exception as e:
            logger.error(f"State persistence error: {e}")

# ============================================================================
# PART 4: WORKFLOW COORDINATOR (Tasks 3.O.1, 3.O.3, 4.O.3, 4.O.4)
# ============================================================================

@dataclass
class WorkflowStep:
    name: str
    handler: Callable
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    rollback_handler: Optional[Callable] = None

@dataclass
class Workflow:
    id: str
    name: str
    status: WorkflowStatus
    steps: List[WorkflowStep]
    context: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class WorkflowCoordinator:
    """Workflow coordinator with rollback capability (Task 3.O.3)"""
    
    def __init__(self, state_manager: GlobalStateManager, event_router: EventRouter):
        self.state_manager = state_manager
        self.event_router = event_router
        self.workflows: Dict[str, Workflow] = {}
        
    def create_workflow(self, name: str, steps: List[WorkflowStep], 
                       context: Dict[str, Any]) -> Workflow:
        """Create new workflow"""
        workflow = Workflow(
            id=f"WF-{uuid.uuid4().hex[:8].upper()}",
            name=name,
            status=WorkflowStatus.CREATED,
            steps=steps,
            context=context
        )
        self.workflows[workflow.id] = workflow
        self.state_manager.set(f'workflows.{workflow.id}', asdict(workflow))
        
        logger.info(f"Workflow created: {workflow.id} - {name}")
        return workflow
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Execute workflow with error handling and rollback (Task 3.O.3)"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {'success': False, 'error': 'Workflow not found'}
        
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now()
        completed_steps = []
        
        try:
            for step in workflow.steps:
                logger.info(f"Executing step: {step.name}")
                step.status = "running"
                
                # Execute step handler
                if asyncio.iscoroutinefunction(step.handler):
                    result = await step.handler(workflow.context)
                else:
                    result = step.handler(workflow.context)
                
                step.result = result
                step.status = "completed"
                completed_steps.append(step)
                
                # Update context with result
                workflow.context[f'{step.name}_result'] = result
                
                # Publish step completion event
                self.event_router.publish(Event(
                    id=str(uuid.uuid4()),
                    type='workflow.step.completed',
                    priority=EventPriority.MEDIUM,
                    timestamp=datetime.now(),
                    source='workflow_coordinator',
                    data={
                        'workflow_id': workflow_id,
                        'step': step.name,
                        'result': result
                    }
                ))
            
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()
            
            logger.info(f"Workflow completed: {workflow_id}")
            return {'success': True, 'workflow_id': workflow_id, 'result': workflow.context}
            
        except Exception as e:
            logger.error(f"Workflow error: {e}")
            workflow.status = WorkflowStatus.FAILED
            
            # Rollback completed steps
            rollback_result = await self._rollback_workflow(workflow, completed_steps)
            
            return {
                'success': False,
                'error': str(e),
                'rollback': rollback_result
            }
    
    async def _rollback_workflow(self, workflow: Workflow, 
                                 completed_steps: List[WorkflowStep]) -> Dict:
        """Rollback workflow steps (Task 3.O.3)"""
        logger.info(f"Rolling back workflow: {workflow.id}")
        rollback_results = []
        
        for step in reversed(completed_steps):
            if step.rollback_handler:
                try:
                    if asyncio.iscoroutinefunction(step.rollback_handler):
                        await step.rollback_handler(workflow.context)
                    else:
                        step.rollback_handler(workflow.context)
                    rollback_results.append({
                        'step': step.name,
                        'status': 'rolled_back'
                    })
                except Exception as e:
                    logger.error(f"Rollback failed for {step.name}: {e}")
                    rollback_results.append({
                        'step': step.name,
                        'status': 'rollback_failed',
                        'error': str(e)
                    })
        
        workflow.status = WorkflowStatus.ROLLED_BACK
        return {'rolled_back_steps': rollback_results}

# ============================================================================
# PART 5: VEHICLE MANAGER MODULE (Tasks 1.6-1.11, 2.1-2.9)
# ============================================================================

class VehicleFactory:
    """Factory pattern for vehicle instantiation (Task 2.2)"""
    
    @staticmethod
    def create_vehicle(vehicle_id: str, vehicle_type: VehicleType, 
                      location: Location) -> Vehicle:
        """Create vehicle with type-specific capabilities (Task 2.3-2.5)"""
        
        if vehicle_type == VehicleType.MULTI_ROTOR:
            capabilities = VehicleCapabilities(
                max_speed=15.0,
                max_altitude=400.0,
                max_range=5000.0,
                cruise_speed=10.0,
                endurance=25.0,
                payload_capacity=2.0,
                sensors=['RGB Camera', 'Multispectral', 'LiDAR']
            )
        elif vehicle_type == VehicleType.FIXED_WING:
            capabilities = VehicleCapabilities(
                max_speed=25.0,
                max_altitude=1000.0,
                max_range=50000.0,
                cruise_speed=20.0,
                endurance=90.0,
                payload_capacity=3.0,
                sensors=['RGB Camera', 'Thermal', 'Multispectral']
            )
        elif vehicle_type == VehicleType.VTOL:
            capabilities = VehicleCapabilities(
                max_speed=20.0,
                max_altitude=800.0,
                max_range=30000.0,
                cruise_speed=15.0,
                endurance=60.0,
                payload_capacity=2.5,
                sensors=['RGB Camera', 'Thermal', 'Multispectral', 'LiDAR']
            )
        else:
            capabilities = VehicleCapabilities()
        
        return Vehicle(
            id=vehicle_id,
            type=vehicle_type,
            status=VehicleStatus.IDLE,
            location=location,
            battery=100.0,
            capabilities=capabilities
        )

class VehicleManagerModule:
    """Core vehicle management module (Task 1.6)"""
    
    def __init__(self, state_manager: GlobalStateManager, event_router: EventRouter):
        self.state_manager = state_manager
        self.event_router = event_router
        self.vehicles: Dict[str, Vehicle] = {}
        
        # Subscribe to events
        self.event_router.subscribe('vehicle.*', self._handle_vehicle_event)
        
    def register_vehicle(self, vehicle: Vehicle) -> bool:
        """Register vehicle in distributed registry (Task 1.9)"""
        if vehicle.id in self.vehicles:
            return False
        
        self.vehicles[vehicle.id] = vehicle
        self.state_manager.set(f'vehicles.{vehicle.id}', asdict(vehicle))
        
        # Publish registration event (Task 1.10)
        self.event_router.publish(Event(
            id=str(uuid.uuid4()),
            type='vehicle.registered',
            priority=EventPriority.HIGH,
            timestamp=datetime.now(),
            source='vehicle_manager',
            data={'vehicle_id': vehicle.id, 'type': vehicle.type.value}
        ))
        
        logger.info(f"Vehicle registered: {vehicle.id}")
        return True
    
    def update_status(self, vehicle_id: str, new_status: VehicleStatus):
        """Update vehicle lifecycle state (Task 1.7)"""
        vehicle = self.vehicles.get(vehicle_id)
        if not vehicle:
            return False
        
        old_status = vehicle.status
        vehicle.status = new_status
        vehicle.last_update = datetime.now()
        
        self.state_manager.update(f'vehicles.{vehicle_id}', 
                                 {'status': new_status.value})
        
        # Publish state change event (Task 1.10)
        self.event_router.publish(Event(
            id=str(uuid.uuid4()),
            type='vehicle.status.changed',
            priority=EventPriority.HIGH,
            timestamp=datetime.now(),
            source='vehicle_manager',
            data={
                'vehicle_id': vehicle_id,
                'old_status': old_status.value,
                'new_status': new_status.value
            }
        ))
        
        return True
    
    def update_location(self, vehicle_id: str, location: Location):
        """Update vehicle location (Task 1.10)"""
        vehicle = self.vehicles.get(vehicle_id)
        if not vehicle:
            return False
        
        vehicle.location = location
        vehicle.last_update = datetime.now()
        
        self.state_manager.update(f'vehicles.{vehicle_id}', 
                                 {'location': asdict(location)})
        
        # Publish location update (Task 1.10)
        self.event_router.publish(Event(
            id=str(uuid.uuid4()),
            type='vehicle.location.updated',
            priority=EventPriority.LOW,
            timestamp=datetime.now(),
            source='vehicle_manager',
            data={
                'vehicle_id': vehicle_id,
                'location': asdict(location)
            }
        ))
        
        return True
    
    def get_vehicle(self, vehicle_id: str) -> Optional[Vehicle]:
        """Get vehicle by ID (Task 1.12)"""
        return self.vehicles.get(vehicle_id)
    
    def get_all_vehicles(self) -> List[Vehicle]:
        """Get all vehicles (Task 1.12)"""
        return list(self.vehicles.values())
    
    def _handle_vehicle_event(self, event: Event):
        """Handle vehicle events for fleet aggregation (Task 1.11)"""
        # Aggregate fleet statistics
        stats = self._aggregate_fleet_stats()
        self.state_manager.set('system.fleet_stats', stats)
    
    def _aggregate_fleet_stats(self) -> Dict:
        """Aggregate fleet status (Task 1.11)"""
        stats = {
            'total': len(self.vehicles),
            'by_status': defaultdict(int),
            'by_type': defaultdict(int),
            'average_battery': 0.0,
            'active_missions': 0
        }
        
        total_battery = 0.0
        for vehicle in self.vehicles.values():
            stats['by_status'][vehicle.status.value] += 1
            stats['by_type'][vehicle.type.value] += 1
            total_battery += vehicle.battery
            if vehicle.mission_id:
                stats['active_missions'] += 1
        
        if self.vehicles:
            stats['average_battery'] = total_battery / len(self.vehicles)
        
        return dict(stats)

# ============================================================================
# PART 6: GEOFENCING ENGINE (Tasks 5.1-5.21, 6.1-6.32)
# ============================================================================

class GeofencingEngine:
    """Advanced geofencing with spatial algorithms"""
    
    def __init__(self, state_manager: GlobalStateManager, event_router: EventRouter):
        self.state_manager = state_manager
        self.event_router = event_router
        self.zones: Dict[str, Geofence] = {}
        self.spatial_index = {}  # R-Tree simulation (Task 6.1)
        self.zone_cache = {}  # LRU cache (Task 6.10)
        self.cache_size = 100
        
    def add_zone(self, geofence: Geofence) -> bool:
        """Add geofence zone (Task 5.19)"""
        if not self._validate_polygon(geofence.polygon):
            return False
        
        self.zones[geofence.id] = geofence
        self.state_manager.set(f'geofences.{geofence.id}', asdict(geofence))
        self._update_spatial_index(geofence)
        
        logger.info(f"Geofence added: {geofence.id}")
        return True
    
    def _validate_polygon(self, polygon: List[Location]) -> bool:
        """Validate polygon geometry (Task 5.11-5.14)"""
        if len(polygon) < 3:
            return False
        
        # Coordinate validation (Task 5.12)
        for point in polygon:
            if not (-90 <= point.lat <= 90 and -180 <= point.lon <= 180):
                return False
        
        # Check if closed (Task 5.11)
        if (polygon[0].lat != polygon[-1].lat or 
            polygon[0].lon != polygon[-1].lon):
            polygon.append(polygon[0])
        
        # Check for self-intersections (simplified - Task 5.11)
        # In production, use Shapely library for robust validation
        
        return True
    
    def point_in_polygon(self, point: Location, polygon: List[Location]) -> bool:
        """Ray casting algorithm (Task 5.1)"""
        x, y = point.lon, point.lat
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0].lon, polygon[0].lat
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n].lon, polygon[i % n].lat
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def haversine_distance(self, loc1: Location, loc2: Location) -> float:
        """Great circle distance (Task 5.3)"""
        R = 6371000  # Earth radius in meters
        
        lat1, lon1 = math.radians(loc1.lat), math.radians(loc1.lon)
        lat2, lon2 = math.radians(loc2.lat), math.radians(loc2.lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def check_breach(self, vehicle_location: Location, 
                    vehicle_id: str = None) -> List[Dict[str, Any]]:
        """Check for geofence breaches with graduated severity (Task 6.13-6.17)"""
        breaches = []
        
        for zone_id, zone in self.zones.items():
            if not zone.active:
                continue
            
            # Altitude bounds check (Task 5.13)
            if not (zone.min_altitude <= vehicle_location.alt <= zone.max_altitude):
                continue
            
            is_inside = self.point_in_polygon(vehicle_location, zone.polygon)
            
            # Determine breach type (Task 6.13-6.14)
            breach = None
            if zone.type == "keep-out" and is_inside:
                breach = {
                    'zone_id': zone_id,
                    'zone_name': zone.name,
                    'type': 'entry_breach',
                    'severity': 'critical',
                    'action': 'RTL',
                    'priority': zone.priority
                }
            elif zone.type == "keep-in" and not is_inside:
                breach = {
                    'zone_id': zone_id,
                    'zone_name': zone.name,
                    'type': 'exit_breach',
                    'severity': 'critical',
                    'action': 'RTL',
                    'priority': zone.priority
                }
            elif zone.type == "warning" and is_inside:
                # Check proximity to boundary (Task 6.15)
                distance_to_boundary = self._distance_to_boundary(
                    vehicle_location, zone.polygon
                )
                
                if distance_to_boundary < 50:  # 50m proximity warning
                    breach = {
                        'zone_id': zone_id,
                        'zone_name': zone.name,
                        'type': 'proximity_warning',
                        'severity': 'warning',
                        'action': 'alert',
                        'distance': distance_to_boundary,
                        'priority': zone.priority
                    }
            
            if breach:
                breaches.append(breach)
                
                # Publish breach event (Task 6.18)
                self.event_router.publish(Event(
                    id=str(uuid.uuid4()),
                    type='geofence.breach',
                    priority=EventPriority.CRITICAL,
                    timestamp=datetime.now(),
                    source='geofencing_engine',
                    data=breach
                ))
        
        return breaches
    
    def _distance_to_boundary(self, point: Location, 
                             polygon: List[Location]) -> float:
        """Calculate nearest point on boundary (Task 5.5)"""
        min_distance = float('inf')
        
        for i in range(len(polygon) - 1):
            p1, p2 = polygon[i], polygon[i + 1]
            distance = self._point_to_segment_distance(point, p1, p2)
            min_distance = min(min_distance, distance)
        
        return min_distance
    
    def _point_to_segment_distance(self, point: Location, 
                                   p1: Location, p2: Location) -> float:
        """Distance from point to line segment"""
        # Simplified implementation - use haversine for actual points
        return self.haversine_distance(point, p1)
    
    def _update_spatial_index(self, geofence: Geofence):
        """Update R-Tree spatial index (Task 6.1)"""
        lats = [p.lat for p in geofence.polygon]
        lons = [p.lon for p in geofence.polygon]
        
        bbox = {
            'min_lat': min(lats),
            'max_lat': max(lats),
            'min_lon': min(lons),
            'max_lon': max(lons),
            'geofence_id': geofence.id
        }
        
        self.spatial_index[geofence.id] = bbox

# ============================================================================
# PART 7: MISSION PLANNER (Tasks 4.1-4.15)
# ============================================================================

class MissionPlanner:
    """Mission planning with multiple planner types"""
    
    def __init__(self, geofencing: GeofencingEngine):
        self.geofencing = geofencing
    
    def create_survey_mission(self, aoi_polygon: List[Location], 
                             grid_spacing: float = 50,
                             altitude: float = 100,
                             overlap: float = 0.7) -> Mission:
        """Survey planner with grid coverage (Task 4.2-4.3)"""
        waypoints = self._generate_grid_pattern(
            aoi_polygon, grid_spacing, altitude, overlap
        )
        
        # Calculate mission statistics (Task 4.15)
        total_distance = self._calculate_path_distance(waypoints)
        coverage_area = self._calculate_area(aoi_polygon)
        estimated_time = self._estimate_flight_time(total_distance, 10.0)
        
        mission = Mission(
            id=f"M-{uuid.uuid4().hex[:8].upper()}",
            name="Survey Mission",
            type=MissionType.SURVEY,
            status=MissionStatus.CREATED,
            waypoints=waypoints,
            metadata={
                'grid_spacing': grid_spacing,
                'coverage_area': coverage_area,
                'total_distance': total_distance,
                'estimated_time': estimated_time,
                'waypoint_count': len(waypoints),
                'overlap': overlap
            }
        )
        
        logger.info(f"Survey mission created: {mission.id} with {len(waypoints)} waypoints")
        return mission
    
    def create_corridor_mission(self, start: Location, end: Location,
                               width: float = 100, altitude: float = 100,
                               segments: int = 3) -> Mission:
        """Corridor planner for linear surveys (Task 4.4-4.5)"""
        waypoints = self._generate_corridor_pattern(
            start, end, width, altitude, segments
        )
        
        distance = self.geofencing.haversine_distance(start, end)
        estimated_time = self._estimate_flight_time(distance, 15.0)
        
        mission = Mission(
            id=f"M-{uuid.uuid4().hex[:8].upper()}",
            name="Corridor Mission",
            type=MissionType.CORRIDOR,
            status=MissionStatus.CREATED,
            waypoints=waypoints,
            metadata={
                'corridor_width': width,
                'distance': distance,
                'estimated_time': estimated_time,
                'segments': segments
            }
        )
        
        logger.info(f"Corridor mission created: {mission.id}")
        return mission
    
    def create_structure_scan(self, center: Location, radius: float = 50,
                             altitude_min: float = 30, altitude_max: float = 70,
                             orbits: int = 3, points_per_orbit: int = 24) -> Mission:
        """Structure scan with 3D orbit (Task 4.6-4.7)"""
        waypoints = []
        
        altitude_step = (altitude_max - altitude_min) / (orbits - 1) if orbits > 1 else 0
        
        for orbit in range(orbits):
            orbit_altitude = altitude_min + (orbit * altitude_step)
            
            for angle_step in range(points_per_orbit):
                angle = (360 / points_per_orbit) * angle_step
                rad_angle = math.radians(angle)
                
                # Calculate point on circle (Task 4.7)
                lat_offset = (radius / 111320) * math.cos(rad_angle)
                lon_offset = (radius / (111320 * math.cos(math.radians(center.lat)))) * math.sin(rad_angle)
                
                waypoints.append(Waypoint(
                    lat=center.lat + lat_offset,
                    lon=center.lon + lon_offset,
                    alt=orbit_altitude,
                    command="WAYPOINT",
                    sequence=len(waypoints)
                ))
        
        mission = Mission(
            id=f"M-{uuid.uuid4().hex[:8].upper()}",
            name="Structure Scan",
            type=MissionType.STRUCTURE_SCAN,
            status=MissionStatus.CREATED,
            waypoints=waypoints,
            metadata={
                'orbits': orbits,
                'radius': radius,
                'altitude_range': [altitude_min, altitude_max],
                'points_per_orbit': points_per_orbit
            }
        )
        
        logger.info(f"Structure scan created: {mission.id} with {len(waypoints)} waypoints")
        return mission
    
    def validate_mission(self, mission: Mission, vehicle: Vehicle) -> Dict[str, Any]:
        """Validate mission against vehicle and geofences (Task 4.11-4.13)"""
        issues = []
        warnings = []
        
        # 1. Flight envelope compliance (Task 4.11)
        for wp in mission.waypoints:
            if wp.alt > vehicle.capabilities.max_altitude:
                issues.append(
                    f"Waypoint {wp.sequence} exceeds max altitude: "
                    f"{wp.alt}m > {vehicle.capabilities.max_altitude}m"
                )
        
        # 2. Battery/range check (Task 4.12)
        total_distance = self._calculate_path_distance(mission.waypoints)
        required_battery = (total_distance / vehicle.capabilities.max_range) * 100
        
        if vehicle.battery < required_battery * 1.2:  # 20% safety margin
            issues.append(
                f"Insufficient battery: {vehicle.battery:.1f}% < "
                f"{required_battery * 1.2:.1f}% required"
            )
        
        # 3. Geofence compliance (Task 4.13)
        for wp in mission.waypoints:
            breaches = self.geofencing.check_breach(
                Location(wp.lat, wp.lon, wp.alt)
            )
            for breach in breaches:
                if breach['severity'] == 'critical':
                    issues.append(
                        f"Waypoint {wp.sequence} violates geofence: "
                        f"{breach['zone_name']}"
                    )
                else:
                    warnings.append(
                        f"Waypoint {wp.sequence} in warning zone: "
                        f"{breach['zone_name']}"
                    )
        
        # 4. Sensor bounds (Task 4.13)
        # Check if vehicle has required sensors
        required_sensors = mission.metadata.get('required_sensors', [])
        for sensor in required_sensors:
            if sensor not in vehicle.capabilities.sensors:
                warnings.append(f"Vehicle lacks required sensor: {sensor}")
        
        validation_result = {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'total_distance': total_distance,
            'required_battery': required_battery,
            'estimated_time': self._estimate_flight_time(
                total_distance, 
                vehicle.capabilities.cruise_speed
            )
        }
        
        return validation_result
    
    def _generate_grid_pattern(self, polygon: List[Location], spacing: float,
                               altitude: float, overlap: float) -> List[Waypoint]:
        """Generate grid waypoints (Task 4.3)"""
        waypoints = []
        
        lats = [p.lat for p in polygon]
        lons = [p.lon for p in polygon]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        # Account for overlap in spacing
        effective_spacing = spacing * (1 - overlap)
        
        lat_spacing = effective_spacing / 111320
        lon_spacing = effective_spacing / (111320 * math.cos(math.radians((min_lat + max_lat) / 2)))
        
        current_lat = min_lat
        line_num = 0
        sequence = 0
        
        while current_lat < max_lat:
            if line_num % 2 == 0:
                current_lon = min_lon
                while current_lon < max_lon:
                    waypoints.append(Waypoint(
                        current_lat, current_lon, altitude,
                        sequence=sequence
                    ))
                    current_lon += lon_spacing
                    sequence += 1
            else:
                current_lon = max_lon
                while current_lon > min_lon:
                    waypoints.append(Waypoint(
                        current_lat, current_lon, altitude,
                        sequence=sequence
                    ))
                    current_lon -= lon_spacing
                    sequence += 1
            
            current_lat += lat_spacing
            line_num += 1
        
        return waypoints
    
    def _generate_corridor_pattern(self, start: Location, end: Location,
                                   width: float, altitude: float, 
                                   segments: int) -> List[Waypoint]:
        """Generate corridor waypoints (Task 4.5)"""
        waypoints = []
        bearing = self._calculate_bearing(start, end)
        
        # Create parallel lines at different offsets
        offsets = [-width/2, 0, width/2]
        
        for offset in offsets:
            # Calculate perpendicular offset
            perp_bearing = bearing + 90
            lat_offset = (offset / 111320) * math.cos(math.radians(perp_bearing))
            lon_offset = (offset / (111320 * math.cos(math.radians(start.lat)))) * math.sin(math.radians(perp_bearing))
            
            # Add start point with offset
            waypoints.append(Waypoint(
                lat=start.lat + lat_offset,
                lon=start.lon + lon_offset,
                alt=altitude,
                sequence=len(waypoints)
            ))
            
            # Add end point with offset
            waypoints.append(Waypoint(
                lat=end.lat + lat_offset,
                lon=end.lon + lon_offset,
                alt=altitude,
                sequence=len(waypoints)
            ))
        
        return waypoints
    
    def _calculate_bearing(self, loc1: Location, loc2: Location) -> float:
        """Calculate bearing (Task 5.8)"""
        lat1, lon1 = math.radians(loc1.lat), math.radians(loc1.lon)
        lat2, lon2 = math.radians(loc2.lat), math.radians(loc2.lon)
        
        dlon = lon2 - lon1
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        bearing = math.atan2(y, x)
        return math.degrees(bearing)
    
    def _calculate_area(self, polygon: List[Location]) -> float:
        """Calculate polygon area (Task 5.7)"""
        area = 0.0
        n = len(polygon)
        
        for i in range(n):
            j = (i + 1) % n
            area += polygon[i].lon * polygon[j].lat
            area -= polygon[j].lon * polygon[i].lat
        
        area = abs(area) / 2.0
        return area * 111320 * 111320
    
    def _calculate_path_distance(self, waypoints: List[Waypoint]) -> float:
        """Calculate total path distance (Task 4.15)"""
        total = 0.0
        for i in range(len(waypoints) - 1):
            wp1 = Location(waypoints[i].lat, waypoints[i].lon, waypoints[i].alt)
            wp2 = Location(waypoints[i+1].lat, waypoints[i+1].lon, waypoints[i+1].alt)
            total += self.geofencing.haversine_distance(wp1, wp2)
        return total
    
    def _estimate_flight_time(self, distance: float, speed: float) -> float:
        """Estimate flight time in seconds (Task 4.15)"""
        return distance / speed

# ============================================================================
# PART 8: ORCHESTRATOR ENGINE (Tasks 1.O.1-6.O.4)
# ============================================================================

class OrchestratorEngine:
    """Central orchestration engine (Task 1.O.1)"""
    
    def __init__(self):
        self.status = "stopped"
        self.start_time = None
        
        # Initialize subsystems
        self.state_manager = GlobalStateManager()
        self.event_router = EventRouter()
        self.workflow_coordinator = WorkflowCoordinator(
            self.state_manager, 
            self.event_router
        )
        self.vehicle_manager = VehicleManagerModule(
            self.state_manager, 
            self.event_router
        )
        self.geofencing = GeofencingEngine(
            self.state_manager,
            self.event_router
        )
        self.mission_planner = MissionPlanner(self.geofencing)
        
        self.missions: Dict[str, Mission] = {}
        
        # Setup event subscriptions
        self._setup_event_handlers()
        
    def _setup_event_handlers(self):
        """Setup orchestrator event handlers"""
        self.event_router.subscribe('*', self._handle_any_event)
        self.event_router.subscribe('geofence.breach', self._handle_breach)
        self.event_router.subscribe('mission.*', self._handle_mission_event)
        
    def start(self):
        """Start orchestrator (Task 1.O.1)"""
        self.status = "running"
        self.start_time = datetime.now()
        self.event_router.start()
        self.state_manager.set('system.status', 'running')
        self.state_manager.set('system.start_time', str(self.start_time))
        
        logger.info("🚀 Orchestrator Engine Started")
        
        # Publish system start event
        self.event_router.publish(Event(
            id=str(uuid.uuid4()),
            type='system.started',
            priority=EventPriority.HIGH,
            timestamp=datetime.now(),
            source='orchestrator',
            data={'status': 'running'}
        ))
    
    def stop(self):
        """Stop orchestrator"""
        self.status = "stopped"
        self.event_router.stop()
        self.state_manager.set('system.status', 'stopped')
        
        logger.info("🛑 Orchestrator Engine Stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        fleet_stats = self.vehicle_manager._aggregate_fleet_stats()
        
        return {
            'status': self.status,
            'uptime': f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
            'uptime_seconds': uptime,
            'events_processed': len(self.event_router.event_history),
            'active_workflows': len([
                w for w in self.workflow_coordinator.workflows.values() 
                if w.status == WorkflowStatus.RUNNING
            ]),
            'vehicles': fleet_stats['total'],
            'missions': len(self.missions),
            'geofences': len(self.geofencing.zones),
            'fleet_stats': fleet_stats
        }
    
    async def execute_mission_workflow(self, mission_id: str, 
                                       vehicle_id: str) -> Dict[str, Any]:
        """Execute complete mission workflow (Task 3.O.1, 4.O.4)"""
        
        # Define workflow steps
        steps = [
            WorkflowStep(
                name='validate_mission',
                handler=lambda ctx: self._validate_mission_step(ctx),
                rollback_handler=lambda ctx: self._rollback_validation(ctx)
            ),
            WorkflowStep(
                name='assign_vehicle',
                handler=lambda ctx: self._assign_vehicle_step(ctx),
                rollback_handler=lambda ctx: self._rollback_assignment(ctx)
            ),
            WorkflowStep(
                name='check_geofences',
                handler=lambda ctx: self._check_geofences_step(ctx)
            ),
            WorkflowStep(
                name='arm_vehicle',
                handler=lambda ctx: self._arm_vehicle_step(ctx),
                rollback_handler=lambda ctx: self._disarm_vehicle_step(ctx)
            ),
            WorkflowStep(
                name='execute_mission',
                handler=lambda ctx: self._execute_mission_step(ctx),
                rollback_handler=lambda ctx: self._abort_mission_step(ctx)
            ),
            WorkflowStep(
                name='monitor_progress',
                handler=lambda ctx: self._monitor_progress_step(ctx)
            )
        ]
        
        # Create workflow
        workflow = self.workflow_coordinator.create_workflow(
            name='mission_execution',
            steps=steps,
            context={
                'mission_id': mission_id,
                'vehicle_id': vehicle_id,
                'start_time': datetime.now()
            }
        )
        
        # Execute workflow
        result = await self.workflow_coordinator.execute_workflow(workflow.id)
        
        return result
    
    def _validate_mission_step(self, context: Dict) -> Dict:
        """Validate mission workflow step (Task 4.O.3)"""
        mission = self.missions.get(context['mission_id'])
        vehicle = self.vehicle_manager.get_vehicle(context['vehicle_id'])
        
        if not mission or not vehicle:
            raise Exception("Mission or vehicle not found")
        
        validation = self.mission_planner.validate_mission(mission, vehicle)
        
        if not validation['valid']:
            raise Exception(f"Validation failed: {validation['issues']}")
        
        mission.status = MissionStatus.VALIDATED
        return validation
    
    def _assign_vehicle_step(self, context: Dict) -> Dict:
        """Assign vehicle to mission (Task 3.O.1)"""
        mission = self.missions[context['mission_id']]
        vehicle = self.vehicle_manager.get_vehicle(context['vehicle_id'])
        
        mission.vehicle_id = vehicle.id
        vehicle.mission_id = mission.id
        
        self.state_manager.update(f'missions.{mission.id}', 
                                 {'vehicle_id': vehicle.id})
        
        return {'assigned': True}
    
    def _check_geofences_step(self, context: Dict) -> Dict:
        """Check geofence compliance (Task 5.O.1)"""
        mission = self.missions[context['mission_id']]
        
        violations = []
        for wp in mission.waypoints:
            breaches = self.geofencing.check_breach(
                Location(wp.lat, wp.lon, wp.alt)
            )
            if breaches:
                violations.extend(breaches)
        
        if violations:
            logger.warning(f"Geofence warnings detected: {len(violations)}")
        
        return {'violations': violations}
    
    def _arm_vehicle_step(self, context: Dict) -> Dict:
        """Arm vehicle (Task 2.O.1)"""
        vehicle_id = context['vehicle_id']
        self.vehicle_manager.update_status(vehicle_id, VehicleStatus.ARMED)
        
        logger.info(f"Vehicle {vehicle_id} armed")
        return {'armed': True}
    
    def _execute_mission_step(self, context: Dict) -> Dict:
        """Execute mission (Task 4.O.4)"""
        mission = self.missions[context['mission_id']]
        vehicle_id = context['vehicle_id']
        
        mission.status = MissionStatus.EXECUTING
        mission.started_at = datetime.now()
        
        self.vehicle_manager.update_status(vehicle_id, VehicleStatus.FLYING)
        
        logger.info(f"Mission {mission.id} execution started")
        return {'executing': True}
    
    def _monitor_progress_step(self, context: Dict) -> Dict:
        """Monitor mission progress (Task 4.O.4)"""
        mission = self.missions[context['mission_id']]
        
        # This would be continuously updated in production
        mission.progress = 0.0
        
        return {'monitoring': True}
    
    def _rollback_validation(self, context: Dict):
        """Rollback validation"""
        mission = self.missions.get(context['mission_id'])
        if mission:
            mission.status = MissionStatus.PLANNED
    
    def _rollback_assignment(self, context: Dict):
        """Rollback vehicle assignment"""
        mission = self.missions.get(context['mission_id'])
        vehicle = self.vehicle_manager.get_vehicle(context['vehicle_id'])
        
        if mission:
            mission.vehicle_id = None
        if vehicle:
            vehicle.mission_id = None
    
    def _disarm_vehicle_step(self, context: Dict):
        """Disarm vehicle"""
        vehicle_id = context['vehicle_id']
        self.vehicle_manager.update_status(vehicle_id, VehicleStatus.IDLE)
    
    def _abort_mission_step(self, context: Dict):
        """Abort mission"""
        mission = self.missions.get(context['mission_id'])
        vehicle_id = context['vehicle_id']
        
        if mission:
            mission.status = MissionStatus.FAILED
        
        self.vehicle_manager.update_status(vehicle_id, VehicleStatus.EMERGENCY)
        logger.warning(f"Mission {mission.id} aborted")
    
    def _handle_any_event(self, event: Event):
        """Handle all events for logging"""
        self.state_manager.update('system', 
                                 {'event_count': len(self.event_router.event_history)})
    
    def _handle_breach(self, event: Event):
        """Handle geofence breach (Task 6.O.1)"""
        breach_data = event.data
        
        if breach_data['severity'] == 'critical':
            # Trigger emergency response workflow
            logger.critical(f"CRITICAL BREACH: {breach_data['zone_name']}")
            
            # Would trigger RTL workflow here
            # self.execute_rtl_workflow(vehicle_id)
    
    def _handle_mission_event(self, event: Event):
        """Handle mission events"""
        mission_id = event.data.get('mission_id')
        if mission_id and mission_id in self.missions:
            mission = self.missions[mission_id]
            logger.info(f"Mission event: {event.type} for {mission.name}")

# ============================================================================
# PART 9: CLI INTERFACE (Tasks 1.C.1-6.C.3)
# ============================================================================

class CLI:
    """Command Line Interface"""
    
    def __init__(self, orchestrator: OrchestratorEngine):
        self.orchestrator = orchestrator
        self.commands = {
            'orchestrator': self._orchestrator_cmd,
            'vehicle': self._vehicle_cmd,
            'mission': self._mission_cmd,
            'geofence': self._geofence_cmd,
            'workflow': self._workflow_cmd,
            'status': self._status_cmd,
            'help': self._help_cmd
        }
    
    def run(self, args: List[str]):
        """Run CLI command"""
        if not args:
            self._help_cmd([])
            return
        
        command = args[0]
        if command in self.commands:
            self.commands[command](args[1:])
        else:
            print(f"❌ Unknown command: {command}")
            self._help_cmd([])
    
    def _orchestrator_cmd(self, args: List[str]):
        """Orchestrator commands (Task 1.C.3)"""
        if not args:
            print("Usage: orchestrator [start|stop|status|health]")
            return
        
        action = args[0]
        
        if action == 'start':
            self.orchestrator.start()
            print("✅ Orchestrator started")
        elif action == 'stop':
            self.orchestrator.stop()
            print("✅ Orchestrator stopped")
        elif action in ['status', 'health']:
            status = self.orchestrator.get_status()
            print(f"\n{'='*60}")
            print(f"ORCHESTRATOR STATUS")
            print(f"{'='*60}")
            print(f"Status: {status['status'].upper()}")
            print(f"Uptime: {status['uptime']}")
            print(f"Events Processed: {status['events_processed']}")
            print(f"Active Workflows: {status['active_workflows']}")
            print(f"\nFleet:")
            print(f"  Total Vehicles: {status['vehicles']}")
            print(f"  Active Missions: {status['fleet_stats']['active_missions']}")
            print(f"  Average Battery: {status['fleet_stats']['average_battery']:.1f}%")
            print(f"\nResources:")
            print(f"  Missions: {status['missions']}")
            print(f"  Geofences: {status['geofences']}")
            print(f"{'='*60}\n")
    
    def _vehicle_cmd(self, args: List[str]):
        """Vehicle commands (Task 2.C.1)"""
        if not args:
            print("Usage: vehicle [register|list|status|update|stream]")
            return
        
        action = args[0]
        
        if action == 'list':
            vehicles = self.orchestrator.vehicle_manager.get_all_vehicles()
            print(f"\n{'='*90}")
            print(f"{'ID':<12} {'Type':<15} {'Status':<12} {'Battery':<10} {'Mission':<15} {'Location'}")
            print(f"{'='*90}")
            for v in vehicles:
                loc_str = f"({v.location.lat:.4f}, {v.location.lon:.4f})"
                print(f"{v.id:<12} {v.type.value:<15} {v.status.value:<12} "
                      f"{v.battery:<10.1f}% {v.mission_id or 'None':<15} {loc_str}")
            print(f"{'='*90}\n")
        
        elif action == 'register':
            vehicle_id = input("Vehicle ID: ")
            vehicle_type = input("Type (multi-rotor/fixed-wing/vtol): ")
            lat = float(input("Latitude: "))
            lon = float(input("Longitude: "))
            
            vehicle = VehicleFactory.create_vehicle(
                vehicle_id,
                VehicleType(vehicle_type),
                Location(lat, lon, 0)
            )
            
            if self.orchestrator.vehicle_manager.register_vehicle(vehicle):
                print(f"✅ Vehicle {vehicle_id} registered")
            else:
                print(f"❌ Vehicle {vehicle_id} already exists")
    
    def _mission_cmd(self, args: List[str]):
        """Mission commands (Task 3.C.1)"""
        if not args:
            print("Usage: mission [create|list|execute|monitor|validate]")
            return
        
        action = args[0]
        
        if action == 'list':
            missions = list(self.orchestrator.missions.values())
            print(f"\n{'='*100}")
            print(f"{'ID':<12} {'Name':<25} {'Type':<12} {'Status':<12} {'Vehicle':<12} {'Progress'}")
            print(f"{'='*100}")
            for m in missions:
                print(f"{m.id:<12} {m.name:<25} {m.type.value:<12} "
                      f"{m.status.value:<12} {m.vehicle_id or 'None':<12} {m.progress:.1f}%")
            print(f"{'='*100}\n")
        
        elif action == 'execute':
            if len(args) < 3:
                print("Usage: mission execute <mission_id> <vehicle_id>")
                return
            
            mission_id = args[1]
            vehicle_id = args[2]
            
            print(f"Executing mission {mission_id} with vehicle {vehicle_id}...")
            
            # Run async workflow
            import asyncio
            result = asyncio.run(
                self.orchestrator.execute_mission_workflow(mission_id, vehicle_id)
            )
            
            if result['success']:
                print(f"✅ Mission execution started")
            else:
                print(f"❌ Mission execution failed: {result.get('error')}")
    
    def _geofence_cmd(self, args: List[str]):
        """Geofence commands (Task 5.C.1)"""
        if not args:
            print("Usage: geofence [add|list|check|validate]")
            return
        
        action = args[0]
        
        if action == 'list':
            zones = self.orchestrator.geofencing.zones.values()
            print(f"\n{'='*80}")
            print(f"{'ID':<12} {'Name':<30} {'Type':<12} {'Active':<8} {'Priority'}")
            print(f"{'='*80}")
            for z in zones:
                print(f"{z.id:<12} {z.name:<30} {z.type:<12} "
                      f"{'Yes' if z.active else 'No':<8} {z.priority}")
            print(f"{'='*80}\n")
    
    def _workflow_cmd(self, args: List[str]):
        """Workflow commands (Task 3.C.2)"""
        if not args:
            print("Usage: workflow [list|status|history]")
            return
        
        action = args[0]
        
        if action == 'list':
            workflows = self.orchestrator.workflow_coordinator.workflows.values()
            print(f"\n{'='*90}")
            print(f"{'ID':<15} {'Name':<25} {'Status':<15} {'Steps':<10} {'Created'}")
            print(f"{'='*90}")
            for w in workflows:
                created = w.created_at.strftime("%Y-%m-%d %H:%M")
                print(f"{w.id:<15} {w.name:<25} {w.status.value:<15} "
                      f"{len(w.steps):<10} {created}")
            print(f"{'='*90}\n")
    
    def _status_cmd(self, args: List[str]):
        """Overall system status"""
        status = self.orchestrator.get_status()
        
        print(f"\n{'='*60}")
        print("GROUND CONTROLLER MISSION CONTROL SYSTEM")
        print(f"{'='*60}")
        print(f"Orchestrator: {status['status'].upper()}")
        print(f"Uptime: {status['uptime']}")
        print(f"Events: {status['events_processed']}")
        print(f"Workflows: {status['active_workflows']}")
        print(f"\nFleet: {status['vehicles']} vehicles")
        print(f"  Flying: {status['fleet_stats']['by_status'].get('flying', 0)}")
        print(f"  Armed: {status['fleet_stats']['by_status'].get('armed', 0)}")
        print(f"  Idle: {status['fleet_stats']['by_status'].get('idle', 0)}")
        print(f"  Avg Battery: {status['fleet_stats']['average_battery']:.1f}%")
        print(f"\nMissions: {status['missions']}")
        print(f"Geofences: {status['geofences']}")
        print(f"{'='*60}\n")
    
    def _help_cmd(self, args: List[str]):
        """Show help"""
        print("\n" + "="*70)
        print("Ground Controller Mission Control System - Orchestrator CLI")
        print("="*70)
        print("\nCommands:")
        print("  orchestrator  - Control orchestrator (start|stop|status|health)")
        print("  vehicle       - Manage vehicles (register|list|status|update)")
        print("  mission       - Manage missions (create|list|execute|monitor)")
        print("  geofence      - Manage geofences (add|list|check|validate)")
        print("  workflow      - View workflows (list|status|history)")
        print("  status        - Show system status")
        print("  help          - Show this help")
        print("="*70 + "\n")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import sys
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║  Ground Controller Mission Control System                    ║
    ║  Orchestrator-Based Architecture v2.0                        ║
    ║  Task-Mapped Implementation                                  ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize orchestrator
    orchestrator = OrchestratorEngine()
    orchestrator.start()
    
    # Add sample data
    sample_vehicle = VehicleFactory.create_vehicle(
        "V001",
        VehicleType.MULTI_ROTOR,
        Location(37.7749, -122.4194, 0)
    )
    orchestrator.vehicle_manager.register_vehicle(sample_vehicle)
    
    # Add sample geofence
    sample_geofence = Geofence(
        id="GF001",
        name="Test Keep-Out Zone",
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
    
    # Initialize CLI
    cli = CLI(orchestrator)
    
    # Run CLI
    if len(sys.argv) > 1:
        cli.run(sys.argv[1:])
    else:
        print("\n📋 Type 'help' for commands, 'exit' to quit\n")
        
        while True:
            try:
                command = input("GCS> ").strip()
                
                if command.lower() in ['exit', 'quit']:
                    orchestrator.stop()
                    print("👋 Goodbye!")
                    break
                
                if command:
                    cli.run(command.split())
                    
            except KeyboardInterrupt:
                orchestrator.stop()
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                logger.exception("CLI error")