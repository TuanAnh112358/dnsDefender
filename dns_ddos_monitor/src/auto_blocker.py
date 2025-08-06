#!/usr/bin/env python3
"""
Auto IP Blocker - Tự động chặn IP dựa trên DNS alerts
"""

import os
import json
import subprocess
import time
import logging
from datetime import datetime, timedelta
from collections import defaultdict

class IPBlocker:
    def __init__(self, config_file='config/blocker_config.json'):
        self.config = self.load_config(config_file)
        self.setup_logging()
        self.blocked_ips = set()
        self.ip_violations = defaultdict(int)
        
    def load_config(self, config_file):
        """Tải cấu hình từ file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.get_default_config()
    
    def get_default_config(self):
        """Cấu hình mặc định"""
        return {
            'alert_file': 'logs/alerts.json',
            'whitelist': ['127.0.0.1', '::1', '192.168.1.0/24'],
            'thresholds': {
                'max_violations': 5,
                'time_window': 300,  # 5 minutes
                'block_duration': 3600  # 1 hour
            },
            'iptables': {
                'chain': 'INPUT',
                'target': 'DROP',
                'comment': 'DNS-DDoS-Block'
            }
        }
    
    def setup_logging(self):
        """Thiết lập logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/auto_blocker.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('AutoBlocker')
    
    def is_whitelisted(self, ip):
        """Kiểm tra IP có trong whitelist không"""
        import ipaddress
        
        try:
            ip_obj = ipaddress.ip_address(ip)
            for whitelist_entry in self.config['whitelist']:
                if '/' in whitelist_entry:
                    # Subnet
                    network = ipaddress.ip_network(whitelist_entry, strict=False)
                    if ip_obj in network:
                        return True
                else:
                    # Single IP
                    if str(ip_obj) == whitelist_entry:
                        return True
        except ValueError:
            pass
        
        return False
    
    def run_iptables_command(self, command):
        """Chạy lệnh iptables"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info(f"IPTables command executed: {command}")
                return True
            else:
                self.logger.error(f"IPTables command failed: {command}, Error: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Error executing iptables command: {e}")
            return False
    
    def block_ip(self, ip, reason="DNS DDoS Attack"):
        """Chặn IP bằng iptables"""
        if ip in self.blocked_ips:
            self.logger.info(f"IP {ip} already blocked")
            return True
        
        if self.is_whitelisted(ip):
            self.logger.info(f"IP {ip} is whitelisted, skipping block")
            return False
        
        # Tạo rule iptables
        chain = self.config['iptables']['chain']
        target = self.config['iptables']['target']
        comment = self.config['iptables']['comment']
        
        command = f'iptables -I {chain} -s {ip} -j {target} -m comment --comment "{comment}-{ip}"'
        
        if self.run_iptables_command(command):
            self.blocked_ips.add(ip)
            self.logger.warning(f"BLOCKED IP: {ip} - Reason: {reason}")
            
            # Ghi log block
            self.log_block_action(ip, reason, 'BLOCK')
            return True
        
        return False
    
    def unblock_ip(self, ip):
        """Bỏ chặn IP"""
        if ip not in self.blocked_ips:
            self.logger.info(f"IP {ip} is not blocked")
            return True
        
        chain = self.config['iptables']['chain']
        target = self.config['iptables']['target']
        comment = self.config['iptables']['comment']
        
        command = f'iptables -D {chain} -s {ip} -j {target} -m comment --comment "{comment}-{ip}"'
        
        if self.run_iptables_command(command):
            self.blocked_ips.discard(ip)
            self.logger.info(f"UNBLOCKED IP: {ip}")
            
            # Ghi log unblock
            self.log_block_action(ip, "Automatic unblock", 'UNBLOCK')
            return True
        
        return False
    
    def log_block_action(self, ip, reason, action):
        """Ghi log hành động block/unblock"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'ip': ip,
            'reason': reason
        }
        
        try:
            with open('logs/block_actions.json', 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            self.logger.error(f"Error logging block action: {e}")
    
    def process_alerts(self):
        """Xử lý alerts từ file"""
        alert_file = self.config['alert_file']
        
        if not os.path.exists(alert_file):
            self.logger.info(f"Alert file {alert_file} not found")
            return
        
        try:
            with open(alert_file, 'r') as f:
                lines = f.readlines()
            
            # Chỉ xử lý alerts trong time window
            time_window = self.config['thresholds']['time_window']
            cutoff_time = datetime.now() - timedelta(seconds=time_window)
            
            recent_alerts = []
            for line in lines:
                if line.strip():
                    try:
                        alert = json.loads(line.strip())
                        alert_time = datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00'))
                        
                        if alert_time > cutoff_time:
                            recent_alerts.append(alert)
                    except:
                        continue
            
            # Đếm violations theo IP
            ip_violations = defaultdict(int)
            for alert in recent_alerts:
                ip = alert.get('client_ip')
                if ip and not self.is_whitelisted(ip):
                    # Tăng trọng số theo severity
                    weight = 3 if alert.get('severity') == 'HIGH' else 1
                    ip_violations[ip] += weight
            
            # Kiểm tra và chặn IPs vượt ngưỡng
            max_violations = self.config['thresholds']['max_violations']
            for ip, violations in ip_violations.items():
                if violations >= max_violations:
                    reason = f"Exceeded threshold: {violations} violations in {time_window}s"
                    self.block_ip(ip, reason)
        
        except Exception as e:
            self.logger.error(f"Error processing alerts: {e}")
    
    def cleanup_expired_blocks(self):
        """Dọn dẹp các IP đã hết thời gian chặn"""
        # Đọc log block actions để tìm IPs cần unblock
        block_duration = self.config['thresholds']['block_duration']
        cutoff_time = datetime.now() - timedelta(seconds=block_duration)
        
        try:
            if os.path.exists('logs/block_actions.json'):
                with open('logs/block_actions.json', 'r') as f:
                    for line in f:
                        if line.strip():
                            try:
                                action = json.loads(line.strip())
                                if action['action'] == 'BLOCK':
                                    block_time = datetime.fromisoformat(action['timestamp'])
                                    if block_time < cutoff_time:
                                        ip = action['ip']
                                        if ip in self.blocked_ips:
                                            self.unblock_ip(ip)
                            except:
                                continue
        except Exception as e:
            self.logger.error(f"Error cleaning up expired blocks: {e}")
    
    def get_current_blocks(self):
        """Lấy danh sách IP đang bị chặn từ iptables"""
        try:
            result = subprocess.run(
                'iptables -L INPUT -n --line-numbers | grep "DNS-DDoS-Block"',
                shell=True, capture_output=True, text=True
            )
            
            blocked_ips = set()
            for line in result.stdout.split('\n'):
                if 'DNS-DDoS-Block' in line:
                    # Parse IP từ output
                    parts = line.split()
                    for part in parts:
                        if '/' in part or '.' in part:
                            ip = part.split('/')[0]
                            if self.is_valid_ip(ip):
                                blocked_ips.add(ip)
                                break
            
            self.blocked_ips = blocked_ips
            return blocked_ips
        
        except Exception as e:
            self.logger.error(f"Error getting current blocks: {e}")
            return set()
    
    def is_valid_ip(self, ip):
        """Kiểm tra IP hợp lệ"""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def run_monitoring_loop(self, interval=60):
        """Chạy vòng lặp giám sát"""
        self.logger.info("Starting auto blocker monitoring loop...")
        
        # Lấy danh sách IP đang bị chặn
        self.get_current_blocks()
        
        while True:
            try:
                self.logger.info("Processing alerts and checking for violations...")
                
                # Xử lý alerts mới
                self.process_alerts()
                
                # Dọn dẹp blocks hết hạn
                self.cleanup_expired_blocks()
                
                # Hiển thị thống kê
                self.show_stats()
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval)
    
    def show_stats(self):
        """Hiển thị thống kê"""
        blocked_count = len(self.blocked_ips)
        self.logger.info(f"Currently blocking {blocked_count} IPs: {list(self.blocked_ips)}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='DNS DDoS Auto IP Blocker')
    parser.add_argument('--config', default='config/blocker_config.json',
                       help='Configuration file')
    parser.add_argument('--interval', type=int, default=60,
                       help='Monitoring interval in seconds')
    parser.add_argument('--block-ip', help='Manually block an IP')
    parser.add_argument('--unblock-ip', help='Manually unblock an IP')
    parser.add_argument('--list-blocked', action='store_true',
                       help='List currently blocked IPs')
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up expired blocks and exit')
    
    args = parser.parse_args()
    
    blocker = IPBlocker(args.config)
    
    if args.block_ip:
        blocker.block_ip(args.block_ip, "Manual block")
    elif args.unblock_ip:
        blocker.unblock_ip(args.unblock_ip)
    elif args.list_blocked:
        blocked_ips = blocker.get_current_blocks()
        print(f"Currently blocked IPs: {list(blocked_ips)}")
    elif args.cleanup:
        blocker.cleanup_expired_blocks()
    else:
        blocker.run_monitoring_loop(args.interval)

if __name__ == '__main__':
    main()