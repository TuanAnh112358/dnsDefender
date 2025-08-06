#!/usr/bin/env python3
"""
DNS DDoS Monitor - Main Application
Orchestrates all monitoring components for DNS DDoS detection and mitigation
"""

import json
import logging
import time
import signal
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List
import argparse
import threading

# Import core modules
from core.log_reader import DNSLogReader
from core.threshold_detector import ThresholdDetector
from core.dga_classifier import DGAClassifier
from core.firewall_controller import FirewallController
from core.rpz_manager import RPZManager
from core.alert_sender import AlertSender

class DNSDDoSMonitor:
    def __init__(self, config_file: str = "config/monitor_config.json"):
        self.config = self._load_config(config_file)
        self.running = False
        self.logger = self._setup_logging()
        
        # Initialize components
        self._initialize_components()
        
        # Statistics
        self.stats = {
            'start_time': None,
            'total_queries_processed': 0,
            'threats_detected': 0,
            'ips_blocked': 0,
            'domains_blocked': 0,
            'alerts_sent': 0
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _load_config(self, config_file: str) -> Dict:
        """Load monitoring configuration"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            print(f"Error: Configuration file not found: {config_file}")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)
            
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        log_level = self.config.get('log_level', 'INFO').upper()
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[
                logging.FileHandler('logs/dns_ddos_monitor.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info("DNS DDoS Monitor starting up")
        return logger
        
    def _initialize_components(self):
        """Initialize all monitoring components"""
        try:
            # Log reader
            self.log_reader = DNSLogReader(self.config['log_file'])
            self.logger.info("DNS log reader initialized")
            
            # Threshold detector
            self.threshold_detector = ThresholdDetector(self.config)
            self.logger.info("Threshold detector initialized")
            
            # DGA classifier (if enabled)
            self.dga_classifier = None
            if self.config.get('use_dga_detection', True):
                model_path = self.config.get('dga_model_path')
                self.dga_classifier = DGAClassifier(model_path)
                self.logger.info("DGA classifier initialized")
                
            # Firewall controller
            self.firewall_controller = FirewallController(self.config)
            if self.firewall_controller.test_iptables_connectivity():
                self.logger.info("Firewall controller initialized")
            else:
                self.logger.warning("Iptables not available - IP blocking disabled")
                
            # RPZ manager (if enabled)
            self.rpz_manager = None
            if self.config.get('use_rpz_filtering', True):
                self.rpz_manager = RPZManager(self.config)
                self.logger.info("RPZ manager initialized")
                
            # Alert sender
            self.alert_sender = AlertSender(self.config)
            self.logger.info("Alert sender initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            sys.exit(1)
            
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    def _process_queries(self, queries: List[Dict]) -> None:
        """Process DNS queries for threats"""
        if not queries:
            return
            
        self.stats['total_queries_processed'] += len(queries)
        
        # Run threshold detection
        detection_results = self.threshold_detector.run_all_detections(queries)
        
        for result in detection_results:
            self.stats['threats_detected'] += 1
            self.logger.warning(f"Threat detected: {result.threat_type} from {result.source_ip}")
            
            # Take action based on detection
            self._handle_detection(result)
            
        # DGA detection on domains
        if self.dga_classifier:
            self._check_dga_domains(queries)
            
    def _handle_detection(self, detection_result) -> None:
        """Handle a threat detection"""
        actions_taken = []
        
        # Block IP if recommended
        if (detection_result.recommended_action == 'block_ip' and 
            self.config.get('response_actions', {}).get('block_ip', True)):
            
            if self.firewall_controller.block_ip(
                detection_result.source_ip, 
                f"{detection_result.threat_type} detected"
            ):
                actions_taken.append(f"Blocked IP {detection_result.source_ip}")
                self.stats['ips_blocked'] += 1
                
        # Send alert if configured
        if self.config.get('response_actions', {}).get('send_alert', True):
            if self.alert_sender.send_ddos_alert(detection_result):
                actions_taken.append("Alert sent to administrators")
                self.stats['alerts_sent'] += 1
                
        # Log actions taken
        if actions_taken:
            self.threshold_detector.add_blocked_ip(
                detection_result.source_ip,
                detection_result.threat_type
            )
            
    def _check_dga_domains(self, queries: List[Dict]) -> None:
        """Check domains for DGA patterns"""
        unique_domains = set(query['query_domain'] for query in queries)
        
        for domain in unique_domains:
            dga_result = self.dga_classifier.classify_domain(domain)
            
            if dga_result.is_dga and dga_result.confidence > 0.7:
                self.logger.warning(f"DGA domain detected: {domain} (confidence: {dga_result.confidence:.2f})")
                
                # Find source IPs for this domain
                source_ips = set(
                    query['client_ip'] for query in queries 
                    if query['query_domain'] == domain
                )
                
                # Block domain via RPZ if configured
                if (self.rpz_manager and 
                    self.config.get('response_actions', {}).get('add_to_rpz', True)):
                    
                    if self.rpz_manager.block_domain(
                        domain, 
                        f"DGA detected (confidence: {dga_result.confidence:.2f})"
                    ):
                        self.stats['domains_blocked'] += 1
                        
                # Send DGA alert for each source IP
                for source_ip in source_ips:
                    if self.alert_sender.send_dga_alert(dga_result, source_ip):
                        self.stats['alerts_sent'] += 1
                        
    def _cleanup_expired_blocks(self) -> None:
        """Clean up expired blocks"""
        try:
            # Cleanup expired IP blocks
            expired_ips = self.firewall_controller.cleanup_expired_blocks()
            if expired_ips > 0:
                self.logger.info(f"Cleaned up {expired_ips} expired IP blocks")
                
            # Cleanup expired domain blocks
            if self.rpz_manager:
                expired_domains = self.rpz_manager.cleanup_expired_blocks()
                if expired_domains > 0:
                    self.logger.info(f"Cleaned up {expired_domains} expired domain blocks")
                    
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            
    def _print_status(self) -> None:
        """Print current status"""
        if self.stats['start_time']:
            uptime = datetime.now() - self.stats['start_time']
            
            # Get component stats
            fw_stats = self.firewall_controller.get_firewall_stats()
            rpz_stats = self.rpz_manager.get_rpz_stats() if self.rpz_manager else {}
            alert_stats = self.alert_sender.get_alert_stats()
            detection_stats = self.threshold_detector.get_detection_stats()
            
            print(f"\n=== DNS DDoS Monitor Status ===")
            print(f"Uptime: {uptime}")
            print(f"Queries processed: {self.stats['total_queries_processed']:,}")
            print(f"Threats detected: {self.stats['threats_detected']}")
            print(f"IPs blocked: {fw_stats.get('total_blocked_ips', 0)}")
            print(f"Domains blocked: {rpz_stats.get('total_blocked_domains', 0)}")
            print(f"Alerts sent: {alert_stats.get('total_alerts', 0)}")
            
            # Recent activity
            print(f"\nRecent activity (last hour):")
            print(f"  IP blocks: {fw_stats.get('blocks_last_hour', 0)}")
            print(f"  Domain blocks: {rpz_stats.get('blocks_last_hour', 0)}")
            print(f"  Alerts: {alert_stats.get('alerts_last_hour', 0)}")
            
    def run_monitoring_cycle(self) -> None:
        """Run one monitoring cycle"""
        try:
            # Read recent logs
            time_window = self.config.get('monitoring', {}).get('stats_window_minutes', 5)
            queries = self.log_reader.read_recent_logs(time_window)
            
            if queries:
                self._process_queries(queries)
                
        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")
            
    def run(self) -> None:
        """Run the main monitoring loop"""
        self.logger.info("Starting DNS DDoS monitoring")
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Send startup alert
        self.alert_sender.send_system_alert(
            "DNS DDoS Monitor started successfully",
            severity='INFO'
        )
        
        check_interval = self.config.get('monitoring', {}).get('check_interval_seconds', 30)
        last_cleanup = datetime.now()
        last_status = datetime.now()
        
        try:
            while self.running:
                # Run monitoring cycle
                self.run_monitoring_cycle()
                
                # Periodic cleanup (every hour)
                if (datetime.now() - last_cleanup).total_seconds() > 3600:
                    self._cleanup_expired_blocks()
                    last_cleanup = datetime.now()
                    
                # Print status (every 5 minutes)
                if (datetime.now() - last_status).total_seconds() > 300:
                    self._print_status()
                    last_status = datetime.now()
                    
                # Wait for next cycle
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring interrupted by user")
        except Exception as e:
            self.logger.error(f"Fatal error in monitoring loop: {e}")
        finally:
            self._shutdown()
            
    def _shutdown(self) -> None:
        """Shutdown the monitor gracefully"""
        self.logger.info("Shutting down DNS DDoS Monitor")
        
        # Send shutdown alert
        try:
            self.alert_sender.send_system_alert(
                "DNS DDoS Monitor shutting down",
                severity='INFO'
            )
        except Exception:
            pass
            
        # Print final stats
        self._print_status()
        
        self.logger.info("DNS DDoS Monitor shutdown complete")
        
    def run_diagnostics(self) -> Dict:
        """Run system diagnostics"""
        diagnostics = {
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        # Test log file access
        try:
            queries = self.log_reader.read_recent_logs(1)
            diagnostics['components']['log_reader'] = {
                'status': 'OK',
                'recent_queries': len(queries)
            }
        except Exception as e:
            diagnostics['components']['log_reader'] = {
                'status': 'ERROR',
                'error': str(e)
            }
            
        # Test firewall
        diagnostics['components']['firewall'] = {
            'status': 'OK' if self.firewall_controller.test_iptables_connectivity() else 'ERROR',
            'stats': self.firewall_controller.get_firewall_stats()
        }
        
        # Test RPZ
        if self.rpz_manager:
            rpz_tests = self.rpz_manager.test_rpz_configuration()
            diagnostics['components']['rpz'] = {
                'status': 'OK' if all(rpz_tests.values()) else 'WARNING',
                'tests': rpz_tests,
                'stats': self.rpz_manager.get_rpz_stats()
            }
            
        # Test email
        try:
            email_test = self.alert_sender.test_email_configuration()
            diagnostics['components']['email'] = {
                'status': 'OK' if email_test else 'ERROR'
            }
        except Exception as e:
            diagnostics['components']['email'] = {
                'status': 'ERROR',
                'error': str(e)
            }
            
        return diagnostics

def main():
    parser = argparse.ArgumentParser(description='DNS DDoS Monitor')
    parser.add_argument('--config', '-c', default='config/monitor_config.json',
                       help='Configuration file path')
    parser.add_argument('--diagnostics', action='store_true',
                       help='Run diagnostics and exit')
    parser.add_argument('--daemon', '-d', action='store_true',
                       help='Run as daemon')
    
    args = parser.parse_args()
    
    # Create monitor instance
    monitor = DNSDDoSMonitor(args.config)
    
    if args.diagnostics:
        # Run diagnostics
        diagnostics = monitor.run_diagnostics()
        print(json.dumps(diagnostics, indent=2))
        return
        
    if args.daemon:
        # TODO: Implement proper daemon mode
        monitor.logger.info("Daemon mode not yet implemented, running in foreground")
        
    # Run monitoring
    try:
        monitor.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()