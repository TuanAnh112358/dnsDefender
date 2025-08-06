#!/usr/bin/env python3
"""
Firewall Controller Module
Manages automatic IP blocking using iptables for DDoS mitigation
"""

import subprocess
import logging
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass

@dataclass
class BlockedIP:
    """Information about a blocked IP"""
    ip: str
    timestamp: datetime
    reason: str
    rule_id: Optional[str] = None
    auto_unblock_time: Optional[datetime] = None

class FirewallController:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.blocked_ips = {}  # ip -> BlockedIP
        self.chain_name = "DNS_DDOS_BLOCK"
        
        # Initialize iptables chain
        self._initialize_chain()
        
        # Load existing blocks
        self._load_blocked_ips()
        
    def _initialize_chain(self):
        """Initialize custom iptables chain for DNS DDoS blocking"""
        try:
            # Create custom chain if it doesn't exist
            result = subprocess.run([
                'iptables', '-t', 'filter', '-N', self.chain_name
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Created iptables chain: {self.chain_name}")
            elif "already exists" in result.stderr:
                self.logger.info(f"Chain {self.chain_name} already exists")
            else:
                self.logger.warning(f"Error creating chain: {result.stderr}")
                
            # Add jump rule to our chain in INPUT if not exists
            check_result = subprocess.run([
                'iptables', '-t', 'filter', '-C', 'INPUT', 
                '-p', 'udp', '--dport', '53', '-j', self.chain_name
            ], capture_output=True, text=True)
            
            if check_result.returncode != 0:
                # Rule doesn't exist, add it
                subprocess.run([
                    'iptables', '-t', 'filter', '-I', 'INPUT', 
                    '-p', 'udp', '--dport', '53', '-j', self.chain_name
                ], check=True)
                self.logger.info("Added jump rule to DNS_DDOS_BLOCK chain")
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to initialize iptables chain: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error initializing firewall: {e}")
            
    def _load_blocked_ips(self):
        """Load previously blocked IPs from file"""
        blocked_file = self.config.get('blocked_ip_log', 'data/blocked_ips.txt')
        try:
            with open(blocked_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('#')
                        if parts:
                            ip = parts[0].strip()
                            reason = parts[1].strip() if len(parts) > 1 else "Unknown"
                            
                            # Check if IP is still blocked in iptables
                            if self._is_ip_blocked(ip):
                                self.blocked_ips[ip] = BlockedIP(
                                    ip=ip,
                                    timestamp=datetime.now(),
                                    reason=reason
                                )
                                
            self.logger.info(f"Loaded {len(self.blocked_ips)} blocked IPs from file")
            
        except FileNotFoundError:
            self.logger.info("No existing blocked IPs file found")
        except Exception as e:
            self.logger.error(f"Error loading blocked IPs: {e}")
            
    def _is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is currently blocked in iptables"""
        try:
            result = subprocess.run([
                'iptables', '-t', 'filter', '-C', self.chain_name,
                '-s', ip, '-j', 'DROP'
            ], capture_output=True, text=True)
            
            return result.returncode == 0
            
        except subprocess.CalledProcessError:
            return False
        except Exception as e:
            self.logger.error(f"Error checking IP block status: {e}")
            return False
            
    def block_ip(self, ip: str, reason: str = "DDoS detected", 
                 duration_hours: Optional[int] = None) -> bool:
        """Block an IP address using iptables"""
        
        # Skip if IP is whitelisted
        if ip in self.config.get('whitelist_ips', []):
            self.logger.info(f"IP {ip} is whitelisted, skipping block")
            return False
            
        # Skip if already blocked
        if ip in self.blocked_ips:
            self.logger.info(f"IP {ip} is already blocked")
            return True
            
        try:
            # Add DROP rule for the IP
            result = subprocess.run([
                'iptables', '-t', 'filter', '-A', self.chain_name,
                '-s', ip, '-j', 'DROP'
            ], capture_output=True, text=True, check=True)
            
            # Calculate auto-unblock time if duration specified
            auto_unblock_time = None
            if duration_hours:
                auto_unblock_time = datetime.now() + timedelta(hours=duration_hours)
                
            # Record the block
            blocked_ip = BlockedIP(
                ip=ip,
                timestamp=datetime.now(),
                reason=reason,
                auto_unblock_time=auto_unblock_time
            )
            
            self.blocked_ips[ip] = blocked_ip
            
            # Log to file
            self._log_blocked_ip(blocked_ip)
            
            self.logger.warning(f"Blocked IP {ip}: {reason}")
            
            # Log iptables rule for reference
            self._log_iptables_rule("ADD", ip, reason)
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to block IP {ip}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error blocking IP {ip}: {e}")
            return False
            
    def unblock_ip(self, ip: str, reason: str = "Manual unblock") -> bool:
        """Unblock an IP address"""
        
        if ip not in self.blocked_ips:
            self.logger.info(f"IP {ip} is not currently blocked")
            return True
            
        try:
            # Remove DROP rule for the IP
            result = subprocess.run([
                'iptables', '-t', 'filter', '-D', self.chain_name,
                '-s', ip, '-j', 'DROP'
            ], capture_output=True, text=True, check=True)
            
            # Remove from tracking
            del self.blocked_ips[ip]
            
            self.logger.info(f"Unblocked IP {ip}: {reason}")
            
            # Log iptables rule for reference
            self._log_iptables_rule("REMOVE", ip, reason)
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to unblock IP {ip}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error unblocking IP {ip}: {e}")
            return False
            
    def block_multiple_ips(self, ips: List[str], reason: str = "Bulk DDoS block") -> Dict[str, bool]:
        """Block multiple IPs at once"""
        results = {}
        
        for ip in ips:
            results[ip] = self.block_ip(ip, reason)
            
        blocked_count = sum(1 for success in results.values() if success)
        self.logger.info(f"Blocked {blocked_count}/{len(ips)} IPs")
        
        return results
        
    def get_blocked_ips(self) -> Dict[str, BlockedIP]:
        """Get all currently blocked IPs"""
        return self.blocked_ips.copy()
        
    def cleanup_expired_blocks(self) -> int:
        """Remove expired auto-unblock rules"""
        current_time = datetime.now()
        expired_ips = []
        
        for ip, blocked_ip in self.blocked_ips.items():
            if (blocked_ip.auto_unblock_time and 
                current_time >= blocked_ip.auto_unblock_time):
                expired_ips.append(ip)
                
        # Unblock expired IPs
        for ip in expired_ips:
            self.unblock_ip(ip, "Auto-unblock expired")
            
        if expired_ips:
            self.logger.info(f"Auto-unblocked {len(expired_ips)} expired IPs")
            
        return len(expired_ips)
        
    def _log_blocked_ip(self, blocked_ip: BlockedIP):
        """Log blocked IP to file"""
        blocked_file = self.config.get('blocked_ip_log', 'data/blocked_ips.txt')
        
        try:
            with open(blocked_file, 'a') as f:
                timestamp_str = blocked_ip.timestamp.isoformat()
                auto_unblock_str = ""
                if blocked_ip.auto_unblock_time:
                    auto_unblock_str = f", auto_unblock: {blocked_ip.auto_unblock_time.isoformat()}"
                    
                f.write(f"{blocked_ip.ip} # Blocked at {timestamp_str} - {blocked_ip.reason}{auto_unblock_str}\n")
                
        except Exception as e:
            self.logger.error(f"Error logging blocked IP: {e}")
            
    def _log_iptables_rule(self, action: str, ip: str, reason: str):
        """Log iptables rule changes"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'ip': ip,
                'reason': reason,
                'chain': self.chain_name
            }
            
            # You could extend this to log to a separate iptables log file
            self.logger.debug(f"Iptables {action}: {ip} - {reason}")
            
        except Exception as e:
            self.logger.error(f"Error logging iptables rule: {e}")
            
    def get_firewall_stats(self) -> Dict:
        """Get firewall statistics"""
        current_time = datetime.now()
        
        # Count blocks by time periods
        last_hour = current_time - timedelta(hours=1)
        last_day = current_time - timedelta(days=1)
        
        recent_blocks_hour = sum(1 for blocked_ip in self.blocked_ips.values() 
                                if blocked_ip.timestamp >= last_hour)
        recent_blocks_day = sum(1 for blocked_ip in self.blocked_ips.values() 
                               if blocked_ip.timestamp >= last_day)
        
        # Count auto-unblock scheduled
        auto_unblock_count = sum(1 for blocked_ip in self.blocked_ips.values() 
                                if blocked_ip.auto_unblock_time)
        
        stats = {
            'total_blocked_ips': len(self.blocked_ips),
            'blocks_last_hour': recent_blocks_hour,
            'blocks_last_day': recent_blocks_day,
            'auto_unblock_scheduled': auto_unblock_count,
            'chain_name': self.chain_name
        }
        
        return stats
        
    def export_blocked_ips(self, format: str = 'json') -> str:
        """Export blocked IPs in specified format"""
        if format.lower() == 'json':
            export_data = []
            for ip, blocked_ip in self.blocked_ips.items():
                export_data.append({
                    'ip': blocked_ip.ip,
                    'timestamp': blocked_ip.timestamp.isoformat(),
                    'reason': blocked_ip.reason,
                    'auto_unblock_time': blocked_ip.auto_unblock_time.isoformat() 
                                       if blocked_ip.auto_unblock_time else None
                })
            return json.dumps(export_data, indent=2)
            
        elif format.lower() == 'csv':
            lines = ['IP,Timestamp,Reason,Auto_Unblock_Time']
            for ip, blocked_ip in self.blocked_ips.items():
                auto_unblock_str = blocked_ip.auto_unblock_time.isoformat() if blocked_ip.auto_unblock_time else ''
                lines.append(f"{blocked_ip.ip},{blocked_ip.timestamp.isoformat()},{blocked_ip.reason},{auto_unblock_str}")
            return '\n'.join(lines)
            
        else:
            raise ValueError(f"Unsupported export format: {format}")
            
    def flush_all_blocks(self) -> bool:
        """Remove all blocks (emergency use)"""
        try:
            # Flush the entire chain
            result = subprocess.run([
                'iptables', '-t', 'filter', '-F', self.chain_name
            ], capture_output=True, text=True, check=True)
            
            # Clear tracking
            blocked_count = len(self.blocked_ips)
            self.blocked_ips.clear()
            
            self.logger.warning(f"Flushed all {blocked_count} IP blocks from firewall")
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to flush blocks: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error flushing blocks: {e}")
            return False
            
    def test_iptables_connectivity(self) -> bool:
        """Test if iptables is available and working"""
        try:
            result = subprocess.run([
                'iptables', '--version'
            ], capture_output=True, text=True, check=True)
            
            self.logger.info(f"Iptables available: {result.stdout.strip()}")
            return True
            
        except subprocess.CalledProcessError:
            self.logger.error("Iptables not available or not accessible")
            return False
        except Exception as e:
            self.logger.error(f"Error testing iptables: {e}")
            return False