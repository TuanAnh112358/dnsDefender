#!/usr/bin/env python3
"""
DNS Log Reader Module
Parses BIND9 query logs and extracts relevant information for DDoS detection
"""

import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter

class DNSLogReader:
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.logger = logging.getLogger(__name__)
        
        # BIND9 query log pattern
        # Example: 06-Jan-2024 10:30:15.123 client 192.168.1.100#54321 (example.com): query: example.com IN A + (192.168.1.1)
        self.query_pattern = re.compile(
            r'(\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3})\s+'
            r'client\s+([0-9.]+)#(\d+)\s+'
            r'\(([^)]+)\):\s+'
            r'query:\s+(\S+)\s+IN\s+(\w+)\s+'
            r'([+-])\s+'
            r'\(([^)]+)\)'
        )
        
        # Statistics tracking
        self.stats = {
            'total_queries': 0,
            'queries_by_ip': defaultdict(int),
            'queries_by_domain': defaultdict(int),
            'queries_by_type': defaultdict(int),
            'nxdomain_count': 0,
            'suspicious_queries': []
        }
        
    def parse_log_line(self, line: str) -> Optional[Dict]:
        """Parse a single log line and extract DNS query information"""
        match = self.query_pattern.match(line.strip())
        if not match:
            return None
            
        timestamp_str, client_ip, client_port, queried_domain, query_domain, query_type, flags, server_ip = match.groups()
        
        try:
            timestamp = datetime.strptime(timestamp_str, '%d-%b-%Y %H:%M:%S.%f')
        except ValueError:
            self.logger.warning(f"Failed to parse timestamp: {timestamp_str}")
            return None
            
        return {
            'timestamp': timestamp,
            'client_ip': client_ip,
            'client_port': int(client_port),
            'queried_domain': queried_domain,
            'query_domain': query_domain,
            'query_type': query_type,
            'flags': flags,
            'server_ip': server_ip,
            'is_recursive': '+' in flags,
            'raw_line': line.strip()
        }
        
    def read_recent_logs(self, minutes: int = 5) -> List[Dict]:
        """Read logs from the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_queries = []
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    query = self.parse_log_line(line)
                    if query and query['timestamp'] >= cutoff_time:
                        recent_queries.append(query)
                        
        except FileNotFoundError:
            self.logger.error(f"Log file not found: {self.log_file}")
        except Exception as e:
            self.logger.error(f"Error reading log file: {e}")
            
        return recent_queries
        
    def analyze_queries(self, queries: List[Dict]) -> Dict:
        """Analyze queries for patterns and anomalies"""
        analysis = {
            'total_queries': len(queries),
            'unique_ips': set(),
            'unique_domains': set(),
            'query_types': Counter(),
            'queries_per_ip': Counter(),
            'queries_per_domain': Counter(),
            'nxdomain_queries': [],
            'amplification_queries': [],
            'suspicious_domains': [],
            'time_distribution': defaultdict(int)
        }
        
        for query in queries:
            # Basic statistics
            analysis['unique_ips'].add(query['client_ip'])
            analysis['unique_domains'].add(query['query_domain'])
            analysis['query_types'][query['query_type']] += 1
            analysis['queries_per_ip'][query['client_ip']] += 1
            analysis['queries_per_domain'][query['query_domain']] += 1
            
            # Time distribution (per minute)
            minute_key = query['timestamp'].strftime('%Y-%m-%d %H:%M')
            analysis['time_distribution'][minute_key] += 1
            
            # Detect potential NXDOMAIN attacks (domains that look suspicious)
            if self._is_suspicious_domain(query['query_domain']):
                analysis['suspicious_domains'].append(query)
                
            # Detect amplification attacks
            if query['query_type'] in ['ANY', 'TXT', 'DNSKEY', 'SOA']:
                analysis['amplification_queries'].append(query)
                
        # Convert sets to counts
        analysis['unique_ips'] = len(analysis['unique_ips'])
        analysis['unique_domains'] = len(analysis['unique_domains'])
        
        return analysis
        
    def _is_suspicious_domain(self, domain: str) -> bool:
        """Check if a domain looks suspicious (potential DGA)"""
        # Simple heuristics for DGA detection
        if len(domain) < 3:
            return False
            
        # Check for random-looking domains
        vowels = 'aeiou'
        consonants = 'bcdfghjklmnpqrstvwxyz'
        
        # Calculate vowel/consonant ratio
        vowel_count = sum(1 for char in domain.lower() if char in vowels)
        consonant_count = sum(1 for char in domain.lower() if char in consonants)
        
        if consonant_count == 0:
            return False
            
        ratio = vowel_count / consonant_count
        
        # Suspicious if very low vowel ratio or very high
        if ratio < 0.1 or ratio > 2.0:
            return True
            
        # Check for consecutive consonants (common in DGA)
        consecutive_consonants = 0
        max_consecutive = 0
        
        for char in domain.lower():
            if char in consonants:
                consecutive_consonants += 1
                max_consecutive = max(max_consecutive, consecutive_consonants)
            else:
                consecutive_consonants = 0
                
        return max_consecutive > 4
        
    def get_top_talkers(self, queries: List[Dict], top_n: int = 10) -> List[Tuple[str, int]]:
        """Get top N IPs by query count"""
        ip_counts = Counter(query['client_ip'] for query in queries)
        return ip_counts.most_common(top_n)
        
    def get_query_rate_per_ip(self, queries: List[Dict]) -> Dict[str, float]:
        """Calculate queries per minute for each IP"""
        if not queries:
            return {}
            
        # Group queries by IP and minute
        ip_minute_counts = defaultdict(lambda: defaultdict(int))
        
        for query in queries:
            ip = query['client_ip']
            minute = query['timestamp'].strftime('%Y-%m-%d %H:%M')
            ip_minute_counts[ip][minute] += 1
            
        # Calculate average rate
        ip_rates = {}
        for ip, minute_counts in ip_minute_counts.items():
            if minute_counts:
                avg_rate = sum(minute_counts.values()) / len(minute_counts)
                ip_rates[ip] = avg_rate
                
        return ip_rates
        
    def detect_dns_tunneling(self, queries: List[Dict]) -> List[Dict]:
        """Detect potential DNS tunneling based on query patterns"""
        tunneling_indicators = []
        
        # Group by IP
        ip_queries = defaultdict(list)
        for query in queries:
            ip_queries[query['client_ip']].append(query)
            
        for ip, ip_query_list in ip_queries.items():
            # Check for high frequency of TXT queries
            txt_queries = [q for q in ip_query_list if q['query_type'] == 'TXT']
            if len(txt_queries) > 20:  # Threshold for suspicious TXT queries
                tunneling_indicators.append({
                    'ip': ip,
                    'type': 'high_txt_queries',
                    'count': len(txt_queries),
                    'queries': txt_queries[:5]  # Sample queries
                })
                
            # Check for long domain names (potential data exfiltration)
            long_domains = [q for q in ip_query_list if len(q['query_domain']) > 50]
            if len(long_domains) > 5:
                tunneling_indicators.append({
                    'ip': ip,
                    'type': 'long_domain_names',
                    'count': len(long_domains),
                    'queries': long_domains[:3]
                })
                
        return tunneling_indicators