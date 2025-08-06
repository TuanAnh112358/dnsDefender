#!/bin/bash

# Script cài đặt tools tấn công DNS cho Kali Linux
echo "🔧 Installing DNS Attack Tools on Kali Linux..."

# Cập nhật package list
echo "📦 Updating package lists..."
sudo apt update

# Cài đặt dnsperf
echo "🚀 Installing dnsperf..."
sudo apt install -y dnsperf

# Cài đặt hping3 (thường đã có sẵn trên Kali)
echo "🚀 Installing hping3..."
sudo apt install -y hping3

# Cài đặt các tools bổ sung
echo "🚀 Installing additional tools..."
sudo apt install -y \
    dnsutils \
    nmap \
    masscan \
    fierce \
    dnsrecon \
    dnsenum \
    sublist3r \
    amass

# Cài đặt Python packages
echo "🐍 Installing Python packages..."
pip3 install --user \
    scapy \
    dnspython \
    requests \
    colorama \
    asyncio \
    concurrent.futures

# Kiểm tra cài đặt
echo "✅ Checking installations..."

tools=("dnsperf" "hping3" "dig" "nslookup" "nmap")
for tool in "${tools[@]}"; do
    if command -v $tool &> /dev/null; then
        echo "✅ $tool: Installed"
    else
        echo "❌ $tool: Not found"
    fi
done

# Tạo thư mục cho query files
mkdir -p /tmp/dns_attacks

echo ""
echo "🎯 DNS Attack Tools Installation Complete!"
echo ""
echo "Available tools:"
echo "- dnsperf: DNS performance testing and flooding"
echo "- hping3: Network packet generator"
echo "- nmap: Network scanner with DNS capabilities"
echo "- dig/nslookup: DNS lookup utilities"
echo "- fierce/dnsrecon/dnsenum: DNS enumeration"
echo ""
echo "Usage examples:"
echo "1. python3 advanced_dns_attacks.py --attack flood --duration 60"
echo "2. python3 advanced_dns_attacks.py --attack mixed --duration 180"
echo "3. ./quick_attacks.sh"