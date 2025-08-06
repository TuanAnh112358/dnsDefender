#!/usr/bin/env python3
"""
DNS DDoS Monitor Web Dashboard
Flask-based web interface for monitoring DNS DDoS attacks and system status
"""

import json
import os
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.log_reader import DNSLogReader
from core.threshold_detector import ThresholdDetector
from core.dga_classifier import DGAClassifier
from core.firewall_controller import FirewallController
from core.rpz_manager import RPZManager
from core.alert_sender import AlertSender

app = Flask(__name__)
app.secret_key = 'dns_ddos_monitor_secret_key'

# Global variables for components
config = {}
log_reader = None
threshold_detector = None
dga_classifier = None
firewall_controller = None
rpz_manager = None
alert_sender = None

def load_config():
    """Load configuration"""
    global config
    config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'monitor_config.json')
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        config = {}

def initialize_components():
    """Initialize monitoring components"""
    global log_reader, threshold_detector, dga_classifier, firewall_controller, rpz_manager, alert_sender
    
    try:
        log_reader = DNSLogReader(config.get('log_file', 'data/query.log'))
        threshold_detector = ThresholdDetector(config)
        
        if config.get('use_dga_detection', True):
            dga_classifier = DGAClassifier(config.get('dga_model_path'))
            
        firewall_controller = FirewallController(config)
        
        if config.get('use_rpz_filtering', True):
            rpz_manager = RPZManager(config)
            
        alert_sender = AlertSender(config)
        
    except Exception as e:
        print(f"Error initializing components: {e}")

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/stats')
def get_stats():
    """Get system statistics"""
    try:
        stats = {
            'timestamp': datetime.now().isoformat(),
            'firewall': firewall_controller.get_firewall_stats() if firewall_controller else {},
            'rpz': rpz_manager.get_rpz_stats() if rpz_manager else {},
            'alerts': alert_sender.get_alert_stats() if alert_sender else {},
            'detection': threshold_detector.get_detection_stats() if threshold_detector else {}
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent_queries')
def get_recent_queries():
    """Get recent DNS queries"""
    try:
        minutes = request.args.get('minutes', 5, type=int)
        queries = log_reader.read_recent_logs(minutes) if log_reader else []
        
        # Convert datetime objects to strings for JSON serialization
        for query in queries:
            query['timestamp'] = query['timestamp'].isoformat()
            
        return jsonify({
            'queries': queries[:100],  # Limit to 100 most recent
            'total_count': len(queries)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/blocked_ips')
def get_blocked_ips():
    """Get blocked IPs"""
    try:
        blocked_ips = firewall_controller.get_blocked_ips() if firewall_controller else {}
        
        # Convert to serializable format
        blocked_list = []
        for ip, blocked_ip in blocked_ips.items():
            blocked_list.append({
                'ip': blocked_ip.ip,
                'timestamp': blocked_ip.timestamp.isoformat(),
                'reason': blocked_ip.reason,
                'auto_unblock_time': blocked_ip.auto_unblock_time.isoformat() 
                                   if blocked_ip.auto_unblock_time else None
            })
            
        return jsonify({'blocked_ips': blocked_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/blocked_domains')
def get_blocked_domains():
    """Get blocked domains"""
    try:
        blocked_domains = rpz_manager.get_blocked_domains() if rpz_manager else {}
        
        # Convert to serializable format
        blocked_list = []
        for domain, blocked_domain in blocked_domains.items():
            blocked_list.append({
                'domain': blocked_domain.domain,
                'timestamp': blocked_domain.timestamp.isoformat(),
                'reason': blocked_domain.reason,
                'policy': blocked_domain.policy,
                'auto_unblock_time': blocked_domain.auto_unblock_time.isoformat() 
                                   if blocked_domain.auto_unblock_time else None
            })
            
        return jsonify({'blocked_domains': blocked_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent_alerts')
def get_recent_alerts():
    """Get recent alerts"""
    try:
        hours = request.args.get('hours', 24, type=int)
        alerts = alert_sender.get_recent_alerts(hours) if alert_sender else []
        
        # Convert to serializable format
        alert_list = []
        for alert in alerts:
            alert_list.append({
                'timestamp': alert.timestamp.isoformat(),
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'source_ip': alert.source_ip,
                'message': alert.message,
                'actions_taken': alert.actions_taken
            })
            
        return jsonify({'alerts': alert_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/query_analysis')
def get_query_analysis():
    """Analyze recent queries"""
    try:
        minutes = request.args.get('minutes', 15, type=int)
        queries = log_reader.read_recent_logs(minutes) if log_reader else []
        
        if not queries:
            return jsonify({'analysis': {}})
            
        analysis = log_reader.analyze_queries(queries)
        
        # Convert Counter objects to regular dicts for JSON serialization
        analysis['query_types'] = dict(analysis['query_types'])
        analysis['queries_per_ip'] = dict(analysis['queries_per_ip'].most_common(10))
        analysis['queries_per_domain'] = dict(analysis['queries_per_domain'].most_common(10))
        analysis['time_distribution'] = dict(analysis['time_distribution'])
        
        # Convert datetime objects
        for query in analysis['suspicious_domains']:
            query['timestamp'] = query['timestamp'].isoformat()
            
        for query in analysis['amplification_queries']:
            query['timestamp'] = query['timestamp'].isoformat()
            
        return jsonify({'analysis': analysis})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/unblock_ip', methods=['POST'])
def unblock_ip():
    """Unblock an IP address"""
    try:
        data = request.get_json()
        ip = data.get('ip')
        reason = data.get('reason', 'Manual unblock via dashboard')
        
        if not ip:
            return jsonify({'error': 'IP address required'}), 400
            
        success = firewall_controller.unblock_ip(ip, reason) if firewall_controller else False
        
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/unblock_domain', methods=['POST'])
def unblock_domain():
    """Unblock a domain"""
    try:
        data = request.get_json()
        domain = data.get('domain')
        reason = data.get('reason', 'Manual unblock via dashboard')
        
        if not domain:
            return jsonify({'error': 'Domain required'}), 400
            
        success = rpz_manager.unblock_domain(domain, reason) if rpz_manager else False
        
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/block_ip', methods=['POST'])
def block_ip():
    """Block an IP address"""
    try:
        data = request.get_json()
        ip = data.get('ip')
        reason = data.get('reason', 'Manual block via dashboard')
        duration = data.get('duration_hours')
        
        if not ip:
            return jsonify({'error': 'IP address required'}), 400
            
        success = firewall_controller.block_ip(ip, reason, duration) if firewall_controller else False
        
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/block_domain', methods=['POST'])
def block_domain():
    """Block a domain"""
    try:
        data = request.get_json()
        domain = data.get('domain')
        reason = data.get('reason', 'Manual block via dashboard')
        policy = data.get('policy', 'nxdomain')
        duration = data.get('duration_hours')
        
        if not domain:
            return jsonify({'error': 'Domain required'}), 400
            
        success = rpz_manager.block_domain(domain, reason, policy, 300, duration) if rpz_manager else False
        
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test_dga', methods=['POST'])
def test_dga():
    """Test DGA classification for a domain"""
    try:
        data = request.get_json()
        domain = data.get('domain')
        
        if not domain:
            return jsonify({'error': 'Domain required'}), 400
            
        if not dga_classifier:
            return jsonify({'error': 'DGA classifier not available'}), 400
            
        result = dga_classifier.classify_domain(domain)
        
        return jsonify({
            'domain': result.domain,
            'is_dga': result.is_dga,
            'confidence': result.confidence,
            'algorithm': result.algorithm,
            'reason': result.reason,
            'features': result.features
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Create templates directory and basic template
def create_template():
    """Create basic HTML template"""
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    template_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DNS DDoS Monitor Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="#">DNS DDoS Monitor</a>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row">
            <div class="col-md-3">
                <div class="card bg-primary text-white">
                    <div class="card-body">
                        <h5>Blocked IPs</h5>
                        <h2 id="blocked-ips-count">-</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-warning text-white">
                    <div class="card-body">
                        <h5>Blocked Domains</h5>
                        <h2 id="blocked-domains-count">-</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-danger text-white">
                    <div class="card-body">
                        <h5>Recent Alerts</h5>
                        <h2 id="alerts-count">-</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-success text-white">
                    <div class="card-body">
                        <h5>Queries/Min</h5>
                        <h2 id="queries-rate">-</h2>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mt-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Recent Blocked IPs</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>IP Address</th>
                                        <th>Reason</th>
                                        <th>Time</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody id="blocked-ips-table">
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Recent Blocked Domains</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Domain</th>
                                        <th>Reason</th>
                                        <th>Time</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody id="blocked-domains-table">
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mt-4">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <h5>Recent Alerts</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Time</th>
                                        <th>Type</th>
                                        <th>Severity</th>
                                        <th>Source IP</th>
                                        <th>Message</th>
                                    </tr>
                                </thead>
                                <tbody id="alerts-table">
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function updateDashboard() {
            // Update statistics
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('blocked-ips-count').textContent = 
                        data.firewall?.total_blocked_ips || 0;
                    document.getElementById('blocked-domains-count').textContent = 
                        data.rpz?.total_blocked_domains || 0;
                    document.getElementById('alerts-count').textContent = 
                        data.alerts?.alerts_last_hour || 0;
                });

            // Update blocked IPs
            fetch('/api/blocked_ips')
                .then(response => response.json())
                .then(data => {
                    const tbody = document.getElementById('blocked-ips-table');
                    tbody.innerHTML = '';
                    data.blocked_ips?.slice(0, 10).forEach(ip => {
                        const row = tbody.insertRow();
                        row.innerHTML = `
                            <td>${ip.ip}</td>
                            <td>${ip.reason}</td>
                            <td>${new Date(ip.timestamp).toLocaleString()}</td>
                            <td><button class="btn btn-sm btn-outline-success" onclick="unblockIP('${ip.ip}')">Unblock</button></td>
                        `;
                    });
                });

            // Update blocked domains
            fetch('/api/blocked_domains')
                .then(response => response.json())
                .then(data => {
                    const tbody = document.getElementById('blocked-domains-table');
                    tbody.innerHTML = '';
                    data.blocked_domains?.slice(0, 10).forEach(domain => {
                        const row = tbody.insertRow();
                        row.innerHTML = `
                            <td>${domain.domain}</td>
                            <td>${domain.reason}</td>
                            <td>${new Date(domain.timestamp).toLocaleString()}</td>
                            <td><button class="btn btn-sm btn-outline-success" onclick="unblockDomain('${domain.domain}')">Unblock</button></td>
                        `;
                    });
                });

            // Update alerts
            fetch('/api/recent_alerts')
                .then(response => response.json())
                .then(data => {
                    const tbody = document.getElementById('alerts-table');
                    tbody.innerHTML = '';
                    data.alerts?.slice(0, 10).forEach(alert => {
                        const row = tbody.insertRow();
                        const severityClass = alert.severity === 'HIGH' ? 'text-danger' : 
                                            alert.severity === 'MEDIUM' ? 'text-warning' : 'text-info';
                        row.innerHTML = `
                            <td>${new Date(alert.timestamp).toLocaleString()}</td>
                            <td>${alert.alert_type}</td>
                            <td class="${severityClass}">${alert.severity}</td>
                            <td>${alert.source_ip}</td>
                            <td>${alert.message}</td>
                        `;
                    });
                });
        }

        function unblockIP(ip) {
            if (confirm(`Are you sure you want to unblock IP ${ip}?`)) {
                fetch('/api/unblock_ip', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ip: ip, reason: 'Manual unblock via dashboard'})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('IP unblocked successfully');
                        updateDashboard();
                    } else {
                        alert('Failed to unblock IP');
                    }
                });
            }
        }

        function unblockDomain(domain) {
            if (confirm(`Are you sure you want to unblock domain ${domain}?`)) {
                fetch('/api/unblock_domain', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({domain: domain, reason: 'Manual unblock via dashboard'})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Domain unblocked successfully');
                        updateDashboard();
                    } else {
                        alert('Failed to unblock domain');
                    }
                });
            }
        }

        // Update dashboard every 30 seconds
        updateDashboard();
        setInterval(updateDashboard, 30000);
    </script>
</body>
</html>'''
    
    template_file = os.path.join(template_dir, 'dashboard.html')
    with open(template_file, 'w') as f:
        f.write(template_content)

if __name__ == '__main__':
    # Load configuration and initialize components
    load_config()
    initialize_components()
    create_template()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)