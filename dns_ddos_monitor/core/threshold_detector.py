#!/usr/bin/env python3
"""
Threshold Detector Module
Detects IPs and patterns that exceed configured thresholds for DDoS detection
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass

@dataclass
class DetectionResult:
    """Result of a detection check"""
    detected: bool
    threat_type: str
    severity: str
    source_ip: str
    details: Dict
    timestamp: datetime
    recommended_action: str

class ThresholdDetector:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Tracking data
        self.ip_query_history = defaultdict(list)
        self.domain_query_history = defaultdict(list)
        self.blocked_ips = set()
        self.detection_history = []
        
        # Load blocked IPs from file if exists
        self._load_blocked_ips()
        
    def _load_blocked_ips(self):
        """Load previously blocked IPs from file"""
        try:
            with open(self.config.get('blocked_ip_log', 'data/blocked_ips.txt'), 'r') as f:
                for line in f:
                    ip = line.strip()
                    if ip:
                        self.blocked_ips.add(ip)
            self.logger.info(f"Loaded {len(self.blocked_ips)} blocked IPs")
        except FileNotFoundError:
            self.logger.info("No existing blocked IPs file found")
        except Exception as e:
            self.logger.error(f"Error loading blocked IPs: {e}")
            
    def detect_dns_flood(self, queries: List[Dict]) -> List[DetectionResult]:
        """Detect DNS query flood attacks"""
        results = []
        
        if not self.config.get('detection_rules', {}).get('dns_flood', {}).get('enabled', True):
            return results
            
        threshold = self.config['detection_rules']['dns_flood']['threshold']
        window_minutes = self.config['detection_rules']['dns_flood']['window_minutes']
        
        # Group queries by IP
        ip_queries = defaultdict(list)
        for query in queries:
            ip_queries[query['client_ip']].append(query)
            
        # Check each IP against threshold
        for ip, ip_query_list in ip_queries.items():
            if ip in self.config.get('whitelist_ips', []):
                continue
                
            # Count queries in the time window
            now = datetime.now()
            cutoff = now - timedelta(minutes=window_minutes)
            recent_queries = [q for q in ip_query_list if q['timestamp'] >= cutoff]
            
            if len(recent_queries) > threshold:
                results.append(DetectionResult(
                    detected=True,
                    threat_type='dns_flood',
                    severity='HIGH',
                    source_ip=ip,
                    details={
                        'query_count': len(recent_queries),
                        'threshold': threshold,
                        'time_window': window_minutes,
                        'queries_per_minute': len(recent_queries) / window_minutes,
                        'unique_domains': len(set(q['query_domain'] for q in recent_queries)),
                        'query_types': Counter(q['query_type'] for q in recent_queries)
                    },
                    timestamp=now,
                    recommended_action='block_ip'
                ))
                
        return results
        
    def detect_nxdomain_attack(self, queries: List[Dict]) -> List[DetectionResult]:
        """Detect NXDOMAIN flood attacks"""
        results = []
        
        if not self.config.get('detection_rules', {}).get('nxdomain_flood', {}).get('enabled', True):
            return results
            
        threshold = self.config['detection_rules']['nxdomain_flood']['threshold']
        ratio_threshold = self.config['detection_rules']['nxdomain_flood']['ratio']
        
        # Group by IP and analyze NXDOMAIN patterns
        ip_queries = defaultdict(list)
        for query in queries:
            ip_queries[query['client_ip']].append(query)
            
        for ip, ip_query_list in ip_queries.items():
            if ip in self.config.get('whitelist_ips', []):
                continue
                
            if len(ip_query_list) < threshold:
                continue
                
            # Count unique domains (potential NXDOMAIN candidates)
            unique_domains = set(q['query_domain'] for q in ip_query_list)
            suspicious_domains = []
            
            # Identify potentially non-existent domains
            for domain in unique_domains:
                domain_queries = [q for q in ip_query_list if q['query_domain'] == domain]
                if len(domain_queries) == 1:  # Only queried once (likely NXDOMAIN)
                    suspicious_domains.append(domain)
                    
            nxdomain_ratio = len(suspicious_domains) / len(unique_domains) if unique_domains else 0
            
            if nxdomain_ratio >= ratio_threshold and len(suspicious_domains) >= threshold:
                results.append(DetectionResult(
                    detected=True,
                    threat_type='nxdomain_flood',
                    severity='MEDIUM',
                    source_ip=ip,
                    details={
                        'total_queries': len(ip_query_list),
                        'unique_domains': len(unique_domains),
                        'suspicious_domains': len(suspicious_domains),
                        'nxdomain_ratio': nxdomain_ratio,
                        'threshold': threshold,
                        'sample_domains': list(suspicious_domains)[:10]
                    },
                    timestamp=datetime.now(),
                    recommended_action='block_ip'
                ))
                
        return results
        
    def detect_amplification_attack(self, queries: List[Dict]) -> List[DetectionResult]:
        """Detect DNS amplification attacks"""
        results = []
        
        if not self.config.get('detection_rules', {}).get('amplification_detection', {}).get('enabled', True):
            return results
            
        suspicious_types = self.config['detection_rules']['amplification_detection']['suspicious_types']
        threshold = self.config['detection_rules']['amplification_detection']['threshold']
        
        # Group by IP and check for amplification patterns
        ip_queries = defaultdict(list)
        for query in queries:
            ip_queries[query['client_ip']].append(query)
            
        for ip, ip_query_list in ip_queries.items():
            if ip in self.config.get('whitelist_ips', []):
                continue
                
            # Count suspicious query types
            suspicious_queries = [q for q in ip_query_list if q['query_type'] in suspicious_types]
            
            if len(suspicious_queries) >= threshold:
                query_type_dist = Counter(q['query_type'] for q in suspicious_queries)
                target_domains = Counter(q['query_domain'] for q in suspicious_queries)
                
                results.append(DetectionResult(
                    detected=True,
                    threat_type='amplification_attack',
                    severity='HIGH',
                    source_ip=ip,
                    details={
                        'suspicious_queries': len(suspicious_queries),
                        'total_queries': len(ip_query_list),
                        'suspicious_ratio': len(suspicious_queries) / len(ip_query_list),
                        'query_types': dict(query_type_dist),
                        'target_domains': dict(target_domains.most_common(5)),
                        'threshold': threshold
                    },
                    timestamp=datetime.now(),
                    recommended_action='block_ip'
                ))
                
        return results
        
    def detect_subdomain_enumeration(self, queries: List[Dict]) -> List[DetectionResult]:
        """Detect subdomain enumeration attacks"""
        results = []
        
        # Group by IP and analyze subdomain patterns
        ip_queries = defaultdict(list)
        for query in queries:
            ip_queries[query['client_ip']].append(query)
            
        for ip, ip_query_list in ip_queries.items():
            if ip in self.config.get('whitelist_ips', []):
                continue
                
            # Group by base domain
            domain_patterns = defaultdict(set)
            for query in ip_query_list:
                domain = query['query_domain']
                parts = domain.split('.')
                if len(parts) >= 2:
                    base_domain = '.'.join(parts[-2:])  # Get base domain
                    domain_patterns[base_domain].add(domain)
                    
            # Check for excessive subdomains
            for base_domain, subdomains in domain_patterns.items():
                if len(subdomains) > 50:  # Threshold for subdomain enumeration
                    results.append(DetectionResult(
                        detected=True,
                        threat_type='subdomain_enumeration',
                        severity='MEDIUM',
                        source_ip=ip,
                        details={
                            'base_domain': base_domain,
                            'subdomain_count': len(subdomains),
                            'sample_subdomains': list(subdomains)[:10],
                            'queries_count': len([q for q in ip_query_list if base_domain in q['query_domain']])
                        },
                        timestamp=datetime.now(),
                        recommended_action='monitor'
                    ))
                    
        return results
        
    def detect_rate_limit_violations(self, queries: List[Dict]) -> List[DetectionResult]:
        """Detect rate limit violations"""
        results = []
        
        if not self.config.get('rate_limit', {}).get('enabled', False):
            return results
            
        max_rps = self.config['rate_limit']['rps']
        window_seconds = self.config['rate_limit']['window']
        
        # Group queries by IP and time window
        ip_time_queries = defaultdict(lambda: defaultdict(int))
        
        for query in queries:
            ip = query['client_ip']
            time_bucket = int(query['timestamp'].timestamp()) // window_seconds
            ip_time_queries[ip][time_bucket] += 1
            
        # Check for rate limit violations
        for ip, time_buckets in ip_time_queries.items():
            if ip in self.config.get('whitelist_ips', []):
                continue
                
            for time_bucket, query_count in time_buckets.items():
                if query_count > (max_rps * window_seconds):
                    results.append(DetectionResult(
                        detected=True,
                        threat_type='rate_limit_violation',
                        severity='MEDIUM',
                        source_ip=ip,
                        details={
                            'queries_in_window': query_count,
                            'max_allowed': max_rps * window_seconds,
                            'window_seconds': window_seconds,
                            'queries_per_second': query_count / window_seconds
                        },
                        timestamp=datetime.now(),
                        recommended_action='rate_limit'
                    ))
                    
        return results
        
    def run_all_detections(self, queries: List[Dict]) -> List[DetectionResult]:
        """Run all detection algorithms"""
        all_results = []
        
        try:
            # Run each detection method
            all_results.extend(self.detect_dns_flood(queries))
            all_results.extend(self.detect_nxdomain_attack(queries))
            all_results.extend(self.detect_amplification_attack(queries))
            all_results.extend(self.detect_subdomain_enumeration(queries))
            all_results.extend(self.detect_rate_limit_violations(queries))
            
            # Store detection history
            self.detection_history.extend(all_results)
            
            # Log results
            for result in all_results:
                self.logger.warning(f"Threat detected: {result.threat_type} from {result.source_ip} - {result.severity}")
                
        except Exception as e:
            self.logger.error(f"Error during detection: {e}")
            
        return all_results
        
    def get_blocked_ips(self) -> Set[str]:
        """Get set of currently blocked IPs"""
        return self.blocked_ips.copy()
        
    def add_blocked_ip(self, ip: str, reason: str = ""):
        """Add IP to blocked list"""
        if ip not in self.blocked_ips:
            self.blocked_ips.add(ip)
            self._save_blocked_ip(ip, reason)
            
    def _save_blocked_ip(self, ip: str, reason: str):
        """Save blocked IP to file"""
        try:
            with open(self.config.get('blocked_ip_log', 'data/blocked_ips.txt'), 'a') as f:
                timestamp = datetime.now().isoformat()
                f.write(f"{ip} # Blocked at {timestamp} - {reason}\n")
        except Exception as e:
            self.logger.error(f"Error saving blocked IP: {e}")
            
    def get_detection_stats(self) -> Dict:
        """Get detection statistics"""
        if not self.detection_history:
            return {}
            
        stats = {
            'total_detections': len(self.detection_history),
            'detections_by_type': Counter(r.threat_type for r in self.detection_history),
            'detections_by_severity': Counter(r.severity for r in self.detection_history),
            'unique_source_ips': len(set(r.source_ip for r in self.detection_history)),
            'blocked_ips_count': len(self.blocked_ips),
            'recent_detections': len([r for r in self.detection_history 
                                    if (datetime.now() - r.timestamp).total_seconds() < 3600])
        }
        
        return stats