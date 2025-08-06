#!/usr/bin/env python3
"""
Alert Sender Module
Handles email notifications and alert logging for DNS DDoS events
"""

import smtplib
import logging
import json
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

@dataclass
class Alert:
    """Alert information"""
    timestamp: datetime
    alert_type: str
    severity: str
    source_ip: str
    message: str
    details: Dict[str, Any]
    actions_taken: List[str]
    alert_id: str

class AlertSender:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.alerts_log = config.get('alerts_log', 'data/alerts_log.json')
        self.alert_history = []
        
        # Email configuration
        self.smtp_config = {
            'server': config.get('smtp_server', 'localhost'),
            'port': config.get('smtp_port', 25),
            'use_tls': config.get('smtp_use_tls', False),
            'use_ssl': config.get('smtp_use_ssl', False),
            'username': config.get('smtp_username'),
            'password': config.get('smtp_password'),
            'from_email': config.get('from_email', 'dns-monitor@localhost'),
            'to_emails': config.get('alert_email', 'admin@localhost')
        }
        
        # Alert cooldown to prevent spam
        self.alert_cooldown = config.get('alert_cooldown_minutes', 5)
        self.last_alerts = {}  # alert_type -> timestamp
        
        # Load existing alerts
        self._load_alert_history()
        
    def _load_alert_history(self):
        """Load alert history from file"""
        try:
            if os.path.exists(self.alerts_log):
                with open(self.alerts_log, 'r') as f:
                    alerts_data = json.load(f)
                    
                # Convert to Alert objects (recent ones only)
                cutoff_time = datetime.now() - timedelta(days=7)
                for alert_data in alerts_data:
                    try:
                        timestamp = datetime.fromisoformat(alert_data['timestamp'])
                        if timestamp >= cutoff_time:
                            alert = Alert(
                                timestamp=timestamp,
                                alert_type=alert_data['alert_type'],
                                severity=alert_data['severity'],
                                source_ip=alert_data['source_ip'],
                                message=alert_data['message'],
                                details=alert_data.get('details', {}),
                                actions_taken=alert_data.get('actions_taken', []),
                                alert_id=alert_data.get('alert_id', '')
                            )
                            self.alert_history.append(alert)
                    except (KeyError, ValueError) as e:
                        self.logger.warning(f"Skipping invalid alert entry: {e}")
                        
                self.logger.info(f"Loaded {len(self.alert_history)} recent alerts")
                
        except FileNotFoundError:
            self.logger.info("No existing alerts log found")
        except Exception as e:
            self.logger.error(f"Error loading alert history: {e}")
            
    def _save_alert(self, alert: Alert):
        """Save alert to persistent storage"""
        try:
            # Load existing alerts
            if os.path.exists(self.alerts_log):
                with open(self.alerts_log, 'r') as f:
                    alerts_data = json.load(f)
            else:
                alerts_data = []
                
            # Add new alert
            alert_dict = asdict(alert)
            alert_dict['timestamp'] = alert.timestamp.isoformat()
            alerts_data.append(alert_dict)
            
            # Keep only recent alerts (last 30 days)
            cutoff_time = datetime.now() - timedelta(days=30)
            alerts_data = [
                a for a in alerts_data 
                if datetime.fromisoformat(a['timestamp']) >= cutoff_time
            ]
            
            # Save back to file
            os.makedirs(os.path.dirname(self.alerts_log), exist_ok=True)
            with open(self.alerts_log, 'w') as f:
                json.dump(alerts_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving alert: {e}")
            
    def _check_cooldown(self, alert_type: str, source_ip: str = "") -> bool:
        """Check if alert is in cooldown period"""
        cooldown_key = f"{alert_type}_{source_ip}"
        
        if cooldown_key in self.last_alerts:
            last_alert_time = self.last_alerts[cooldown_key]
            if (datetime.now() - last_alert_time).total_seconds() < (self.alert_cooldown * 60):
                return True  # Still in cooldown
                
        return False  # Not in cooldown
        
    def _update_cooldown(self, alert_type: str, source_ip: str = ""):
        """Update cooldown timestamp"""
        cooldown_key = f"{alert_type}_{source_ip}"
        self.last_alerts[cooldown_key] = datetime.now()
        
    def send_alert(self, alert_type: str, severity: str, source_ip: str, 
                  message: str, details: Dict = None, actions_taken: List[str] = None,
                  force_send: bool = False) -> bool:
        """Send an alert notification"""
        
        # Check cooldown unless forced
        if not force_send and self._check_cooldown(alert_type, source_ip):
            self.logger.debug(f"Alert {alert_type} for {source_ip} is in cooldown")
            return False
            
        # Create alert object
        alert_id = f"{alert_type}_{source_ip}_{int(datetime.now().timestamp())}"
        alert = Alert(
            timestamp=datetime.now(),
            alert_type=alert_type,
            severity=severity,
            source_ip=source_ip,
            message=message,
            details=details or {},
            actions_taken=actions_taken or [],
            alert_id=alert_id
        )
        
        # Save alert
        self._save_alert(alert)
        self.alert_history.append(alert)
        
        # Send email notification
        email_sent = self._send_email_alert(alert)
        
        # Update cooldown
        if not force_send:
            self._update_cooldown(alert_type, source_ip)
            
        # Log the alert
        self.logger.warning(f"ALERT [{severity}] {alert_type}: {message} from {source_ip}")
        
        return email_sent
        
    def _send_email_alert(self, alert: Alert) -> bool:
        """Send email notification for alert"""
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['from_email']
            msg['To'] = self.smtp_config['to_emails']
            msg['Subject'] = f"[DNS DDoS Monitor] {alert.severity} Alert: {alert.alert_type}"
            
            # Create email body
            body = self._create_email_body(alert)
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server and send
            if self.smtp_config['use_ssl']:
                server = smtplib.SMTP_SSL(self.smtp_config['server'], self.smtp_config['port'])
            else:
                server = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])
                if self.smtp_config['use_tls']:
                    server.starttls()
                    
            # Login if credentials provided
            if self.smtp_config['username'] and self.smtp_config['password']:
                server.login(self.smtp_config['username'], self.smtp_config['password'])
                
            # Send email
            text = msg.as_string()
            server.sendmail(self.smtp_config['from_email'], 
                          self.smtp_config['to_emails'].split(','), text)
            server.quit()
            
            self.logger.info(f"Alert email sent for {alert.alert_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
            return False
            
    def _create_email_body(self, alert: Alert) -> str:
        """Create formatted email body"""
        body = f"""DNS DDoS Monitor Alert

Alert Details:
==============
Type: {alert.alert_type}
Severity: {alert.severity}
Source IP: {alert.source_ip}
Timestamp: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Alert ID: {alert.alert_id}

Message:
{alert.message}

"""
        
        # Add details if available
        if alert.details:
            body += "Additional Details:\n"
            body += "==================\n"
            for key, value in alert.details.items():
                body += f"{key}: {value}\n"
            body += "\n"
            
        # Add actions taken
        if alert.actions_taken:
            body += "Actions Taken:\n"
            body += "==============\n"
            for action in alert.actions_taken:
                body += f"- {action}\n"
            body += "\n"
            
        # Add system info
        body += f"""System Information:
==================
Monitor Host: {os.uname().nodename}
Alert Log: {self.alerts_log}

This is an automated alert from DNS DDoS Monitor.
"""
        
        return body
        
    def send_ddos_alert(self, detection_result) -> bool:
        """Send DDoS detection alert"""
        actions = []
        
        # Determine actions based on detection
        if detection_result.recommended_action == 'block_ip':
            actions.append(f"IP {detection_result.source_ip} blocked via iptables")
            
        # Create detailed message
        message = f"DDoS attack detected: {detection_result.threat_type}"
        if 'query_count' in detection_result.details:
            message += f" ({detection_result.details['query_count']} queries)"
            
        return self.send_alert(
            alert_type=detection_result.threat_type,
            severity=detection_result.severity,
            source_ip=detection_result.source_ip,
            message=message,
            details=detection_result.details,
            actions_taken=actions
        )
        
    def send_dga_alert(self, dga_result, source_ip: str) -> bool:
        """Send DGA detection alert"""
        message = f"DGA domain detected: {dga_result.domain} (confidence: {dga_result.confidence:.2f})"
        
        actions = [f"Domain {dga_result.domain} added to RPZ blocklist"]
        
        details = {
            'domain': dga_result.domain,
            'confidence': dga_result.confidence,
            'algorithm': dga_result.algorithm,
            'reason': dga_result.reason,
            'features': dga_result.features
        }
        
        return self.send_alert(
            alert_type='dga_detection',
            severity='MEDIUM',
            source_ip=source_ip,
            message=message,
            details=details,
            actions_taken=actions
        )
        
    def send_system_alert(self, message: str, severity: str = 'INFO', 
                         details: Dict = None) -> bool:
        """Send system status alert"""
        return self.send_alert(
            alert_type='system_status',
            severity=severity,
            source_ip='localhost',
            message=message,
            details=details or {}
        )
        
    def get_alert_stats(self) -> Dict:
        """Get alert statistics"""
        if not self.alert_history:
            return {}
            
        current_time = datetime.now()
        
        # Time-based counts
        last_hour = current_time - timedelta(hours=1)
        last_day = current_time - timedelta(days=1)
        last_week = current_time - timedelta(days=7)
        
        stats = {
            'total_alerts': len(self.alert_history),
            'alerts_last_hour': len([a for a in self.alert_history if a.timestamp >= last_hour]),
            'alerts_last_day': len([a for a in self.alert_history if a.timestamp >= last_day]),
            'alerts_last_week': len([a for a in self.alert_history if a.timestamp >= last_week]),
        }
        
        # Alert type distribution
        alert_types = {}
        for alert in self.alert_history:
            alert_types[alert.alert_type] = alert_types.get(alert.alert_type, 0) + 1
        stats['alert_types'] = alert_types
        
        # Severity distribution
        severities = {}
        for alert in self.alert_history:
            severities[alert.severity] = severities.get(alert.severity, 0) + 1
        stats['severities'] = severities
        
        # Top source IPs
        source_ips = {}
        for alert in self.alert_history:
            if alert.source_ip != 'localhost':
                source_ips[alert.source_ip] = source_ips.get(alert.source_ip, 0) + 1
        stats['top_source_ips'] = dict(sorted(source_ips.items(), key=lambda x: x[1], reverse=True)[:10])
        
        return stats
        
    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """Get recent alerts within specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff_time]
        
    def export_alerts(self, format: str = 'json', hours: int = 24) -> str:
        """Export recent alerts in specified format"""
        recent_alerts = self.get_recent_alerts(hours)
        
        if format.lower() == 'json':
            export_data = []
            for alert in recent_alerts:
                alert_dict = asdict(alert)
                alert_dict['timestamp'] = alert.timestamp.isoformat()
                export_data.append(alert_dict)
            return json.dumps(export_data, indent=2)
            
        elif format.lower() == 'csv':
            lines = ['Timestamp,Type,Severity,Source_IP,Message,Actions_Taken']
            for alert in recent_alerts:
                actions_str = '; '.join(alert.actions_taken)
                lines.append(f"{alert.timestamp.isoformat()},{alert.alert_type},{alert.severity},{alert.source_ip},\"{alert.message}\",\"{actions_str}\"")
            return '\n'.join(lines)
            
        else:
            raise ValueError(f"Unsupported export format: {format}")
            
    def test_email_configuration(self) -> bool:
        """Test email configuration by sending a test message"""
        try:
            test_alert = Alert(
                timestamp=datetime.now(),
                alert_type='test',
                severity='INFO',
                source_ip='localhost',
                message='This is a test alert to verify email configuration',
                details={'test': True},
                actions_taken=['Email configuration test'],
                alert_id='test_' + str(int(datetime.now().timestamp()))
            )
            
            return self._send_email_alert(test_alert)
            
        except Exception as e:
            self.logger.error(f"Email test failed: {e}")
            return False