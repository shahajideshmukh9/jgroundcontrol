# Kafka Event Bus Integration (Task 1.8, 1.O.4, 6.O.2)
# File: kafka_integration.py

"""
Kafka integration for distributed event processing and fleet-wide alerts
Complete implementation with producer, consumer, and fleet aggregation
"""

import json
import logging
import threading
from typing import Dict, List, Callable, Optional
from datetime import datetime
from dataclasses import asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("Kafka not installed. Run: pip install kafka-python")

# ============================================================================
# KAFKA TOPICS (Task 1.8)
# ============================================================================

class KafkaTopics:
    """Kafka topic definitions for different event types"""
    
    # Vehicle Topics
    VEHICLE_STATUS = "vehicle.status.updates"
    VEHICLE_LOCATION = "vehicle.location.updates"
    VEHICLE_TELEMETRY = "vehicle.telemetry.stream"
    VEHICLE_REGISTRY = "vehicle.registry.events"
    
    # Mission Topics
    MISSION_LIFECYCLE = "mission.lifecycle.events"
    MISSION_PROGRESS = "mission.progress.updates"
    MISSION_COMMANDS = "mission.commands"
    
    # Geofence Topics
    GEOFENCE_BREACH = "geofence.breach.alerts"
    GEOFENCE_WARNING = "geofence.warning.notifications"
    GEOFENCE_UPDATES = "geofence.updates"
    
    # Orchestrator Topics
    ORCHESTRATOR_EVENTS = "orchestrator.system.events"
    WORKFLOW_EVENTS = "orchestrator.workflow.events"
    
    # Alert Topics (Task 6.O.2)
    CRITICAL_ALERTS = "alerts.critical"
    WARNING_ALERTS = "alerts.warning"
    INFO_ALERTS = "alerts.info"

# ============================================================================
# KAFKA PRODUCER (Task 1.10, 6.O.2)
# ============================================================================

class KafkaEventProducer:
    """Kafka event producer for publishing events to distributed system"""
    
    def __init__(self, bootstrap_servers: List[str], client_id: str = "orchestrator-producer"):
        """
        Initialize Kafka producer
        
        Args:
            bootstrap_servers: List of Kafka broker addresses
            client_id: Client identifier for this producer
        """
        if not KAFKA_AVAILABLE:
            raise ImportError("Kafka not available. Install with: pip install kafka-python")
        
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self.producer = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Kafka brokers"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas to acknowledge
                retries=3,   # Retry failed sends
                max_in_flight_requests_per_connection=1,  # Ensure ordering
                compression_type='snappy'  # Compress messages
            )
            logger.info(f"Kafka producer connected: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to connect Kafka producer: {e}")
            raise
    
    def publish_vehicle_status(self, vehicle_id: str, status: str, metadata: Dict):
        """
        Publish vehicle status update (Task 1.10)
        
        Args:
            vehicle_id: Unique vehicle identifier
            status: Vehicle status (idle, armed, flying, etc.)
            metadata: Additional status information
        """
        message = {
            'vehicle_id': vehicle_id,
            'status': status,
            'metadata': metadata,
            'timestamp': datetime.now().isoformat()
        }
        self._send(KafkaTopics.VEHICLE_STATUS, message, key=vehicle_id)
        logger.debug(f"Published vehicle status: {vehicle_id} -> {status}")
    
    def publish_vehicle_location(self, vehicle_id: str, location: Dict):
        """
        Publish vehicle location update (Task 1.10)
        
        Args:
            vehicle_id: Unique vehicle identifier
            location: Location dict with lat, lon, alt
        """
        message = {
            'vehicle_id': vehicle_id,
            'location': location,
            'timestamp': datetime.now().isoformat()
        }
        self._send(KafkaTopics.VEHICLE_LOCATION, message, key=vehicle_id)
    
    def publish_vehicle_telemetry(self, vehicle_id: str, telemetry: Dict):
        """
        Publish vehicle telemetry stream (high frequency data)
        
        Args:
            vehicle_id: Unique vehicle identifier
            telemetry: Telemetry data (battery, speed, altitude, etc.)
        """
        message = {
            'vehicle_id': vehicle_id,
            'telemetry': telemetry,
            'timestamp': datetime.now().isoformat()
        }
        self._send(KafkaTopics.VEHICLE_TELEMETRY, message, key=vehicle_id)
    
    def publish_vehicle_registered(self, vehicle_id: str, vehicle_type: str, capabilities: Dict):
        """
        Publish vehicle registration event
        
        Args:
            vehicle_id: Unique vehicle identifier
            vehicle_type: Type of vehicle
            capabilities: Vehicle capabilities
        """
        message = {
            'event_type': 'vehicle_registered',
            'vehicle_id': vehicle_id,
            'vehicle_type': vehicle_type,
            'capabilities': capabilities,
            'timestamp': datetime.now().isoformat()
        }
        self._send(KafkaTopics.VEHICLE_REGISTRY, message, key=vehicle_id)
        logger.info(f"Published vehicle registration: {vehicle_id}")
    
    def publish_mission_event(self, mission_id: str, event_type: str, data: Dict):
        """
        Publish mission lifecycle event
        
        Args:
            mission_id: Unique mission identifier
            event_type: Type of event (created, started, completed, failed)
            data: Event data
        """
        message = {
            'mission_id': mission_id,
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        self._send(KafkaTopics.MISSION_LIFECYCLE, message, key=mission_id)
        logger.info(f"Published mission event: {mission_id} - {event_type}")
    
    def publish_mission_progress(self, mission_id: str, progress: float, current_waypoint: int):
        """
        Publish mission progress update
        
        Args:
            mission_id: Unique mission identifier
            progress: Progress percentage (0-100)
            current_waypoint: Current waypoint index
        """
        message = {
            'mission_id': mission_id,
            'progress': progress,
            'current_waypoint': current_waypoint,
            'timestamp': datetime.now().isoformat()
        }
        self._send(KafkaTopics.MISSION_PROGRESS, message, key=mission_id)
    
    def publish_geofence_breach(self, breach_data: Dict):
        """
        Publish geofence breach alert (Task 6.O.2)
        
        Args:
            breach_data: Breach information including vehicle, zone, severity
        """
        message = {
            'breach_data': breach_data,
            'timestamp': datetime.now().isoformat(),
            'severity': breach_data.get('severity', 'unknown'),
            'vehicle_id': breach_data.get('vehicle_id'),
            'zone_id': breach_data.get('zone_id')
        }
        
        # Route to appropriate topic based on severity
        if breach_data.get('severity') == 'critical':
            topic = KafkaTopics.CRITICAL_ALERTS
            logger.critical(f"CRITICAL BREACH: {breach_data.get('zone_name')}")
        elif breach_data.get('severity') == 'warning':
            topic = KafkaTopics.WARNING_ALERTS
        else:
            topic = KafkaTopics.GEOFENCE_BREACH
        
        self._send(topic, message, key=breach_data.get('vehicle_id'))
    
    def publish_fleet_alert(self, alert_type: str, alert_data: Dict, severity: str = 'critical'):
        """
        Publish fleet-wide alert (Task 6.O.2)
        
        Args:
            alert_type: Type of alert
            alert_data: Alert information
            severity: Alert severity level
        """
        message = {
            'alert_type': alert_type,
            'alert_data': alert_data,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        }
        
        if severity == 'critical':
            topic = KafkaTopics.CRITICAL_ALERTS
        elif severity == 'warning':
            topic = KafkaTopics.WARNING_ALERTS
        else:
            topic = KafkaTopics.INFO_ALERTS
        
        self._send(topic, message)
        logger.warning(f"Fleet-wide {severity} alert: {alert_type}")
    
    def publish_workflow_event(self, workflow_id: str, event_type: str, data: Dict):
        """
        Publish workflow event
        
        Args:
            workflow_id: Unique workflow identifier
            event_type: Type of workflow event
            data: Event data
        """
        message = {
            'workflow_id': workflow_id,
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        self._send(KafkaTopics.WORKFLOW_EVENTS, message, key=workflow_id)
    
    def publish_orchestrator_event(self, event_type: str, data: Dict):
        """
        Publish orchestrator system event
        
        Args:
            event_type: Type of system event
            data: Event data
        """
        message = {
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        self._send(KafkaTopics.ORCHESTRATOR_EVENTS, message)
    
    def _send(self, topic: str, message: Dict, key: Optional[str] = None):
        """
        Send message to Kafka topic
        
        Args:
            topic: Kafka topic name
            message: Message data
            key: Optional message key for partitioning
        """
        try:
            future = self.producer.send(
                topic,
                value=message,
                key=key
            )
            
            # Optionally wait for confirmation (blocks)
            # record_metadata = future.get(timeout=10)
            # logger.debug(f"Message sent to {topic}: partition {record_metadata.partition}")
            
        except KafkaError as e:
            logger.error(f"Failed to send message to {topic}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending to {topic}: {e}")
    
    def flush(self, timeout: int = None):
        """
        Flush pending messages
        
        Args:
            timeout: Max time to wait in seconds
        """
        if self.producer:
            self.producer.flush(timeout=timeout)
            logger.debug("Producer flushed")
    
    def close(self):
        """Close producer connection"""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")

# ============================================================================
# KAFKA CONSUMER (Task 1.11, 6.O.2)
# ============================================================================

class KafkaEventConsumer:
    """Kafka event consumer for processing events from distributed system"""
    
    def __init__(self, bootstrap_servers: List[str], group_id: str, client_id: str = None):
        """
        Initialize Kafka consumer
        
        Args:
            bootstrap_servers: List of Kafka broker addresses
            group_id: Consumer group ID
            client_id: Optional client identifier
        """
        if not KAFKA_AVAILABLE:
            raise ImportError("Kafka not available. Install with: pip install kafka-python")
        
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.client_id = client_id or f"{group_id}-consumer"
        self.consumers: Dict[str, KafkaConsumer] = {}
        self.handlers: Dict[str, List[Callable]] = {}
        self.running = False
        self.threads: List[threading.Thread] = []
    
    def subscribe(self, topic: str, handler: Callable):
        """
        Subscribe to topic with handler (Task 1.11)
        
        Args:
            topic: Kafka topic to subscribe to
            handler: Callback function to handle messages
        """
        if topic not in self.handlers:
            self.handlers[topic] = []
        
        self.handlers[topic].append(handler)
        logger.info(f"Subscribed to topic: {topic}")
    
    def start(self):
        """Start consuming messages from all subscribed topics"""
        self.running = True
        
        for topic in self.handlers.keys():
            thread = threading.Thread(
                target=self._consume_topic,
                args=(topic,),
                daemon=True,
                name=f"consumer-{topic}"
            )
            thread.start()
            self.threads.append(thread)
        
        logger.info(f"Kafka consumers started for {len(self.handlers)} topics")
    
    def _consume_topic(self, topic: str):
        """
        Consume messages from specific topic
        
        Args:
            topic: Kafka topic to consume from
        """
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                client_id=f"{self.client_id}-{topic}",
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='latest',  # Start from latest message
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                max_poll_records=100
            )
            
            self.consumers[topic] = consumer
            logger.info(f"Started consuming from {topic}")
            
            while self.running:
                # Poll for messages
                messages = consumer.poll(timeout_ms=1000, max_records=100)
                
                for topic_partition, records in messages.items():
                    for record in records:
                        try:
                            self._process_message(topic, record.value, record.key)
                        except Exception as e:
                            logger.error(f"Error processing message from {topic}: {e}")
            
            consumer.close()
            logger.info(f"Stopped consuming from {topic}")
            
        except Exception as e:
            logger.error(f"Error in consumer for {topic}: {e}")
    
    def _process_message(self, topic: str, message: Dict, key: Optional[str]):
        """
        Process message with registered handlers (Task 1.11)
        
        Args:
            topic: Topic the message came from
            message: Message data
            key: Message key
        """
        handlers = self.handlers.get(topic, [])
        
        for handler in handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Handler error for {topic}: {e}")
    
    def stop(self):
        """Stop consuming messages"""
        logger.info("Stopping Kafka consumers...")
        self.running = False
        
        # Close all consumers
        for consumer in self.consumers.values():
            try:
                consumer.close(autocommit=True)
            except Exception as e:
                logger.error(f"Error closing consumer: {e}")
        
        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=5)
        
        logger.info("Kafka consumers stopped")

# ============================================================================
# FLEET AGGREGATOR (Task 1.11)
# ============================================================================

class FleetStatusAggregator:
    """Aggregate fleet status from Kafka events (Task 1.11)"""
    
    def __init__(self, consumer: KafkaEventConsumer):
        """
        Initialize fleet aggregator
        
        Args:
            consumer: KafkaEventConsumer instance to subscribe with
        """
        self.consumer = consumer
        self.fleet_status: Dict[str, Dict] = {}
        self.fleet_stats = {
            'total_vehicles': 0,
            'by_status': {},
            'by_type': {},
            'active': 0,
            'idle': 0,
            'flying': 0,
            'emergency': 0,
            'total_missions': 0,
            'active_missions': 0,
            'completed_missions': 0,
            'failed_missions': 0
        }
        
        # Subscribe to relevant topics
        self._setup_subscriptions()
    
    def _setup_subscriptions(self):
        """Setup topic subscriptions"""
        self.consumer.subscribe(
            KafkaTopics.VEHICLE_STATUS,
            self._handle_vehicle_status
        )
        self.consumer.subscribe(
            KafkaTopics.VEHICLE_LOCATION,
            self._handle_vehicle_location
        )
        self.consumer.subscribe(
            KafkaTopics.VEHICLE_REGISTRY,
            self._handle_vehicle_registry
        )
        self.consumer.subscribe(
            KafkaTopics.VEHICLE_TELEMETRY,
            self._handle_vehicle_telemetry
        )
        self.consumer.subscribe(
            KafkaTopics.MISSION_LIFECYCLE,
            self._handle_mission_event
        )
        
        logger.info("Fleet aggregator subscriptions setup complete")
    
    def _handle_vehicle_status(self, message: Dict):
        """Handle vehicle status update"""
        vehicle_id = message.get('vehicle_id')
        status = message.get('status')
        
        if not vehicle_id:
            return
        
        if vehicle_id not in self.fleet_status:
            self.fleet_status[vehicle_id] = {}
            self.fleet_stats['total_vehicles'] += 1
        
        self.fleet_status[vehicle_id]['status'] = status
        self.fleet_status[vehicle_id]['last_status_update'] = message.get('timestamp')
        self.fleet_status[vehicle_id]['metadata'] = message.get('metadata', {})
        
        # Update aggregated stats
        self._update_stats()
    
    def _handle_vehicle_location(self, message: Dict):
        """Handle vehicle location update"""
        vehicle_id = message.get('vehicle_id')
        
        if not vehicle_id:
            return
        
        if vehicle_id not in self.fleet_status:
            self.fleet_status[vehicle_id] = {}
        
        self.fleet_status[vehicle_id]['location'] = message.get('location')
        self.fleet_status[vehicle_id]['last_location_update'] = message.get('timestamp')
    
    def _handle_vehicle_registry(self, message: Dict):
        """Handle vehicle registration event"""
        event_type = message.get('event_type')
        vehicle_id = message.get('vehicle_id')
        
        if not vehicle_id:
            return
        
        if event_type == 'vehicle_registered':
            if vehicle_id not in self.fleet_status:
                self.fleet_status[vehicle_id] = {}
                self.fleet_stats['total_vehicles'] += 1
            
            self.fleet_status[vehicle_id]['type'] = message.get('vehicle_type')
            self.fleet_status[vehicle_id]['capabilities'] = message.get('capabilities', {})
            self.fleet_status[vehicle_id]['registered_at'] = message.get('timestamp')
            
            self._update_stats()
    
    def _handle_vehicle_telemetry(self, message: Dict):
        """Handle vehicle telemetry stream"""
        vehicle_id = message.get('vehicle_id')
        
        if not vehicle_id:
            return
        
        if vehicle_id not in self.fleet_status:
            self.fleet_status[vehicle_id] = {}
        
        self.fleet_status[vehicle_id]['telemetry'] = message.get('telemetry')
        self.fleet_status[vehicle_id]['last_telemetry_update'] = message.get('timestamp')
    
    def _handle_mission_event(self, message: Dict):
        """Handle mission lifecycle event"""
        event_type = message.get('event_type')
        
        if event_type == 'mission_started':
            self.fleet_stats['active_missions'] += 1
            self.fleet_stats['total_missions'] += 1
        elif event_type == 'mission_completed':
            self.fleet_stats['active_missions'] -= 1
            self.fleet_stats['completed_missions'] += 1
        elif event_type == 'mission_failed':
            self.fleet_stats['active_missions'] -= 1
            self.fleet_stats['failed_missions'] += 1
    
    def _update_stats(self):
        """Update aggregated fleet statistics"""
        # Reset status counts
        status_counts = {'idle': 0, 'armed': 0, 'flying': 0, 'landing': 0, 'emergency': 0, 'offline': 0}
        type_counts = {}
        
        for vehicle_data in self.fleet_status.values():
            # Count by status
            status = vehicle_data.get('status', 'unknown')
            if status in status_counts:
                status_counts[status] += 1
            
            # Count by type
            vehicle_type = vehicle_data.get('type', 'unknown')
            type_counts[vehicle_type] = type_counts.get(vehicle_type, 0) + 1
        
        self.fleet_stats['by_status'] = status_counts
        self.fleet_stats['by_type'] = type_counts
        self.fleet_stats['active'] = status_counts.get('flying', 0) + status_counts.get('armed', 0)
        self.fleet_stats['idle'] = status_counts.get('idle', 0)
        self.fleet_stats['flying'] = status_counts.get('flying', 0)
        self.fleet_stats['emergency'] = status_counts.get('emergency', 0)
    
    def get_fleet_status(self) -> Dict:
        """Get current fleet status snapshot"""
        return {
            'fleet_status': self.fleet_status,
            'stats': self.fleet_stats,
            'timestamp': datetime.now().isoformat(),
            'vehicle_count': len(self.fleet_status)
        }
    
    def get_vehicle_status(self, vehicle_id: str) -> Optional[Dict]:
        """Get specific vehicle status"""
        return self.fleet_status.get(vehicle_id)

# ============================================================================
# ORCHESTRATOR KAFKA INTEGRATION (Task 1.O.4)
# ============================================================================

class OrchestratorKafkaIntegration:
    """Integrate Kafka with orchestrator (Task 1.O.4)"""
    
    def __init__(self, orchestrator, bootstrap_servers: List[str], group_id: str = "orchestrator"):
        """
        Initialize Kafka integration with orchestrator
        
        Args:
            orchestrator: OrchestratorEngine instance
            bootstrap_servers: List of Kafka broker addresses
            group_id: Consumer group ID
        """
        self.orchestrator = orchestrator
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        
        # Initialize producer and consumer
        self.producer = KafkaEventProducer(bootstrap_servers, client_id=group_id)
        self.consumer = KafkaEventConsumer(bootstrap_servers, group_id)
        self.aggregator = FleetStatusAggregator(self.consumer)
        
        self._setup_integration()
    
    def _setup_integration(self):
        """Setup Kafka integration with orchestrator"""
        
        # Subscribe orchestrator event router to Kafka producer
        def publish_to_kafka(event):
            """Route orchestrator events to appropriate Kafka topics"""
            
            # Vehicle events
            if 'vehicle' in event.type:
                if 'status' in event.type:
                    self.producer.publish_vehicle_status(
                        event.data.get('vehicle_id'),
                        event.data.get('new_status'),
                        event.data
                    )
                elif 'location' in event.type:
                    self.producer.publish_vehicle_location(
                        event.data.get('vehicle_id'),
                        event.data.get('location')
                    )
                elif 'registered' in event.type:
                    self.producer.publish_vehicle_registered(
                        event.data.get('vehicle_id'),
                        event.data.get('type'),
                        event.data.get('capabilities', {})
                    )
            
            # Mission events
            elif 'mission' in event.type:
                self.producer.publish_mission_event(
                    event.data.get('mission_id'),
                    event.type,
                    event.data
                )
            
            # Geofence breach events
            elif 'geofence.breach' == event.type:
                self.producer.publish_geofence_breach(event.data)
            
            # Workflow events
            elif 'workflow' in event.type:
                self.producer.publish_workflow_event(
                    event.data.get('workflow_id'),
                    event.type,
                    event.data
                )
            
            # System events
            elif 'system' in event.type:
                self.producer.publish_orchestrator_event(event.type, event.data)
        
        # Subscribe to all orchestrator events
        self.orchestrator.event_router.subscribe('*', publish_to_kafka)
        
        # Subscribe to Kafka critical alerts for orchestrator response
        self.consumer.subscribe(
            KafkaTopics.CRITICAL_ALERTS,
            self._handle_critical_alert
        )
        
        # Subscribe to warning alerts
        self.consumer.subscribe(
            KafkaTopics.WARNING_ALERTS,
            self._handle_warning_alert
        )
        
        logger.info("Kafka integration setup complete")
    
    def _handle_critical_alert(self, message: Dict):
        """Handle critical alerts from Kafka (Task 6.O.2)"""
        alert_type = message.get('alert_type')
        alert_data = message.get('alert_data')
        
        logger.critical(f"CRITICAL ALERT RECEIVED: {alert_type}")
        logger.critical(f"Alert data: {alert_data}")
        
        # Orchestrator can take automatic actions here
        # Example: Trigger emergency workflows, notify operators, etc.
        
        # If it's a geofence breach, trigger RTL
        if 'breach' in alert_type.lower():
            vehicle_id = alert_data.get('vehicle_id')
            if vehicle_id:
                logger.critical(f"Initiating emergency RTL for {vehicle_id}")
                # Trigger RTL workflow
                # self.orchestrator.trigger_emergency_rtl(vehicle_id)
    
    def _handle_warning_alert(self, message: Dict):
        """Handle warning alerts from Kafka"""
        alert_type = message.get('alert_type')
        logger.warning(f"Warning alert received: {alert_type}")
    
    def start(self):
        """Start Kafka integration"""
        self.consumer.start()
        logger.info("Kafka integration started - producer and consumer active")
    
    def stop(self):
        """Stop Kafka integration"""
        self.producer.flush()
        self.producer.close()
        self.consumer.stop()
        logger.info("Kafka integration stopped")
    
    def get_fleet_status(self) -> Dict:
        """Get aggregated fleet status"""
        return self.aggregator.get_fleet_status()

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    """Example usage of Kafka integration"""
    
    if not KAFKA_AVAILABLE:
        print("Kafka not available. Install with: pip install kafka-python")
        exit(1)
    
    # Configuration
    bootstrap_servers = ['localhost:9092']
    
    try:
        print("Testing Kafka Integration...")
        print("="*60)
        
        # Create producer
        print("\n1. Creating Kafka producer...")
        producer = KafkaEventProducer(bootstrap_servers)
        
        # Publish test events
        print("\n2. Publishing test events...")
        
        # Vehicle status
        producer.publish_vehicle_status('V001', 'flying', {
            'battery': 85,
            'altitude': 100,
            'speed': 12.5
        })
        print("   ✓ Published vehicle status")
        
        # Vehicle location
        producer.publish_vehicle_location('V001', {
            'lat': 37.7749,
            'lon': -122.4194,
            'alt': 100
        })
        print("   ✓ Published vehicle location")
        
        # Mission event
        producer.publish_mission_event('M001', 'mission_started', {
            'vehicle_id': 'V001',
            'waypoints': 50
        })
        print("   ✓ Published mission event")
        
        # Geofence breach
        producer.publish_geofence_breach({
            'vehicle_id': 'V001',
            'zone_name': 'Restricted Zone Alpha',
            'zone_id': 'GF001',
            'severity': 'critical',
            'action': 'RTL'
        })
        print("   ✓ Published geofence breach")
        
        # Fleet alert
        producer.publish_fleet_alert(
            'weather_warning',
            {'wind_speed': 45, 'gusts': 60},
            severity='warning'
        )
        print("   ✓ Published fleet alert")
        
        # Flush and close
        print("\n3. Flushing producer...")
        producer.flush()
        producer.close()
        
        print("\n" + "="*60)
        print("✅ Kafka integration test completed successfully!")
        print("\nTo consume these messages, run a consumer with:")
        print("  consumer = KafkaEventConsumer(bootstrap_servers, 'test-group')")
        print("  consumer.subscribe(KafkaTopics.VEHICLE_STATUS, handler)")
        print("  consumer.start()")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()