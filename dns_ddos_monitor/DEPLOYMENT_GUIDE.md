# 🚀 Hướng dẫn Triển khai DNS DDoS Monitor - 3 Máy

## 📋 Tổng quan Hệ thống

| Máy | IP | Vai trò | OS | Cài đặt |
|-----|----|---------|----|---------|
| **Kali** | 192.168.85.100 | Attacker | Kali Linux | Attack tools |
| **DNS Server** | 192.168.85.130 | DNS + Monitor | Ubuntu | BIND9, Monitor, Blocker |
| **Web Server** | 192.168.85.135 | Web + Dashboard | Ubuntu | Apache, Flask Dashboard |

---

## 🎯 TRIỂN KHAI TỪNG BƯỚC

### 📦 Bước 0: Chuẩn bị Files

**Trên máy phát triển (hoặc USB):**
```bash
# Tạo archive để copy sang các máy
tar -czf dns_ddos_monitor.tar.gz dns_ddos_monitor/
```

**Copy sang từng máy:**
```bash
# Copy sang DNS Server
scp dns_ddos_monitor.tar.gz user@192.168.85.130:~/

# Copy sang Web Server  
scp dns_ddos_monitor.tar.gz user@192.168.85.135:~/

# Copy sang Kali
scp dns_ddos_monitor.tar.gz user@192.168.85.100:~/
```

---

## 🖥️ MÁY 1: KALI LINUX (192.168.85.100) - ATTACKER

### Bước 1: Giải nén và setup
```bash
cd ~
tar -xzf dns_ddos_monitor.tar.gz
cd dns_ddos_monitor

# Chạy script setup
./scripts/setup_kali.sh
```

### Bước 2: Test connectivity
```bash
cd ~/dns_attacks

# Test DNS connectivity
./test_dns.sh

# Kết quả mong đợi:
# - dig @192.168.85.130 test.local trả về 192.168.85.130
# - dig @192.168.85.130 www.test.local trả về 192.168.85.135
# - curl http://192.168.85.135 trả về HTTP/1.1 200 OK
```

### Bước 3: Sẵn sàng tấn công
```bash
# Chạy attack scenarios
./attack_scenarios.sh

# Hoặc manual attack
python3 dns_flooder.py 192.168.85.130 --threads 10 --rate 100 --duration 60
```

---

## 🌐 MÁY 2: UBUNTU (192.168.85.130) - DNS SERVER

### Bước 1: Giải nén và cài đặt hệ thống
```bash
cd ~
tar -xzf dns_ddos_monitor.tar.gz
cd dns_ddos_monitor

# Chạy script cài đặt (cần sudo)
sudo ./scripts/install.sh
```

### Bước 2: Cấu hình cho multi-machine
```bash
# Copy cấu hình multi-machine
sudo cp config/named.conf.options.multi /etc/bind/named.conf.options
sudo cp config/db.test.local.multi /etc/bind/zones/db.test.local

# Tạo thư mục zones nếu chưa có
sudo mkdir -p /etc/bind/zones
sudo chown bind:bind /etc/bind/zones

# Kiểm tra cấu hình
sudo named-checkconf
sudo named-checkzone test.local /etc/bind/zones/db.test.local
```

### Bước 3: Cấu hình firewall
```bash
# Cho phép DNS từ mạng local
sudo ufw allow from 192.168.85.0/24 to any port 53
sudo ufw allow ssh
sudo ufw --force enable
```

### Bước 4: Khởi động DNS Server
```bash
# Restart BIND9
sudo systemctl restart bind9
sudo systemctl enable bind9

# Kiểm tra status
sudo systemctl status bind9

# Test DNS từ chính máy này
dig @localhost test.local
dig @localhost www.test.local
```

### Bước 5: Cấu hình Monitor
```bash
# Tạo config cho multi-machine
cat > config/monitor_config.json << 'EOF'
{
    "log_files": [
        "/var/log/dns_monitor/query.log",
        "/var/log/dns_monitor/security.log",
        "/var/log/syslog"
    ],
    "thresholds": {
        "queries_per_second": 30,
        "queries_per_minute": 200,
        "nxdomain_ratio": 0.6
    },
    "network": {
        "allowed_subnets": ["192.168.85.0/24"],
        "attacker_detection": true
    }
}
EOF

# Tạo config cho auto blocker
cat > config/blocker_config.json << 'EOF'
{
    "alert_file": "logs/alerts.json",
    "whitelist": ["127.0.0.1", "192.168.85.135", "192.168.85.0/24"],
    "thresholds": {
        "max_violations": 3,
        "time_window": 180,
        "block_duration": 1800
    }
}
EOF
```

### Bước 6: Khởi động Monitor (3 terminals)
```bash
# Terminal 1: DNS Monitor
cd dns_ddos_monitor
source venv/bin/activate
python3 src/dns_monitor.py

# Terminal 2: Auto Blocker (cần sudo)
sudo python3 src/auto_blocker.py --interval 30

# Terminal 3: Log monitoring
tail -f logs/alerts.json
```

---

## 🌍 MÁY 3: UBUNTU (192.168.85.135) - WEB SERVER

### Bước 1: Setup Web Server
```bash
cd ~
tar -xzf dns_ddos_monitor.tar.gz

# Chạy script setup (cần sudo)
sudo dns_ddos_monitor/scripts/setup_web_server.sh
```

### Bước 2: Copy Dashboard files từ DNS Server
```bash
# Copy dashboard files
scp -r user@192.168.85.130:~/dns_ddos_monitor/dashboard/* ~/dashboard/
scp user@192.168.85.130:~/dns_ddos_monitor/requirements.txt ~/
```

### Bước 3: Khởi động Dashboard
```bash
cd ~/dashboard

# Cài đặt dependencies
pip3 install -r ../requirements.txt

# Khởi động dashboard
python3 app.py
```

### Bước 4: Test Web Server
```bash
# Test Apache
curl http://192.168.85.135

# Test Dashboard
curl http://192.168.85.135:5000

# Test từ máy khác
# Từ Kali: curl http://192.168.85.135
```

---

## 🧪 KỊCH BẢN TEST HOÀN CHỈNH

### Phase 1: Kiểm tra Connectivity

**Từ Kali (192.168.85.100):**
```bash
# Test DNS resolution
dig @192.168.85.130 test.local
dig @192.168.85.130 www.test.local
dig @192.168.85.130 mail.test.local

# Test web connectivity
curl http://192.168.85.135
curl http://192.168.85.135:5000
```

**Từ DNS Server (192.168.85.130):**
```bash
# Test local DNS
dig @localhost test.local

# Test web server
curl http://192.168.85.135
```

### Phase 2: Baseline Monitoring

**DNS Server - Quan sát trạng thái bình thường:**
- Monitor console hiển thị 0 alerts
- Dashboard hiển thị traffic thấp
- iptables không có blocking rules

### Phase 3: Attack Simulation

**Từ Kali - Tấn công theo phases:**

```bash
# Phase 3.1: Light attack (30s)
python3 dns_flooder.py 192.168.85.130 --threads 5 --rate 50 --duration 30

# Quan sát: Monitor bắt đầu hiển thị alerts màu vàng

# Phase 3.2: Medium attack (60s)  
python3 dns_flooder.py 192.168.85.130 --threads 10 --rate 100 --duration 60

# Quan sát: Alerts màu đỏ, IP blocker bắt đầu chặn

# Phase 3.3: NXDOMAIN attack (60s)
python3 dns_flooder.py 192.168.85.130 --type nxdomain --threads 8 --rate 80 --duration 60

# Quan sát: NXDOMAIN alerts, dashboard charts cập nhật

# Phase 3.4: Heavy mixed attack (120s)
python3 dns_flooder.py 192.168.85.130 --type both --threads 15 --rate 150 --duration 120

# Quan sát: IP 192.168.85.100 bị block hoàn toàn
```

### Phase 4: Verification

**Kiểm tra kết quả trên DNS Server:**
```bash
# Xem IP bị chặn
sudo iptables -L INPUT -n | grep 192.168.85.100

# Xem alerts
cat logs/alerts.json | jq . | tail -20

# Xem block actions
cat logs/block_actions.json | jq . | tail -10

# Xem fail2ban status
sudo fail2ban-client status dns-ddos
```

**Kiểm tra Dashboard:**
- Truy cập http://192.168.85.135:5000
- Xem charts timeline attacks
- Xem top attackers (192.168.85.100 top 1)
- Xem attack types distribution

---

## 📊 KẾT QUẢ MONG ĐỢI

### ✅ Sau khi test thành công:

1. **DNS Server Console**: 
   - Alerts màu đỏ/vàng xuất hiện
   - Top clients hiển thị 192.168.85.100
   - Attack types được phân loại

2. **Auto Blocker**:
   - IP 192.168.85.100 bị block
   - Block actions được log
   - Automatic unblock sau thời gian

3. **Dashboard Web**:
   - Timeline chart hiển thị spike attacks
   - Attack types pie chart
   - Top attackers bar chart
   - Real-time statistics

4. **Log Files**:
   - `logs/alerts.json`: Chứa structured alerts
   - `logs/block_actions.json`: Block/unblock history
   - `/var/log/dns_monitor/query.log`: Raw DNS queries
   - `/var/log/fail2ban.log`: Fail2ban actions

5. **Network Impact**:
   - DNS queries từ Kali bị drop
   - Web access từ Kali bị block
   - Legitimate traffic không bị ảnh hưởng

---

## 🚨 TROUBLESHOOTING

### Lỗi DNS Server không start:
```bash
# Check config
sudo named-checkconf

# Check logs
sudo journalctl -u bind9 -f

# Restart service
sudo systemctl restart bind9
```

### Lỗi DNS không resolve từ Kali:
```bash
# Check firewall trên DNS server
sudo ufw status
sudo ufw allow from 192.168.85.0/24 to any port 53

# Test từ DNS server
dig @localhost test.local
```

### Lỗi Dashboard không hiển thị data:
```bash
# Check log sync
cd ~/dashboard
./sync_logs.sh &

# Manual copy logs
scp user@192.168.85.130:~/dns_ddos_monitor/logs/* ./logs/
```

### Lỗi Auto Blocker không chặn:
```bash
# Check iptables
sudo iptables -L INPUT -n

# Check permissions
sudo python3 src/auto_blocker.py --list-blocked

# Manual block test
sudo python3 src/auto_blocker.py --block-ip 192.168.85.100
```

---

## 🎓 DEMO CHO BÁO CÁO

### Chuẩn bị Demo:

1. **3 máy đều sẵn sàng**
2. **DNS Server**: 2-3 terminals (monitor, blocker, logs)
3. **Web Server**: Browser mở dashboard
4. **Kali**: Terminal sẵn sàng attack

### Kịch bản Demo 15 phút:

1. **Phút 0-2**: Giới thiệu topology và mục tiêu
2. **Phút 2-4**: Hiển thị hệ thống bình thường
3. **Phút 4-8**: Bắt đầu attacks, quan sát alerts
4. **Phút 8-12**: Hiển thị blocking và dashboard
5. **Phút 12-15**: Tổng kết kết quả và Q&A

### Script Demo tự động:
```bash
#!/bin/bash
# Chạy trên Kali để demo tự động

echo "=== DEMO DNS DDoS Detection ==="
echo "Phase 1: Light attack..."
python3 dns_flooder.py 192.168.85.130 --threads 5 --rate 50 --duration 20

echo "Phase 2: Medium attack..."  
python3 dns_flooder.py 192.168.85.130 --threads 10 --rate 100 --duration 30

echo "Phase 3: NXDOMAIN attack..."
python3 dns_flooder.py 192.168.85.130 --type nxdomain --duration 30

echo "Demo completed. Check dashboard!"
```

Hệ thống này hoàn toàn sẵn sàng cho việc demo và báo cáo đề tài của bạn! 🎯