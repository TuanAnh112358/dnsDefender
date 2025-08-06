# Hướng dẫn Khởi động Nhanh - DNS DDoS Monitor

## 🚀 Cài đặt và Khởi động

### Bước 1: Cài đặt Hệ thống
```bash
# Clone hoặc copy dự án
cd dns_ddos_monitor

# Cài đặt tự động (cần quyền root)
sudo ./scripts/install.sh
```

### Bước 2: Kiểm tra DNS Server
```bash
# Kiểm tra BIND9 đã chạy
sudo systemctl status bind9

# Test DNS server
dig @localhost test.local
```

### Bước 3: Khởi động Monitor
```bash
# Kích hoạt virtual environment
source venv/bin/activate

# Chạy DNS monitor
python3 src/dns_monitor.py
```

## 🎯 Mô phỏng Tấn công (Terminal mới)

### DNS Flood Attack
```bash
# Tấn công cơ bản
python3 attack_tools/dns_flooder.py 127.0.0.1 --type flood --duration 60

# Tấn công mạnh
python3 attack_tools/dns_flooder.py 127.0.0.1 --threads 20 --rate 200 --duration 120
```

### NXDOMAIN Attack
```bash
python3 attack_tools/dns_flooder.py 127.0.0.1 --type nxdomain --duration 60
```

### Mixed Attack
```bash
python3 attack_tools/dns_flooder.py 127.0.0.1 --type both --duration 180
```

## 📊 Dashboard Web

### Khởi động Dashboard
```bash
# Terminal mới
cd dashboard
python3 app.py
```

Truy cập: http://localhost:5000

## 🛡️ Tự động Chặn IP

### Khởi động Auto Blocker
```bash
# Terminal mới (cần quyền root)
sudo python3 src/auto_blocker.py
```

### Quản lý IP thủ công
```bash
# Chặn IP
sudo python3 src/auto_blocker.py --block-ip 192.168.1.100

# Bỏ chặn IP
sudo python3 src/auto_blocker.py --unblock-ip 192.168.1.100

# Xem danh sách IP bị chặn
sudo python3 src/auto_blocker.py --list-blocked
```

## 📝 Kiểm tra Log

### Log Files
```bash
# DNS Monitor logs
tail -f logs/dns_monitor.log

# DNS Server logs
tail -f /var/log/dns_monitor/query.log

# Alerts
tail -f logs/alerts.json

# Block actions
tail -f logs/block_actions.json
```

### Phân tích Log
```bash
# Phân tích file log cụ thể
python3 src/dns_monitor.py --mode analyze --log-file /var/log/dns_monitor/query.log
```

## 🔧 Cấu hình

### Điều chỉnh Ngưỡng Cảnh báo
Chỉnh sửa file: `config/monitor_config.json`

```json
{
    "thresholds": {
        "queries_per_minute": 300,
        "nxdomain_ratio": 0.7,
        "amplification_size": 512
    }
}
```

### Cấu hình Auto Blocker
Tạo file: `config/blocker_config.json`

```json
{
    "thresholds": {
        "max_violations": 5,
        "time_window": 300,
        "block_duration": 3600
    },
    "whitelist": ["127.0.0.1", "192.168.1.0/24"]
}
```

## 🧪 Kịch bản Test Hoàn chỉnh

### Script Test Tự động
```bash
#!/bin/bash
# test_scenario.sh

echo "=== Bắt đầu test DNS DDoS Monitor ==="

# 1. Khởi động monitor (background)
python3 src/dns_monitor.py &
MONITOR_PID=$!

# 2. Khởi động auto blocker (background)
sudo python3 src/auto_blocker.py &
BLOCKER_PID=$!

# 3. Chờ 5 giây
sleep 5

# 4. Bắt đầu tấn công
echo "Bắt đầu DNS Flood attack..."
python3 attack_tools/dns_flooder.py 127.0.0.1 --threads 10 --rate 100 --duration 60 &

# 5. Chờ 30 giây rồi bắt đầu NXDOMAIN attack
sleep 30
echo "Bắt đầu NXDOMAIN attack..."
python3 attack_tools/dns_flooder.py 127.0.0.1 --type nxdomain --duration 60 &

# 6. Chờ hoàn thành
sleep 90

# 7. Dừng các process
kill $MONITOR_PID
sudo kill $BLOCKER_PID

echo "=== Test hoàn thành ==="
echo "Kiểm tra logs:"
echo "- logs/alerts.json"
echo "- logs/block_actions.json"
echo "- logs/dns_monitor.log"
```

## 📈 Kết quả Mong đợi

### Sau khi chạy test:
1. **Monitor Console**: Hiển thị alerts màu đỏ/vàng
2. **Log alerts.json**: Chứa các cảnh báo JSON
3. **IPTables**: IP attacker bị chặn
4. **Dashboard**: Biểu đồ thống kê tấn công
5. **Fail2ban**: Log trong `/var/log/fail2ban.log`

### Kiểm tra Kết quả
```bash
# Xem alerts
cat logs/alerts.json | jq .

# Xem IP bị chặn
sudo iptables -L INPUT -n | grep DNS-DDoS-Block

# Xem thống kê fail2ban
sudo fail2ban-client status dns-ddos
```

## 🚨 Troubleshooting

### Lỗi thường gặp:

1. **Permission denied**: Chạy với `sudo`
2. **Port 53 busy**: Dừng systemd-resolved: `sudo systemctl stop systemd-resolved`
3. **Module not found**: Cài đặt dependencies: `pip install -r requirements.txt`
4. **BIND9 không start**: Kiểm tra config: `sudo named-checkconf`

### Reset hệ thống:
```bash
# Dừng tất cả services
sudo systemctl stop bind9 fail2ban

# Xóa rules iptables
sudo iptables -F INPUT

# Xóa logs
rm -rf logs/*

# Khởi động lại
sudo systemctl start bind9 fail2ban
```

## 📚 Tài liệu Thêm

- `docs/ARCHITECTURE.md` - Kiến trúc hệ thống
- `docs/API.md` - API documentation
- `config/` - Các file cấu hình
- `logs/` - Log files và alerts

## 🎓 Demo cho Báo cáo

### Chuẩn bị Demo:
1. Mở 4 terminal tabs
2. Tab 1: DNS Monitor
3. Tab 2: Auto Blocker
4. Tab 3: Attack simulation
5. Tab 4: Log monitoring

### Kịch bản Demo:
1. Hiển thị hệ thống bình thường
2. Bắt đầu tấn công DNS Flood
3. Quan sát alerts và blocking
4. Chuyển sang NXDOMAIN attack
5. Hiển thị dashboard web
6. Giải thích các biểu đồ và thống kê