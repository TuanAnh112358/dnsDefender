#!/bin/bash

# Script cài đặt tự động cho DNS DDoS Monitor
# Sử dụng: sudo ./install.sh

set -e

echo "=== DNS DDoS Monitor - Script Cài đặt ==="
echo "Bắt đầu cài đặt môi trường..."

# Kiểm tra quyền root
if [[ $EUID -ne 0 ]]; then
   echo "Script này cần chạy với quyền root (sudo)" 
   exit 1
fi

# Cập nhật hệ thống
echo "Cập nhật package lists..."
apt update

# Cài đặt BIND9 DNS Server
echo "Cài đặt BIND9 DNS Server..."
apt install -y bind9 bind9utils bind9-doc

# Cài đặt Python và các thư viện cần thiết
echo "Cài đặt Python và dependencies..."
apt install -y python3 python3-pip python3-venv
pip3 install pandas numpy matplotlib flask scapy dnspython psutil

# Cài đặt các công cụ mạng và giám sát
echo "Cài đặt network tools..."
apt install -y hping3 dnsutils tcpdump wireshark-common dnstop fail2ban iptables-persistent

# Cài đặt dnsperf (từ source)
echo "Cài đặt dnsperf..."
apt install -y build-essential libldns-dev libck-dev libnghttp2-dev libssl-dev
cd /tmp
git clone https://github.com/DNS-OARC/dnsperf.git
cd dnsperf
./configure
make
make install
cd /

# Tạo thư mục log
echo "Tạo thư mục logs..."
mkdir -p /var/log/dns_monitor
chown bind:bind /var/log/dns_monitor

# Backup cấu hình BIND9 gốc
echo "Backup cấu hình BIND9..."
cp /etc/bind/named.conf.local /etc/bind/named.conf.local.backup
cp /etc/bind/named.conf.options /etc/bind/named.conf.options.backup

# Copy cấu hình BIND9 mới
echo "Cấu hình BIND9..."
cp config/named.conf.local /etc/bind/
cp config/named.conf.options /etc/bind/
cp config/db.test.local /etc/bind/zones/

# Tạo thư mục zones nếu chưa có
mkdir -p /etc/bind/zones

# Cấu hình quyền
chown -R bind:bind /etc/bind/zones
chmod 755 /etc/bind/zones

# Cấu hình fail2ban
echo "Cấu hình fail2ban..."
cp config/dns-ddos.conf /etc/fail2ban/filter.d/
cp config/jail.local /etc/fail2ban/

# Khởi động các dịch vụ
echo "Khởi động dịch vụ..."
systemctl enable bind9
systemctl start bind9
systemctl enable fail2ban
systemctl start fail2ban

# Kiểm tra trạng thái
echo "Kiểm tra trạng thái dịch vụ..."
systemctl status bind9 --no-pager
systemctl status fail2ban --no-pager

# Tạo virtual environment cho Python
echo "Tạo Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "=== Cài đặt hoàn tất! ==="
echo "Để bắt đầu sử dụng:"
echo "1. source venv/bin/activate"
echo "2. python3 src/dns_monitor.py"
echo ""
echo "Để test DNS server:"
echo "dig @localhost test.local"