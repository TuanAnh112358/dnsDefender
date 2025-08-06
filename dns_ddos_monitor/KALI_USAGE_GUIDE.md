# 🎯 Hướng dẫn Sử dụng Attack Tools trên Kali Linux

## 📋 Thông tin Hệ thống
- **Kali IP**: 192.168.85.100
- **DNS Target**: 192.168.85.130
- **Web Target**: 192.168.85.135
- **DNS Resolver**: Đã cấu hình trong `/etc/resolv.conf`

## 🔧 Cài đặt Tools

### Bước 1: Copy project và cài đặt
```bash
# Copy project files
cd ~
tar -xzf dns_ddos_monitor.tar.gz
cd dns_ddos_monitor/attack_tools

# Cài đặt tools
./install_tools.sh
```

### Bước 2: Kiểm tra tools đã cài đặt
```bash
# Kiểm tra dnsperf
dnsperf -h

# Kiểm tra hping3
hping3 -h

# Kiểm tra DNS resolution
dig @192.168.85.130 test.local
```

## 🚀 Các Công cụ Tấn công

### 1. Advanced DNS Attacks (Python)
```bash
# DNS Flood Attack
python3 advanced_dns_attacks.py --attack flood --duration 60 --qps 1000

# NXDOMAIN Attack
python3 advanced_dns_attacks.py --attack nxdomain --duration 60 --qps 500

# UDP Flood với hping3
python3 advanced_dns_attacks.py --attack udp-flood --duration 60 --pps 1000

# DNS Amplification
python3 advanced_dns_attacks.py --attack amplification --duration 60

# Subdomain Enumeration
python3 advanced_dns_attacks.py --attack enumeration --duration 60

# Mixed Attack Scenario
python3 advanced_dns_attacks.py --attack mixed --duration 180

# Stress Test (Tất cả đồng thời)
python3 advanced_dns_attacks.py --attack stress --duration 120
```

### 2. Quick Attack Menu
```bash
# Menu tương tác
./quick_attacks.sh

# Chọn từ menu:
# 1. DNS Flood Attack (dnsperf)
# 2. NXDOMAIN Flood (dnsperf)  
# 3. UDP Flood (hping3)
# 4. DNS Amplification
# 5. Subdomain Enumeration
# 6. Mixed Attack Scenario
# 7. Stress Test
# 8. Custom Attack
# 9. Test Connectivity
```

### 3. Demo Script cho Báo cáo
```bash
# Demo tự động cho báo cáo
./demo_attacks.sh

# Options:
# 1. Run Full Demo (Auto) - Chạy 5 phases tự động
# 2. Run Individual Phases - Chạy từng phase riêng
# 3. Quick Connectivity Test - Test kết nối
```

## 📊 Các Loại Tấn công Chi tiết

### 🚀 DNS Flood Attack
**Mục đích**: Làm quá tải DNS server bằng queries hợp lệ
```bash
# Light attack
python3 advanced_dns_attacks.py --attack flood --duration 30 --qps 300

# Medium attack  
python3 advanced_dns_attacks.py --attack flood --duration 60 --qps 800

# Heavy attack
python3 advanced_dns_attacks.py --attack flood --duration 120 --qps 1500
```

**Kết quả mong đợi**:
- Monitor hiển thị alerts màu vàng/đỏ
- Query count tăng cao
- Response time tăng

### 💥 NXDOMAIN Attack
**Mục đích**: Tấn công bằng queries domain không tồn tại
```bash
# Standard NXDOMAIN attack
python3 advanced_dns_attacks.py --attack nxdomain --duration 60 --qps 500

# Heavy NXDOMAIN
python3 advanced_dns_attacks.py --attack nxdomain --duration 90 --qps 800
```

**Kết quả mong đợi**:
- NXDOMAIN alerts xuất hiện
- Cache pollution
- DNS server phải xử lý nhiều negative responses

### 🌊 UDP Flood Attack
**Mục đích**: Tấn công layer 4 bằng UDP packets
```bash
# UDP flood với hping3
python3 advanced_dns_attacks.py --attack udp-flood --duration 60 --pps 1000

# Heavy UDP flood
python3 advanced_dns_attacks.py --attack udp-flood --duration 120 --pps 2000
```

**Kết quả mong đợi**:
- Network congestion
- UDP packet loss
- Server resource exhaustion

### 📈 DNS Amplification Attack
**Mục đích**: Lợi dụng ANY queries để amplification
```bash
python3 advanced_dns_attacks.py --attack amplification --duration 60
```

**Kết quả mong đợi**:
- Large response packets
- Bandwidth amplification
- ANY query alerts

### 🔍 Subdomain Enumeration Attack
**Mục đích**: Mô phỏng tấn công reconnaissance
```bash
python3 advanced_dns_attacks.py --attack enumeration --duration 60
```

**Kết quả mong đợi**:
- Nhiều queries cho subdomains khác nhau
- Pattern recognition alerts
- Enumeration detection

## 🎭 Kịch bản Demo cho Báo cáo

### Demo Script Tự động
```bash
./demo_attacks.sh
# Chọn option 1: Run Full Demo

# Demo sẽ chạy 5 phases:
# Phase 1: Baseline (30s) - Traffic bình thường
# Phase 2: Light Flood (45s) - Trigger first alerts  
# Phase 3: NXDOMAIN (60s) - NXDOMAIN detection
# Phase 4: Mixed Attack (90s) - Trigger IP blocking
# Phase 5: Verification - Kiểm tra blocking
```

### Manual Demo Steps
```bash
# Step 1: Test connectivity
dig @192.168.85.130 test.local

# Step 2: Light attack
python3 advanced_dns_attacks.py --attack flood --duration 45 --qps 300

# Step 3: NXDOMAIN attack  
python3 advanced_dns_attacks.py --attack nxdomain --duration 60 --qps 400

# Step 4: Heavy mixed attack
python3 advanced_dns_attacks.py --attack mixed --duration 120

# Step 5: Verify blocking
dig @192.168.85.130 test.local  # Should timeout
```

## 📈 Monitoring Kết quả

### Trên DNS Server (192.168.85.130)
```bash
# Xem alerts real-time
tail -f ~/dns_ddos_monitor/logs/alerts.json

# Xem IP blocking
sudo iptables -L INPUT -n | grep 192.168.85.100

# Xem fail2ban status
sudo fail2ban-client status dns-ddos
```

### Trên Web Dashboard (192.168.85.135:5000)
- **Timeline Chart**: Hiển thị spike attacks theo thời gian
- **Attack Types**: Pie chart phân loại attacks
- **Top Attackers**: Bar chart với 192.168.85.100 ở top
- **Real-time Stats**: Counters và metrics

### Verification Commands
```bash
# Kiểm tra DNS bị block
timeout 5 dig @192.168.85.130 test.local

# Kiểm tra web access bị block  
timeout 5 curl http://192.168.85.135

# Xem iptables rules
sudo iptables -L INPUT -n --line-numbers | grep DNS-DDoS-Block
```

## 🛠️ Troubleshooting

### Lỗi "dnsperf not found"
```bash
sudo apt update
sudo apt install -y dnsperf
```

### Lỗi "hping3 not found"
```bash
sudo apt install -y hping3
```

### DNS không resolve
```bash
# Kiểm tra /etc/resolv.conf
cat /etc/resolv.conf

# Test manual
dig @192.168.85.130 test.local

# Ping DNS server
ping 192.168.85.130
```

### Python module errors
```bash
pip3 install --user scapy dnspython requests colorama
```

## 🎓 Tips cho Demo Báo cáo

### Chuẩn bị Demo
1. **Test connectivity** trước khi demo
2. **Mở 3 terminals** trên DNS server (monitor, blocker, logs)
3. **Mở web dashboard** trên browser
4. **Chuẩn bị screenshot** tools và results

### Kịch bản Demo 15 phút
1. **0-2 phút**: Giới thiệu topology và tools
2. **2-4 phút**: Hiển thị hệ thống bình thường
3. **4-8 phút**: Chạy attacks, quan sát alerts
4. **8-12 phút**: Hiển thị blocking và dashboard
5. **12-15 phút**: Tổng kết và Q&A

### Commands cho Demo
```bash
# Quick demo sequence
./demo_attacks.sh  # Option 1: Full Demo

# Manual demo
python3 advanced_dns_attacks.py --attack flood --duration 30 --qps 500
python3 advanced_dns_attacks.py --attack nxdomain --duration 30 --qps 300
python3 advanced_dns_attacks.py --attack mixed --duration 60
```

## 📝 Log Files và Evidence

### Files quan trọng để show
- `~/dns_ddos_monitor/logs/alerts.json` - Structured alerts
- `~/dns_ddos_monitor/logs/block_actions.json` - IP blocking history
- `/var/log/dns_monitor/query.log` - Raw DNS queries
- `/var/log/fail2ban.log` - Fail2ban actions

### Commands để show evidence
```bash
# Show alerts với jq
cat ~/dns_ddos_monitor/logs/alerts.json | jq . | tail -20

# Show blocked IPs
sudo iptables -L INPUT -n | grep DNS-DDoS-Block

# Show attack statistics
python3 advanced_dns_attacks.py --attack flood --duration 10 --qps 100
```

Hệ thống này sẵn sàng cho việc demo và báo cáo đề tài! 🎯