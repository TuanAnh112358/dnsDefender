#!/usr/bin/env python3
"""
DNS DDoS Monitor - Công cụ giám sát và phát hiện tấn công DDoS DNS
Tác giả: [Tên sinh viên]
"""

import os
import re
import sys
import time
import json
import logging
import argparse
import threading
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path

import pandas as pd
import numpy as np
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from colorama import init, Fore, Back, Style
from tabulate import tabulate

# Khởi tạo colorama
init()

class DNSLogAnalyzer:
    """Phân tích log DNS để phát hiện các bất thường"""
    
    def __init__(self, config_file='config/monitor_config.json'):
        self.config = self.load_config(config_file)
        self.setup_logging()
        
        # Thống kê thời gian thực
        self.query_stats = defaultdict(int)
        self.client_stats = defaultdict(lambda: {'count': 0, 'last_seen': None})
        self.domain_stats = defaultdict(int)
        self.attack_alerts = []
        
        # Ngưỡng cảnh báo
        self.thresholds = self.config.get('thresholds', {
            'queries_per_second': 50,
            'queries_per_minute': 300,
            'unique_domains_per_client': 100,
            'nxdomain_ratio': 0.7,
            'amplification_size': 512
        })
        
    def load_config(self, config_file):
        """Tải cấu hình từ file JSON"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.get_default_config()
    
    def get_default_config(self):
        """Cấu hình mặc định"""
        return {
            'log_files': [
                '/var/log/dns_monitor/query.log',
                '/var/log/dns_monitor/security.log',
                '/var/log/syslog'
            ],
            'output_dir': 'logs',
            'alert_file': 'logs/alerts.json',
            'stats_file': 'logs/stats.json',
            'thresholds': {
                'queries_per_second': 50,
                'queries_per_minute': 300,
                'unique_domains_per_client': 100,
                'nxdomain_ratio': 0.7,
                'amplification_size': 512
            }
        }
    
    def setup_logging(self):
        """Thiết lập logging"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('logs/dns_monitor.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('DNSMonitor')
    
    def parse_bind_log(self, log_line):
        """Phân tích log line từ BIND9"""
        patterns = {
            'query': r'client ([0-9.]+)#(\d+) \(([^)]+)\): query: (\S+) IN (\S+)',
            'rate_limit': r'rate-limit.*client ([0-9.]+)#(\d+)',
            'nxdomain': r'client ([0-9.]+)#(\d+).*NXDOMAIN',
            'security': r'security.*client ([0-9.]+)#(\d+)',
        }
        
        for log_type, pattern in patterns.items():
            match = re.search(pattern, log_line)
            if match:
                return {
                    'type': log_type,
                    'client_ip': match.group(1),
                    'client_port': match.group(2) if len(match.groups()) > 1 else None,
                    'domain': match.group(3) if log_type == 'query' and len(match.groups()) > 2 else None,
                    'query_type': match.group(5) if log_type == 'query' and len(match.groups()) > 4 else None,
                    'timestamp': datetime.now(),
                    'raw_line': log_line
                }
        return None
    
    def analyze_query(self, query_data):
        """Phân tích một truy vấn DNS"""
        if not query_data:
            return
            
        client_ip = query_data['client_ip']
        domain = query_data.get('domain', '')
        query_type = query_data.get('query_type', '')
        
        # Cập nhật thống kê
        self.client_stats[client_ip]['count'] += 1
        self.client_stats[client_ip]['last_seen'] = query_data['timestamp']
        
        if domain:
            self.domain_stats[domain] += 1
        
        # Kiểm tra các loại tấn công
        self.check_flood_attack(client_ip, query_data)
        self.check_nxdomain_attack(client_ip, query_data)
        self.check_amplification_attack(client_ip, query_data)
    
    def check_flood_attack(self, client_ip, query_data):
        """Kiểm tra tấn công Flood"""
        now = datetime.now()
        
        # Đếm queries trong 1 phút qua
        recent_queries = sum(1 for stats in self.client_stats.values() 
                           if stats['last_seen'] and 
                           (now - stats['last_seen']).seconds < 60)
        
        if self.client_stats[client_ip]['count'] > self.thresholds['queries_per_minute']:
            alert = {
                'type': 'DNS_FLOOD',
                'client_ip': client_ip,
                'query_count': self.client_stats[client_ip]['count'],
                'threshold': self.thresholds['queries_per_minute'],
                'timestamp': now.isoformat(),
                'severity': 'HIGH'
            }
            self.add_alert(alert)
    
    def check_nxdomain_attack(self, client_ip, query_data):
        """Kiểm tra tấn công NXDOMAIN"""
        if query_data['type'] == 'nxdomain':
            alert = {
                'type': 'NXDOMAIN_ATTACK',
                'client_ip': client_ip,
                'domain': query_data.get('domain', 'unknown'),
                'timestamp': datetime.now().isoformat(),
                'severity': 'MEDIUM'
            }
            self.add_alert(alert)
    
    def check_amplification_attack(self, client_ip, query_data):
        """Kiểm tra tấn công Amplification"""
        if query_data.get('query_type') == 'ANY':
            alert = {
                'type': 'AMPLIFICATION_ATTACK',
                'client_ip': client_ip,
                'query_type': 'ANY',
                'domain': query_data.get('domain', 'unknown'),
                'timestamp': datetime.now().isoformat(),
                'severity': 'HIGH'
            }
            self.add_alert(alert)
    
    def add_alert(self, alert):
        """Thêm cảnh báo mới"""
        self.attack_alerts.append(alert)
        self.logger.warning(f"ALERT: {alert['type']} from {alert['client_ip']}")
        
        # Lưu alert vào file
        self.save_alert(alert)
        
        # Hiển thị alert trên console
        self.display_alert(alert)
    
    def display_alert(self, alert):
        """Hiển thị cảnh báo với màu sắc"""
        color = Fore.RED if alert['severity'] == 'HIGH' else Fore.YELLOW
        print(f"\n{color}{'='*60}{Style.RESET_ALL}")
        print(f"{color}[ALERT] {alert['type']}{Style.RESET_ALL}")
        print(f"IP: {alert['client_ip']}")
        print(f"Time: {alert['timestamp']}")
        print(f"Severity: {alert['severity']}")
        if 'query_count' in alert:
            print(f"Query Count: {alert['query_count']}")
        if 'domain' in alert:
            print(f"Domain: {alert['domain']}")
        print(f"{color}{'='*60}{Style.RESET_ALL}\n")
    
    def save_alert(self, alert):
        """Lưu cảnh báo vào file"""
        alert_file = self.config.get('alert_file', 'logs/alerts.json')
        os.makedirs(os.path.dirname(alert_file), exist_ok=True)
        
        try:
            with open(alert_file, 'a') as f:
                f.write(json.dumps(alert) + '\n')
        except Exception as e:
            self.logger.error(f"Không thể lưu alert: {e}")
    
    def get_top_clients(self, limit=10):
        """Lấy danh sách client có nhiều truy vấn nhất"""
        sorted_clients = sorted(
            self.client_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        return sorted_clients[:limit]
    
    def get_top_domains(self, limit=10):
        """Lấy danh sách domain được truy vấn nhiều nhất"""
        return Counter(self.domain_stats).most_common(limit)
    
    def display_stats(self):
        """Hiển thị thống kê thời gian thực"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}DNS DDoS Monitor - Real-time Statistics{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Alerts: {len(self.attack_alerts)}")
        print(f"Active Clients: {len(self.client_stats)}")
        print(f"Unique Domains: {len(self.domain_stats)}")
        
        # Top clients
        print(f"\n{Fore.GREEN}Top Clients by Query Count:{Style.RESET_ALL}")
        top_clients = self.get_top_clients()
        if top_clients:
            headers = ['IP Address', 'Query Count', 'Last Seen']
            table_data = []
            for ip, stats in top_clients:
                last_seen = stats['last_seen'].strftime('%H:%M:%S') if stats['last_seen'] else 'N/A'
                table_data.append([ip, stats['count'], last_seen])
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        # Top domains
        print(f"\n{Fore.GREEN}Top Queried Domains:{Style.RESET_ALL}")
        top_domains = self.get_top_domains()
        if top_domains:
            headers = ['Domain', 'Query Count']
            table_data = [[domain, count] for domain, count in top_domains]
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        # Recent alerts
        print(f"\n{Fore.RED}Recent Alerts (Last 10):{Style.RESET_ALL}")
        recent_alerts = self.attack_alerts[-10:] if self.attack_alerts else []
        if recent_alerts:
            headers = ['Time', 'Type', 'IP', 'Severity']
            table_data = []
            for alert in recent_alerts:
                time_str = alert['timestamp'].split('T')[1][:8]
                table_data.append([
                    time_str,
                    alert['type'],
                    alert['client_ip'],
                    alert['severity']
                ])
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
        else:
            print("No alerts yet.")

class LogFileWatcher(FileSystemEventHandler):
    """Theo dõi thay đổi file log"""
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.log'):
            self.process_new_lines(event.src_path)
    
    def process_new_lines(self, file_path):
        """Xử lý các dòng mới trong file log"""
        try:
            with open(file_path, 'r') as f:
                f.seek(0, 2)  # Đi đến cuối file
                while True:
                    line = f.readline()
                    if not line:
                        break
                    query_data = self.analyzer.parse_bind_log(line.strip())
                    if query_data:
                        self.analyzer.analyze_query(query_data)
        except Exception as e:
            logging.error(f"Lỗi khi đọc file {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description='DNS DDoS Monitor')
    parser.add_argument('--config', default='config/monitor_config.json',
                       help='File cấu hình')
    parser.add_argument('--mode', choices=['monitor', 'analyze'], default='monitor',
                       help='Chế độ hoạt động')
    parser.add_argument('--log-file', help='File log cụ thể để phân tích')
    
    args = parser.parse_args()
    
    # Tạo thư mục cần thiết
    os.makedirs('logs', exist_ok=True)
    
    analyzer = DNSLogAnalyzer(args.config)
    
    if args.mode == 'monitor':
        print(f"{Fore.GREEN}Khởi động DNS DDoS Monitor...{Style.RESET_ALL}")
        
        # Thiết lập file watcher
        event_handler = LogFileWatcher(analyzer)
        observer = Observer()
        
        # Theo dõi các file log
        for log_file in analyzer.config['log_files']:
            if os.path.exists(log_file):
                observer.schedule(event_handler, os.path.dirname(log_file), recursive=False)
                print(f"Đang theo dõi: {log_file}")
        
        observer.start()
        
        try:
            while True:
                analyzer.display_stats()
                time.sleep(5)  # Cập nhật mỗi 5 giây
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Đang dừng monitor...{Style.RESET_ALL}")
            observer.stop()
        
        observer.join()
    
    elif args.mode == 'analyze':
        if args.log_file and os.path.exists(args.log_file):
            print(f"Phân tích file: {args.log_file}")
            with open(args.log_file, 'r') as f:
                for line in f:
                    query_data = analyzer.parse_bind_log(line.strip())
                    if query_data:
                        analyzer.analyze_query(query_data)
            
            analyzer.display_stats()
        else:
            print("Vui lòng chỉ định file log hợp lệ với --log-file")

if __name__ == '__main__':
    main()