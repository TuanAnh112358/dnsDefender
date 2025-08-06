#!/usr/bin/env python3
"""
DNS DDoS Monitor Dashboard - Web interface để hiển thị thống kê
"""

import os
import json
import sys
from datetime import datetime, timedelta
from collections import Counter, defaultdict

from flask import Flask, render_template, jsonify, request
import plotly.graph_objs as go
import plotly.utils

# Thêm thư mục src vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from dns_monitor import DNSLogAnalyzer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dns-monitor-secret-key'

# Global analyzer instance
analyzer = None

def init_analyzer():
    """Khởi tạo DNS analyzer"""
    global analyzer
    config_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'monitor_config.json')
    analyzer = DNSLogAnalyzer(config_file)
    
    # Load existing data nếu có
    load_existing_data()

def load_existing_data():
    """Tải dữ liệu có sẵn từ log files"""
    global analyzer
    
    alert_file = analyzer.config.get('alert_file', 'logs/alerts.json')
    if os.path.exists(alert_file):
        try:
            with open(alert_file, 'r') as f:
                for line in f:
                    if line.strip():
                        alert = json.loads(line.strip())
                        analyzer.attack_alerts.append(alert)
        except Exception as e:
            print(f"Lỗi khi tải alerts: {e}")

@app.route('/')
def index():
    """Trang chủ dashboard"""
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """API trả về thống kê tổng quan"""
    global analyzer
    
    if not analyzer:
        return jsonify({'error': 'Analyzer not initialized'})
    
    # Thống kê cơ bản
    stats = {
        'total_alerts': len(analyzer.attack_alerts),
        'active_clients': len(analyzer.client_stats),
        'unique_domains': len(analyzer.domain_stats),
        'last_update': datetime.now().isoformat()
    }
    
    # Thống kê theo loại alert
    alert_types = Counter([alert['type'] for alert in analyzer.attack_alerts])
    stats['alert_types'] = dict(alert_types)
    
    # Thống kê theo severity
    alert_severity = Counter([alert['severity'] for alert in analyzer.attack_alerts])
    stats['alert_severity'] = dict(alert_severity)
    
    return jsonify(stats)

@app.route('/api/top_clients')
def get_top_clients():
    """API trả về top clients"""
    global analyzer
    
    if not analyzer:
        return jsonify([])
    
    top_clients = analyzer.get_top_clients(20)
    
    result = []
    for ip, stats in top_clients:
        result.append({
            'ip': ip,
            'query_count': stats['count'],
            'last_seen': stats['last_seen'].isoformat() if stats['last_seen'] else None
        })
    
    return jsonify(result)

@app.route('/api/top_domains')
def get_top_domains():
    """API trả về top domains"""
    global analyzer
    
    if not analyzer:
        return jsonify([])
    
    top_domains = analyzer.get_top_domains(20)
    
    result = []
    for domain, count in top_domains:
        result.append({
            'domain': domain,
            'query_count': count
        })
    
    return jsonify(result)

@app.route('/api/recent_alerts')
def get_recent_alerts():
    """API trả về alerts gần đây"""
    global analyzer
    
    if not analyzer:
        return jsonify([])
    
    limit = request.args.get('limit', 50, type=int)
    recent_alerts = analyzer.attack_alerts[-limit:] if analyzer.attack_alerts else []
    
    # Reverse để hiển thị mới nhất trước
    recent_alerts.reverse()
    
    return jsonify(recent_alerts)

@app.route('/api/alerts_timeline')
def get_alerts_timeline():
    """API trả về timeline của alerts"""
    global analyzer
    
    if not analyzer:
        return jsonify({'data': [], 'layout': {}})
    
    # Nhóm alerts theo giờ
    hourly_alerts = defaultdict(int)
    
    for alert in analyzer.attack_alerts:
        try:
            timestamp = datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00'))
            hour_key = timestamp.strftime('%Y-%m-%d %H:00')
            hourly_alerts[hour_key] += 1
        except:
            continue
    
    # Tạo dữ liệu cho biểu đồ
    sorted_hours = sorted(hourly_alerts.keys())
    counts = [hourly_alerts[hour] for hour in sorted_hours]
    
    trace = go.Scatter(
        x=sorted_hours,
        y=counts,
        mode='lines+markers',
        name='Alerts per Hour',
        line=dict(color='red', width=2),
        marker=dict(size=6)
    )
    
    layout = go.Layout(
        title='DNS Attacks Timeline',
        xaxis=dict(title='Time'),
        yaxis=dict(title='Number of Alerts'),
        hovermode='closest'
    )
    
    fig = go.Figure(data=[trace], layout=layout)
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return graphJSON

@app.route('/api/attack_types_chart')
def get_attack_types_chart():
    """API trả về biểu đồ các loại tấn công"""
    global analyzer
    
    if not analyzer:
        return jsonify({'data': [], 'layout': {}})
    
    # Đếm các loại tấn công
    attack_types = Counter([alert['type'] for alert in analyzer.attack_alerts])
    
    if not attack_types:
        return jsonify({'data': [], 'layout': {}})
    
    trace = go.Pie(
        labels=list(attack_types.keys()),
        values=list(attack_types.values()),
        hole=0.3
    )
    
    layout = go.Layout(
        title='Attack Types Distribution'
    )
    
    fig = go.Figure(data=[trace], layout=layout)
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return graphJSON

@app.route('/api/top_attackers_chart')
def get_top_attackers_chart():
    """API trả về biểu đồ top attackers"""
    global analyzer
    
    if not analyzer:
        return jsonify({'data': [], 'layout': {}})
    
    # Đếm alerts theo IP
    attacker_ips = Counter([alert['client_ip'] for alert in analyzer.attack_alerts])
    
    if not attacker_ips:
        return jsonify({'data': [], 'layout': {}})
    
    # Lấy top 10
    top_attackers = attacker_ips.most_common(10)
    
    ips = [ip for ip, count in top_attackers]
    counts = [count for ip, count in top_attackers]
    
    trace = go.Bar(
        x=ips,
        y=counts,
        marker=dict(color='orange')
    )
    
    layout = go.Layout(
        title='Top Attacking IPs',
        xaxis=dict(title='IP Address'),
        yaxis=dict(title='Number of Attacks')
    )
    
    fig = go.Figure(data=[trace], layout=layout)
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return graphJSON

@app.route('/api/query_volume_chart')
def get_query_volume_chart():
    """API trả về biểu đồ volume truy vấn"""
    global analyzer
    
    if not analyzer:
        return jsonify({'data': [], 'layout': {}})
    
    top_clients = analyzer.get_top_clients(15)
    
    if not top_clients:
        return jsonify({'data': [], 'layout': {}})
    
    ips = [ip for ip, stats in top_clients]
    counts = [stats['count'] for ip, stats in top_clients]
    
    trace = go.Bar(
        x=ips,
        y=counts,
        marker=dict(color='blue')
    )
    
    layout = go.Layout(
        title='Query Volume by Client IP',
        xaxis=dict(title='Client IP', tickangle=45),
        yaxis=dict(title='Query Count')
    )
    
    fig = go.Figure(data=[trace], layout=layout)
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return graphJSON

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    print("Khởi động DNS DDoS Monitor Dashboard...")
    
    # Khởi tạo analyzer
    init_analyzer()
    
    # Chạy Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)