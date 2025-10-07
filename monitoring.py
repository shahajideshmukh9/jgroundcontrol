# Monitoring & Metrics Dashboard (Task 6.O.3, 6.O.4)
# File: monitoring.py

"""
Health monitoring, metrics collection, and dashboard for orchestrator
Complete implementation with health checks, metrics, and recovery
"""

import time
import psutil
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from collections import deque, defaultdict
from dataclasses import dataclass, field, asdict
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# METRICS MODELS
# ============================================================================

@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)

@dataclass
class HealthCheck:
    """Health check result"""
    component: str
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    details: Dict = field(default_factory=dict)
    latency_ms: Optional[float] = None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'component': self.component,
            'status': self.status,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details,
            'latency_ms': self.latency_ms
        }

# ============================================================================
# METRICS COLLECTOR (Task 6.O.3, 6.O.4)
# ============================================================================

class MetricsCollector:
    """Collect and aggregate system metrics"""
    
    def __init__(self, retention_minutes: int = 60):
        """
        Initialize metrics collector
        
        Args:
            retention_minutes: How long to retain metric data
        """
        self.retention_minutes = retention_minutes
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()
        
        logger.info(f"Metrics collector initialized (retention: {retention_minutes}m)")
    
    def record_counter(self, name: str, value: int = 1, labels: Dict = None):
        """
        Record counter metric (monotonically increasing)
        
        Args:
            name: Metric name
            value: Value to add (default 1)
            labels: Optional labels for grouping
        """
        with self.lock:
            key = self._make_key(name, labels)
            self.counters[key] += value
            
            # Also store as time series
            self.metrics[key].append(MetricPoint(
                timestamp=datetime.now(),
                value=self.counters[key],
                labels=labels or {}
            ))
    
    def record_gauge(self, name: str, value: float, labels: Dict = None):
        """
        Record gauge metric (current value that can go up or down)
        
        Args:
            name: Metric name
            value: Current value
            labels: Optional labels for grouping
        """
        with self.lock:
            key = self._make_key(name, labels)
            self.gauges[key] = value
            
            self.metrics[key].append(MetricPoint(
                timestamp=datetime.now(),
                value=value,
                labels=labels or {}
            ))
    
    def record_histogram(self, name: str, value: float, labels: Dict = None):
        """
        Record histogram metric (for distributions - latencies, sizes, etc.)
        
        Args:
            name: Metric name
            value: Observed value
            labels: Optional labels for grouping
        """
        with self.lock:
            key = self._make_key(name, labels)
            self.histograms[key].append(value)
            
            # Keep last 1000 values
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
            
            self.metrics[key].append(MetricPoint(
                timestamp=datetime.now(),
                value=value,
                labels=labels or {}
            ))
    
    def get_metric(self, name: str, labels: Dict = None) -> List[MetricPoint]:
        """
        Get metric time series
        
        Args:
            name: Metric name
            labels: Optional labels filter
            
        Returns:
            List of metric points within retention period
        """
        key = self._make_key(name, labels)
        
        with self.lock:
            # Filter by retention period
            cutoff = datetime.now() - timedelta(minutes=self.retention_minutes)
            return [
                point for point in self.metrics[key]
                if point.timestamp > cutoff
            ]
    
    def get_counter(self, name: str, labels: Dict = None) -> int:
        """Get current counter value"""
        key = self._make_key(name, labels)
        return self.counters.get(key, 0)
    
    def get_gauge(self, name: str, labels: Dict = None) -> float:
        """Get current gauge value"""
        key = self._make_key(name, labels)
        return self.gauges.get(key, 0.0)
    
    def get_histogram_stats(self, name: str, labels: Dict = None) -> Dict:
        """
        Get histogram statistics (min, max, mean, median, percentiles)
        
        Args:
            name: Metric name
            labels: Optional labels filter
            
        Returns:
            Dictionary with statistical values
        """
        key = self._make_key(name, labels)
        values = self.histograms.get(key, [])
        
        if not values:
            return {
                'count': 0,
                'min': 0,
                'max': 0,
                'mean': 0,
                'median': 0,
                'p50': 0,
                'p95': 0,
                'p99': 0
            }
        
        sorted_values = sorted(values)
        count = len(sorted_values)
        
        return {
            'count': count,
            'min': sorted_values[0],
            'max': sorted_values[-1],
            'mean': statistics.mean(sorted_values),
            'median': statistics.median(sorted_values),
            'p50': sorted_values[count // 2],
            'p95': sorted_values[int(count * 0.95)] if count > 20 else sorted_values[-1],
            'p99': sorted_values[int(count * 0.99)] if count > 100 else sorted_values[-1]
        }
    
    def _make_key(self, name: str, labels: Dict = None) -> str:
        """
        Create metric key from name and labels
        
        Args:
            name: Metric name
            labels: Optional labels
            
        Returns:
            Formatted key string
        """
        if not labels:
            return name
        
        label_str = ','.join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_all_metrics(self) -> Dict:
        """Get all metrics summary"""
        with self.lock:
            return {
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'histograms': {
                    name: self.get_histogram_stats(name)
                    for name in self.histograms.keys()
                },
                'timestamp': datetime.now().isoformat()
            }
    
    def reset(self):
        """Reset all metrics"""
        with self.lock:
            self.metrics.clear()
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
        logger.info("Metrics reset")

# ============================================================================
# HEALTH MONITOR (Task 6.O.3)
# ============================================================================

class HealthMonitor:
    """Monitor system health and perform checks"""
    
    def __init__(self, orchestrator):
        """
        Initialize health monitor
        
        Args:
            orchestrator: OrchestratorEngine instance
        """
        self.orchestrator = orchestrator
        self.checks: Dict[str, Callable] = {}
        self.health_history: deque = deque(maxlen=100)
        self.running = False
        self.check_interval = 30  # seconds
        self.monitor_thread = None
        self.recovery_enabled = True
        
        logger.info("Health monitor initialized")
    
    def register_check(self, name: str, check_fn: Callable):
        """
        Register health check function
        
        Args:
            name: Check name
            check_fn: Function that returns HealthCheck or boolean
        """
        self.checks[name] = check_fn
        logger.info(f"Registered health check: {name}")
    
    def start(self):
        """Start health monitoring"""
        if self.running:
            logger.warning("Health monitor already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="health-monitor"
        )
        self.monitor_thread.start()
        logger.info("Health monitor started")
    
    def stop(self):
        """Stop health monitoring"""
        logger.info("Stopping health monitor...")
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Health monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Run all health checks
                results = self.run_checks()
                
                # Store in history
                self.health_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'results': [r.to_dict() for r in results]
                })
                
                # Check for unhealthy components
                unhealthy = [r for r in results if r.status == 'unhealthy']
                degraded = [r for r in results if r.status == 'degraded']
                
                if unhealthy:
                    logger.warning(f"Unhealthy components detected: {[r.component for r in unhealthy]}")
                    if self.recovery_enabled:
                        self._handle_unhealthy_components(unhealthy)
                
                if degraded:
                    logger.info(f"Degraded components: {[r.component for r in degraded]}")
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
            
            # Sleep until next check
            time.sleep(self.check_interval)
    
    def run_checks(self) -> List[HealthCheck]:
        """
        Run all registered health checks
        
        Returns:
            List of health check results
        """
        results = []
        
        for name, check_fn in self.checks.items():
            start_time = time.time()
            
            try:
                result = check_fn()
                latency = (time.time() - start_time) * 1000  # Convert to ms
                
                if isinstance(result, HealthCheck):
                    result.latency_ms = latency
                    results.append(result)
                else:
                    # If check returns boolean, convert to HealthCheck
                    results.append(HealthCheck(
                        component=name,
                        status='healthy' if result else 'unhealthy',
                        timestamp=datetime.now(),
                        latency_ms=latency
                    ))
                    
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results.append(HealthCheck(
                    component=name,
                    status='unhealthy',
                    timestamp=datetime.now(),
                    details={'error': str(e)}
                ))
        
        return results
    
    def _handle_unhealthy_components(self, unhealthy: List[HealthCheck]):
        """
        Handle unhealthy components with recovery actions (Task 6.O.3)
        
        Args:
            unhealthy: List of unhealthy check results
        """
        for check in unhealthy:
            logger.warning(f"Attempting recovery for: {check.component}")
            
            try:
                if check.component == 'orchestrator':
                    self._recover_orchestrator(check)
                elif check.component == 'event_router':
                    self._recover_event_router(check)
                elif check.component.startswith('vehicle'):
                    self._recover_vehicle(check)
                elif check.component == 'system_resources':
                    self._recover_system_resources(check)
                else:
                    logger.warning(f"No recovery action defined for: {check.component}")
            except Exception as e:
                logger.error(f"Recovery failed for {check.component}: {e}")
    
    def _recover_orchestrator(self, check: HealthCheck):
        """Attempt to recover orchestrator"""
        logger.info("Attempting orchestrator recovery...")
        
        # Try restarting event router
        if not self.orchestrator.event_router.running:
            self.orchestrator.event_router.start()
            logger.info("Event router restarted")
    
    def _recover_event_router(self, check: HealthCheck):
        """Attempt to recover event router"""
        logger.info("Attempting event router recovery...")
        
        # Check queue size
        queue_size = self.orchestrator.event_router.event_queue.qsize()
        if queue_size > 5000:
            logger.warning(f"Event queue very large: {queue_size}")
            # Could implement queue drainage or increase workers
    
    def _recover_vehicle(self, check: HealthCheck):
        """Attempt to recover vehicle"""
        vehicle_id = check.component.replace('vehicle_', '')
        logger.info(f"Attempting vehicle recovery: {vehicle_id}")
        
        # Could implement:
        # - Reset vehicle connection
        # - Request status update
        # - Mark vehicle as offline
    
    def _recover_system_resources(self, check: HealthCheck):
        """Attempt to recover system resources"""
        logger.warning("System resources critical")
        
        details = check.details
        if details.get('memory_percent', 0) > 90:
            logger.critical("Memory usage critical - consider scaling")
        
        if details.get('cpu_percent', 0) > 90:
            logger.critical("CPU usage critical - consider scaling")
    
    def get_health_status(self) -> Dict:
        """
        Get current health status
        
        Returns:
            Dictionary with overall status and check results
        """
        results = self.run_checks()
        
        # Determine overall status
        overall_status = 'healthy'
        if any(r.status == 'unhealthy' for r in results):
            overall_status = 'unhealthy'
        elif any(r.status == 'degraded' for r in results):
            overall_status = 'degraded'
        
        return {
            'overall_status': overall_status,
            'checks': [r.to_dict() for r in results],
            'timestamp': datetime.now().isoformat(),
            'check_count': len(results)
        }
    
    def get_health_history(self, limit: int = 10) -> List[Dict]:
        """Get recent health check history"""
        return list(self.health_history)[-limit:]

# ============================================================================
# ORCHESTRATOR METRICS INTEGRATION (Task 6.O.4)
# ============================================================================

class OrchestratorMetrics:
    """Integrate metrics collection with orchestrator"""
    
    def __init__(self, orchestrator):
        """
        Initialize orchestrator metrics
        
        Args:
            orchestrator: OrchestratorEngine instance
        """
        self.orchestrator = orchestrator
        self.collector = MetricsCollector()
        self.health_monitor = HealthMonitor(orchestrator)
        self.system_metrics_thread = None
        self.running = False
        
        self._setup_metrics()
        self._setup_health_checks()
        
        logger.info("Orchestrator metrics initialized")
    
    def _setup_metrics(self):
        """Setup metric collection from orchestrator events"""
        
        # Subscribe to orchestrator events for metric recording
        def record_event_metrics(event):
            # Count events by type and priority
            self.collector.record_counter(
                'orchestrator_events_total',
                labels={'type': event.type, 'priority': event.priority.name}
            )
            
            # Record event processing time if available
            if hasattr(event, 'processing_time'):
                self.collector.record_histogram(
                    'event_processing_duration_ms',
                    event.processing_time * 1000,
                    labels={'type': event.type}
                )
        
        self.orchestrator.event_router.subscribe('*', record_event_metrics)
        logger.info("Event metrics recording setup complete")
    
    def _setup_health_checks(self):
        """Setup health checks for all components"""
        
        # Orchestrator health
        self.health_monitor.register_check(
            'orchestrator',
            self._check_orchestrator_health
        )
        
        # Event router health
        self.health_monitor.register_check(
            'event_router',
            self._check_event_router_health
        )
        
        # Vehicle manager health
        self.health_monitor.register_check(
            'vehicle_manager',
            self._check_vehicle_manager_health
        )
        
        # Mission planner health
        self.health_monitor.register_check(
            'mission_planner',
            self._check_mission_planner_health
        )
        
        # Geofencing engine health
        self.health_monitor.register_check(
            'geofencing',
            self._check_geofencing_health
        )
        
        # System resources health
        self.health_monitor.register_check(
            'system_resources',
            self._check_system_resources
        )
        
        logger.info("Health checks registered")
    
    def _check_orchestrator_health(self) -> HealthCheck:
        """Check orchestrator health"""
        status = 'healthy' if self.orchestrator.status == 'running' else 'unhealthy'
        
        return HealthCheck(
            component='orchestrator',
            status=status,
            timestamp=datetime.now(),
            details={
                'status': self.orchestrator.status,
                'uptime': str(datetime.now() - self.orchestrator.start_time) if self.orchestrator.start_time else 'N/A'
            }
        )
    
    def _check_event_router_health(self) -> HealthCheck:
        """Check event router health"""
        queue_size = self.orchestrator.event_router.event_queue.qsize()
        
        # Determine status based on queue size
        if queue_size > 8000:
            status = 'unhealthy'
        elif queue_size > 5000:
            status = 'degraded'
        else:
            status = 'healthy' if self.orchestrator.event_router.running else 'unhealthy'
        
        return HealthCheck(
            component='event_router',
            status=status,
            timestamp=datetime.now(),
            details={
                'running': self.orchestrator.event_router.running,
                'queue_size': queue_size,
                'event_count': len(self.orchestrator.event_router.event_history)
            }
        )
    
    def _check_vehicle_manager_health(self) -> HealthCheck:
        """Check vehicle manager health"""
        vehicle_count = len(self.orchestrator.vehicle_manager.vehicles)
        
        return HealthCheck(
            component='vehicle_manager',
            status='healthy',
            timestamp=datetime.now(),
            details={
                'vehicle_count': vehicle_count,
                'max_vehicles': 100
            }
        )
    
    def _check_mission_planner_health(self) -> HealthCheck:
        """Check mission planner health"""
        return HealthCheck(
            component='mission_planner',
            status='healthy',
            timestamp=datetime.now(),
            details={
                'active_missions': len([m for m in self.orchestrator.missions.values() if m.status.value == 'executing'])
            }
        )
    
    def _check_geofencing_health(self) -> HealthCheck:
        """Check geofencing engine health"""
        zone_count = len(self.orchestrator.geofencing.zones)
        
        return HealthCheck(
            component='geofencing',
            status='healthy',
            timestamp=datetime.now(),
            details={
                'zone_count': zone_count,
                'active_zones': len([z for z in self.orchestrator.geofencing.zones.values() if z.active])
            }
        )
    
    def _check_system_resources(self) -> HealthCheck:
        """Check system resource health"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Determine status
        status = 'healthy'
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            status = 'unhealthy'
        elif cpu_percent > 70 or memory.percent > 70 or disk.percent > 80:
            status = 'degraded'
        
        return HealthCheck(
            component='system_resources',
            status=status,
            timestamp=datetime.now(),
            details={
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3)
            }
        )
    
    def _start_system_metrics(self):
        """Start collecting system metrics"""
        def collect_system_metrics():
            logger.info("System metrics collection started")
            
            while self.running:
                try:
                    # System metrics
                    self.collector.record_gauge('system_cpu_percent', psutil.cpu_percent())
                    self.collector.record_gauge('system_memory_percent', psutil.virtual_memory().percent)
                    self.collector.record_gauge('system_disk_percent', psutil.disk_usage('/').percent)
                    
                    # Orchestrator metrics
                    status = self.orchestrator.get_status()
                    self.collector.record_gauge('orchestrator_vehicles_total', status.get('vehicles', 0))
                    self.collector.record_gauge('orchestrator_missions_total', status.get('missions', 0))
                    self.collector.record_gauge('orchestrator_workflows_active', status.get('active_workflows', 0))
                    self.collector.record_gauge('orchestrator_events_processed', status.get('events_processed', 0))
                    self.collector.record_gauge('orchestrator_geofences_total', status.get('geofences', 0))
                    
                    # Fleet metrics
                    if 'fleet_stats' in status:
                        fleet = status['fleet_stats']
                        self.collector.record_gauge('fleet_vehicles_total', fleet.get('total', 0))
                        self.collector.record_gauge('fleet_battery_average', fleet.get('average_battery', 0))
                        self.collector.record_gauge('fleet_missions_active', fleet.get('active_missions', 0))
                        
                        # Per-status counts
                        for status_type, count in fleet.get('by_status', {}).items():
                            self.collector.record_gauge(
                                'fleet_vehicles_by_status',
                                count,
                                labels={'status': status_type}
                            )
                        
                        # Per-type counts
                        for vehicle_type, count in fleet.get('by_type', {}).items():
                            self.collector.record_gauge(
                                'fleet_vehicles_by_type',
                                count,
                                labels={'type': vehicle_type}
                            )
                    
                except Exception as e:
                    logger.error(f"System metrics collection error: {e}")
                
                time.sleep(10)  # Collect every 10 seconds
        
        self.system_metrics_thread = threading.Thread(
            target=collect_system_metrics,
            daemon=True,
            name="system-metrics"
        )
        self.system_metrics_thread.start()
    
    def start(self):
        """Start metrics and monitoring"""
        self.running = True
        self.health_monitor.start()
        self._start_system_metrics()
        logger.info("Orchestrator metrics started")
    
    def stop(self):
        """Stop metrics and monitoring"""
        self.running = False
        self.health_monitor.stop()
        if self.system_metrics_thread:
            self.system_metrics_thread.join(timeout=5)
        logger.info("Orchestrator metrics stopped")
    
    def get_dashboard_data(self) -> Dict:
        """
        Get complete dashboard data (Task 6.O.4)
        
        Returns:
            Dictionary with health, metrics, and rates
        """
        health = self.health_monitor.get_health_status()
        metrics = self.collector.get_all_metrics()
        
        # Calculate rates
        event_rate = self._calculate_rate('orchestrator_events_total')
        
        return {
            'health': health,
            'metrics': metrics,
            'rates': {
                'events_per_second': event_rate,
                'timestamp': datetime.now().isoformat()
            },
            'system': {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'uptime': str(datetime.now() - self.orchestrator.start_time) if self.orchestrator.start_time else 'N/A'
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_rate(self, metric_name: str, window_seconds: int = 60) -> float:
        """
        Calculate rate for a metric over time window
        
        Args:
            metric_name: Name of metric
            window_seconds: Time window in seconds
            
        Returns:
            Rate per second
        """
        points = self.collector.get_metric(metric_name)
        
        if len(points) < 2:
            return 0.0
        
        # Calculate rate over window
        now = datetime.now()
        window_ago = now - timedelta(seconds=window_seconds)
        recent_points = [p for p in points if p.timestamp > window_ago]
        
        if len(recent_points) < 2:
            return 0.0
        
        value_diff = recent_points[-1].value - recent_points[0].value
        time_diff = (recent_points[-1].timestamp - recent_points[0].timestamp).total_seconds()
        
        return value_diff / time_diff if time_diff > 0 else 0.0
    
    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format
        
        Returns:
            Prometheus-formatted metrics string
        """
        metrics = self.collector.get_all_metrics()
        output = []
        
        # Export counters
        for name, value in metrics['counters'].items():
            clean_name = name.split('{')[0]  # Remove labels from name
            output.append(f"# TYPE {clean_name} counter")
            output.append(f"{name} {value}")
        
        # Export gauges
        for name, value in metrics['gauges'].items():
            clean_name = name.split('{')[0]
            output.append(f"# TYPE {clean_name} gauge")
            output.append(f"{name} {value}")
        
        # Export histogram summaries
        for name, stats in metrics['histograms'].items():
            if stats['count'] > 0:
                clean_name = name.split('{')[0]
                output.append(f"# TYPE {clean_name} summary")
                output.append(f"{name}_count {stats['count']}")
                output.append(f"{name}_sum {stats['mean'] * stats['count']}")
                output.append(f"{name}{{quantile=\"0.5\"}} {stats['p50']}")
                output.append(f"{name}{{quantile=\"0.95\"}} {stats['p95']}")
                output.append(f"{name}{{quantile=\"0.99\"}} {stats['p99']}")
        
        return "\n".join(output)

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    """Example usage of monitoring system"""
    
    print("Testing Monitoring System...")
    print("="*70)
    
    # Mock orchestrator for testing
    class MockOrchestrator:
        def __init__(self):
            self.status = "running"
            self.start_time = datetime.now()
            self.event_router = type('obj', (object,), {
                'running': True,
                'event_queue': type('obj', (object,), {'qsize': lambda: 10})(),
                'event_history': [],
                'subscribe': lambda *args: None
            })()
            self.vehicle_manager = type('obj', (object,), {'vehicles': {}})()
            self.mission_planner = type('obj', (object,), {})()
            self.missions = {}
            self.geofencing = type('obj', (object,), {'zones': {}})()
        
        def get_status(self):
            return {
                'status': self.status,
                'vehicles': 3,
                'missions': 5,
                'active_workflows': 2,
                'events_processed': 150,
                'geofences': 2,
                'fleet_stats': {
                    'total': 3,
                    'active_missions': 1,
                    'average_battery': 85.5,
                    'by_status': {'idle': 2, 'flying': 1},
                    'by_type': {'multi-rotor': 2, 'fixed-wing': 1}
                }
            }
    
    # Create mock orchestrator
    orchestrator = MockOrchestrator()
    
    # Initialize metrics
    print("\n1. Initializing metrics system...")
    metrics = OrchestratorMetrics(orchestrator)
    
    # Start monitoring
    print("2. Starting health monitoring...")
    metrics.start()
    
    print("3. Collecting metrics for 10 seconds...")
    
    # Simulate some metrics
    for i in range(10):
        metrics.collector.record_counter('test_counter')
        metrics.collector.record_gauge('test_gauge', 50 + i)
        metrics.collector.record_histogram('test_latency', 10 + i * 0.5)
        time.sleep(1)
    
    # Get dashboard data
    print("\n4. Retrieving dashboard data...")
    dashboard = metrics.get_dashboard_data()
    
    print("\n" + "="*70)
    print("METRICS DASHBOARD")
    print("="*70)
    
    print(f"\nOverall Health: {dashboard['health']['overall_status'].upper()}")
    
    print(f"\nHealth Checks ({len(dashboard['health']['checks'])}):")
    for check in dashboard['health']['checks']:
        icon = "✓" if check['status'] == 'healthy' else "⚠" if check['status'] == 'degraded' else "✗"
        print(f"  {icon} {check['component']}: {check['status']} ({check['latency_ms']:.2f}ms)")
    
    print(f"\nSystem Metrics:")
    print(f"  CPU: {dashboard['system']['cpu_percent']:.1f}%")
    print(f"  Memory: {dashboard['system']['memory_percent']:.1f}%")
    print(f"  Uptime: {dashboard['system']['uptime']}")
    
    print(f"\nKey Metrics:")
    gauges = dashboard['metrics']['gauges']
    for key in list(gauges.keys())[:5]:
        print(f"  {key}: {gauges[key]}")
    
    print(f"\nEvent Rate: {dashboard['rates']['events_per_second']:.2f} events/sec")
    
    # Export Prometheus format
    print(f"\n5. Exporting Prometheus format...")
    prometheus_output = metrics.export_prometheus()
    print(f"\nPrometheus metrics (first 10 lines):")
    print('\n'.join(prometheus_output.split('\n')[:10]))
    
    print("\n" + "="*70)
    
    # Stop monitoring
    print("\n6. Stopping monitoring...")
    metrics.stop()
    
    print("\n✅ Monitoring system test completed successfully!")