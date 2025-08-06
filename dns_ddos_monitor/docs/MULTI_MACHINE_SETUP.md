# Hướng dẫn Triển khai Trên 3 Máy

## 🖥️ Cấu hình Hệ thống

### Máy 1: Kali Linux (Attacker) - 192.168.85.100
- **Vai trò**: Máy tấn công, mô phỏng DDoS
- **Cài đặt**: Công cụ tấn công DNS

### Máy 2: Ubuntu (DNS Server) - 192.168.85.130  
- **Vai trò**: DNS Server + Monitor + Auto Blocker
- **Cài đặt**: BIND9, DNS Monitor, Fail2ban

### Máy 3: Ubuntu (Web Server) - 192.168.85.135
- **Vai trò**: Web server hợp lệ, Dashboard
- **Cài đặt**: Apache/Nginx, Flask Dashboard

---

## 🎯 TRIỂN KHAI CHI TIẾT

## Máy 1: Kali Linux (192.168.85.100) - ATTACKER

### Bước 1: Chuẩn bị môi trường
```bash
# Cập nhật hệ thống
sudo apt update && sudo apt upgrade -y

# Cài đặt Python và tools
sudo apt install -y python3 python3-pip git

# Tải project
git clone <your-repo> dns_ddos_monitor
cd dns_ddos_monitor

# Cài đặt Python dependencies cho attacker
pip3 install --user scapy dnspython requests
```

### Bước 2: Cấu hình Attack Tools
```bash
# Chỉ cần copy thư mục attack_tools
mkdir -p ~/dns_attacks
cp -r attack_tools/* ~/dns_attacks/
cd ~/dns_attacks
```

### Bước 3: Test kết nối DNS
```bash
# Test DNS server
dig @192.168.85.130 test.local

# Test với nslookup
nslookup test.local 192.168.85.130
```

### Bước 4: Các lệnh tấn công
```bash
# DNS Flood Attack
python3 dns_flooder.py 192.168.85.130 --type flood --threads 15 --rate 150 --duration 120

# NXDOMAIN Attack  
python3 dns_flooder.py 192.168.85.130 --type nxdomain --threads 10 --rate 100 --duration 90

# Mixed Attack
python3 dns_flooder.py 192.168.85.130 --type both --threads 20 --rate 200 --duration 180

# Amplification Attack (ANY queries)
python3 dns_flooder.py 192.168.85.130 --type flood --threads 5 --rate 50 --duration 60
```

---

## Máy 2: Ubuntu (192.168.85.130) - DNS SERVER + MONITOR

### Bước 1: Cài đặt hệ thống
```bash
# Copy toàn bộ project
scp -r dns_ddos_monitor user@192.168.85.130:~/
ssh user@192.168.85.130
cd dns_ddos_monitor

# Chạy script cài đặt
sudo ./scripts/install.sh
```

### Bước 2: Cấu hình BIND9 cho multi-machine
```bash
# Sửa file cấu hình BIND9
sudo nano /etc/bind/named.conf.options
```

Thêm cấu hình:
```bind
options {
    directory "/var/cache/bind";
    
    // Cho phép truy vấn từ mạng local
    allow-query { 192.168.85.0/24; localhost; };
    allow-recursion { 192.168.85.0/24; localhost; };
    
    // Listen trên tất cả interfaces
    listen-on { any; };
    listen-on-v6 { none; };
    
    // Forwarders
    forwarders {
        8.8.8.8;
        8.8.4.4;
    };
    
    // Rate limiting chống DDoS
    rate-limit {
        responses-per-second 20;
        window 5;
        slip 2;
        exempt-clients { 192.168.85.0/24; };
    };
    
    // Logging
    querylog yes;
};
```

### Bước 3: Cập nhật Zone Files
```bash
# Sửa zone file
sudo nano /etc/bind/zones/db.test.local
```

Cập nhật với IP thực:
```dns
$TTL    604800
@       IN      SOA     ns1.test.local. admin.test.local. (
                              2024010101 ; Serial
                         604800         ; Refresh
                          86400         ; Retry
                        2419200         ; Expire
                         604800 )       ; Negative Cache TTL

; Name servers
@       IN      NS      ns1.test.local.
@       IN      NS      ns2.test.local.

; A records pointing to real servers
@       IN      A       192.168.85.130
ns1     IN      A       192.168.85.130
ns2     IN      A       192.168.85.130
www     IN      A       192.168.85.135    ; Point to web server
mail    IN      A       192.168.85.135
ftp     IN      A       192.168.85.135
api     IN      A       192.168.85.135

; MX record
@       IN      MX      10 mail.test.local.
```

### Bước 4: Khởi động DNS Server
```bash
# Kiểm tra cấu hình
sudo named-checkconf
sudo named-checkzone test.local /etc/bind/zones/db.test.local

# Khởi động BIND9
sudo systemctl restart bind9
sudo systemctl enable bind9

# Kiểm tra status
sudo systemctl status bind9
```

### Bước 5: Cấu hình Monitoring
```bash
# Tạo thư mục logs
sudo mkdir -p /var/log/dns_monitor
sudo chown $USER:$USER /var/log/dns_monitor

# Cập nhật config cho multi-machine
nano config/monitor_config.json
```

Cập nhật config:
```json
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
```

### Bước 6: Khởi động Monitor
```bash
# Kích hoạt virtual environment
source venv/bin/activate

# Chạy DNS Monitor
python3 src/dns_monitor.py
```

### Bước 7: Khởi động Auto Blocker (Terminal mới)
```bash
# Cấu hình auto blocker
nano config/blocker_config.json
```

```json
{
    "alert_file": "logs/alerts.json",
    "whitelist": ["127.0.0.1", "192.168.85.135", "192.168.85.0/24"],
    "thresholds": {
        "max_violations": 3,
        "time_window": 180,
        "block_duration": 1800
    },
    "iptables": {
        "chain": "INPUT",
        "target": "DROP",
        "comment": "DNS-DDoS-Block"
    }
}
```

```bash
# Chạy auto blocker
sudo python3 src/auto_blocker.py --interval 30
```

---

## Máy 3: Ubuntu (192.168.85.135) - WEB SERVER + DASHBOARD

### Bước 1: Cài đặt Web Server
```bash
# Cài đặt Apache
sudo apt update
sudo apt install -y apache2 python3 python3-pip

# Tạo simple website
sudo nano /var/www/html/index.html
```

```html
<!DOCTYPE html>
<html>
<head>
    <title>Legitimate Web Server</title>
</head>
<body>
    <h1>Welcome to Legitimate Web Server</h1>
    <p>Server IP: 192.168.85.135</p>
    <p>This is a legitimate web server for DNS DDoS testing</p>
    
    <h2>Services:</h2>
    <ul>
        <li><a href="/api">API Endpoint</a></li>
        <li><a href="/mail">Mail Service</a></li>
        <li><a href="/ftp">FTP Service</a></li>
    </ul>
</body>
</html>
```

### Bước 2: Cài đặt Dashboard
```bash
# Copy dashboard files
scp -r user@192.168.85.130:~/dns_ddos_monitor/dashboard ~/
scp -r user@192.168.85.130:~/dns_ddos_monitor/requirements.txt ~/

# Cài đặt dependencies
pip3 install -r requirements.txt

# Cấu hình để kết nối tới DNS server
nano dashboard/config.py
```

```python
# Dashboard config
DNS_SERVER_IP = "192.168.85.130"
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000

# Remote log access (nếu cần)
REMOTE_LOGS = {
    "alerts": "http://192.168.85.130:8080/api/alerts",
    "stats": "http://192.168.85.130:8080/api/stats"
}
```

### Bước 3: Khởi động Dashboard
```bash
cd dashboard
python3 app.py
```

Dashboard sẽ chạy tại: http://192.168.85.135:5000

---

## 🚀 KỊCH BẢN TEST HOÀN CHỈNH

### Bước 1: Chuẩn bị (Tất cả máy)

**Máy DNS Server (192.168.85.130):**
```bash
# Terminal 1: DNS Monitor
cd dns_ddos_monitor
source venv/bin/activate
python3 src/dns_monitor.py

# Terminal 2: Auto Blocker  
sudo python3 src/auto_blocker.py

# Terminal 3: Log monitoring
tail -f logs/alerts.json
```

**Máy Web Server (192.168.85.135):**
```bash
# Terminal 1: Web server (Apache đã chạy)
sudo systemctl status apache2

# Terminal 2: Dashboard
cd dashboard
python3 app.py
```

**Máy Attacker (192.168.85.100):**
```bash
cd ~/dns_attacks
# Sẵn sàng tấn công
```

### Bước 2: Test Connectivity
```bash
# Từ Kali (192.168.85.100)
dig @192.168.85.130 www.test.local
curl http://192.168.85.135

# Từ DNS Server (192.168.85.130)  
dig @localhost test.local
curl http://192.168.85.135:5000
```

### Bước 3: Kịch bản Tấn công

**Phase 1: DNS Flood (từ Kali)**
```bash
python3 dns_flooder.py 192.168.85.130 --type flood --threads 10 --rate 100 --duration 60
```

**Phase 2: NXDOMAIN Attack (từ Kali)**
```bash
python3 dns_flooder.py 192.168.85.130 --type nxdomain --threads 8 --rate 80 --duration 60
```

**Phase 3: Mixed Attack (từ Kali)**
```bash
python3 dns_flooder.py 192.168.85.130 --type both --threads 15 --rate 150 --duration 120
```

### Bước 4: Quan sát Kết quả

1. **DNS Server Console**: Alerts màu đỏ/vàng
2. **Dashboard**: http://192.168.85.135:5000 - Charts và statistics
3. **IP Blocking**: 
   ```bash
   # Trên DNS server
   sudo iptables -L INPUT -n | grep 192.168.85.100
   ```
4. **Logs**:
   ```bash
   # Trên DNS server
   cat logs/alerts.json | jq .
   cat logs/block_actions.json | jq .
   ```

---

## 🔧 TROUBLESHOOTING

### Lỗi thường gặp:

1. **DNS không resolve từ Kali**:
   ```bash
   # Trên DNS server, check firewall
   sudo ufw allow 53/udp
   sudo ufw allow from 192.168.85.0/24
   ```

2. **Dashboard không hiển thị data**:
   ```bash
   # Copy logs từ DNS server sang Web server
   scp user@192.168.85.130:~/dns_ddos_monitor/logs/* ~/dashboard/logs/
   ```

3. **Auto blocker không hoạt động**:
   ```bash
   # Check iptables rules
   sudo iptables -L INPUT -n --line-numbers
   ```

### Script tự động sync logs:
```bash
#!/bin/bash
# sync_logs.sh - Chạy trên Web server
while true; do
    scp -q user@192.168.85.130:~/dns_ddos_monitor/logs/alerts.json ~/dashboard/logs/
    sleep 10
done
```

---

## 📊 KẾT QUẢ DEMO

Sau khi chạy test, bạn sẽ có:

1. **Real-time monitoring** trên DNS server
2. **Web dashboard** với charts tại http://192.168.85.135:5000  
3. **Automatic IP blocking** của máy Kali
4. **Log files** chứa evidence của attacks
5. **Fail2ban logs** cho phòng thủ tự động

Cấu hình này rất thực tế và phù hợp để demo cho giảng viên!