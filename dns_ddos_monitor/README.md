# Công cụ Giám sát và Phát hiện Tấn công DDoS vào Hệ thống DNS

## Mô tả dự án
Xây dựng công cụ giám sát và phát hiện tấn công DDoS vào hệ thống DNS bằng mã nguồn mở và Python.

## Mục tiêu
- Mô phỏng các kiểu tấn công DDoS vào DNS (Flood, NXDOMAIN, Reflection)
- Thu thập và phân tích log DNS để phát hiện dấu hiệu tấn công
- Xây dựng công cụ giám sát và cảnh báo bất thường
- Triển khai các biện pháp phòng thủ tự động

## Cấu trúc dự án
```
dns_ddos_monitor/
├── config/                 # Cấu hình DNS server và các công cụ
├── scripts/                # Scripts cài đặt và cấu hình
├── src/                    # Mã nguồn Python
├── attack_tools/           # Công cụ mô phỏng tấn công
├── logs/                   # Lưu trữ log và dữ liệu phân tích
├── dashboard/              # Web dashboard (Flask)
├── docs/                   # Tài liệu và báo cáo
└── tests/                  # Test cases
```

## Lộ trình thực hiện (3 tuần)

### Tuần 1: Cài đặt môi trường và mô phỏng tấn công
- Ngày 1-2: Cài đặt BIND9, cấu hình zone files
- Ngày 3: Cài đặt công cụ tấn công (dnsperf, hping3, dnsflooder)
- Ngày 4: Mô phỏng các cuộc tấn công DNS
- Ngày 5-6: Cài đặt dnstop, phân tích truy vấn
- Ngày 7: Tối ưu hóa log format

### Tuần 2: Phân tích log và phát hiện bất thường
- Ngày 8: Viết script Python đọc log BIND9
- Ngày 9: Phân tích log với pandas và regex
- Ngày 10: Xác định tiêu chí phát hiện tấn công
- Ngày 11: Thiết lập ngưỡng cảnh báo
- Ngày 12: Ghi log cảnh báo
- Ngày 13-14: Tạo Flask dashboard (tùy chọn)

### Tuần 3: Phòng thủ và hoàn thiện
- Ngày 15: Script iptables tự động block IP
- Ngày 16: Cấu hình fail2ban
- Ngày 17: Tích hợp Python với syslog và fail2ban
- Ngày 18: Test toàn bộ hệ thống
- Ngày 19: Ghi lại kết quả và demo
- Ngày 20: Slide thuyết trình
- Ngày 21: Báo cáo kỹ thuật

## Yêu cầu hệ thống
- Ubuntu 20.04+ hoặc CentOS 7+
- Python 3.8+
- BIND9 DNS Server
- Root privileges để cấu hình firewall

## Cài đặt nhanh
```bash
cd dns_ddos_monitor
chmod +x scripts/install.sh
sudo ./scripts/install.sh
```

## Sử dụng
```bash
# Khởi động DNS server
sudo systemctl start named

# Chạy công cụ giám sát
python3 src/dns_monitor.py

# Mô phỏng tấn công (terminal khác)
python3 attack_tools/dns_flooder.py
```

## Tác giả
[Tên sinh viên] - [Trường đại học]

## Giấy phép
MIT License