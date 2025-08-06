#!/bin/bash

# Setup script cho máy Ubuntu Web Server + Dashboard
# IP: 192.168.85.135

echo "=== Web Server + Dashboard Setup - Ubuntu ==="

# Kiểm tra quyền root
if [[ $EUID -ne 0 ]]; then
   echo "Script này cần chạy với quyền root (sudo)" 
   exit 1
fi

# Cập nhật hệ thống
echo "Cập nhật hệ thống..."
apt update && apt upgrade -y

# Cài đặt Apache Web Server
echo "Cài đặt Apache Web Server..."
apt install -y apache2

# Cài đặt Python và dependencies
echo "Cài đặt Python và dependencies..."
apt install -y python3 python3-pip python3-venv

# Khởi động và enable Apache
systemctl start apache2
systemctl enable apache2

# Cấu hình firewall
echo "Cấu hình firewall..."
ufw allow 'Apache Full'
ufw allow 5000/tcp  # Flask dashboard
ufw allow ssh
ufw --force enable

# Tạo website content
echo "Tạo nội dung website..."
cat > /var/www/html/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Legitimate Web Server - DNS DDoS Test Lab</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .service-box {
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }
        .status {
            color: #28a745;
            font-weight: bold;
        }
        .info-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .info-table th, .info-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .info-table th {
            background-color: #667eea;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 Legitimate Web Server</h1>
            <p>DNS DDoS Testing Laboratory</p>
        </div>
        
        <div class="service-box">
            <h2>📊 Server Information</h2>
            <table class="info-table">
                <tr>
                    <th>Property</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Server IP</td>
                    <td><strong>192.168.85.135</strong></td>
                </tr>
                <tr>
                    <td>Role</td>
                    <td>Legitimate Web Server</td>
                </tr>
                <tr>
                    <td>Status</td>
                    <td><span class="status">✅ Online</span></td>
                </tr>
                <tr>
                    <td>DNS Server</td>
                    <td>192.168.85.130</td>
                </tr>
                <tr>
                    <td>Dashboard</td>
                    <td><a href="http://192.168.85.135:5000">DNS Monitor Dashboard</a></td>
                </tr>
            </table>
        </div>

        <div class="service-box">
            <h2>🔧 Available Services</h2>
            <ul>
                <li><strong>Web Server</strong> - Apache HTTP Server</li>
                <li><strong>DNS Monitor Dashboard</strong> - Real-time monitoring interface</li>
                <li><strong>API Endpoints</strong> - RESTful services</li>
                <li><strong>Mail Service</strong> - Email handling</li>
                <li><strong>FTP Service</strong> - File transfer</li>
            </ul>
        </div>

        <div class="service-box">
            <h2>🎯 DNS Test Domains</h2>
            <p>These domains resolve to this server:</p>
            <ul>
                <li>www.test.local → 192.168.85.135</li>
                <li>mail.test.local → 192.168.85.135</li>
                <li>ftp.test.local → 192.168.85.135</li>
                <li>api.test.local → 192.168.85.135</li>
                <li>blog.test.local → 192.168.85.135</li>
                <li>shop.test.local → 192.168.85.135</li>
            </ul>
        </div>

        <div class="service-box">
            <h2>📈 Monitoring Links</h2>
            <ul>
                <li><a href="http://192.168.85.135:5000" target="_blank">DNS DDoS Monitor Dashboard</a></li>
                <li><a href="/server-info" target="_blank">Server Information</a></li>
                <li><a href="/api/status" target="_blank">API Status</a></li>
            </ul>
        </div>

        <div class="service-box">
            <h2>⚠️ Lab Purpose</h2>
            <p>This server is part of a DNS DDoS monitoring and detection laboratory. It serves as:</p>
            <ul>
                <li>Legitimate web server target</li>
                <li>Dashboard hosting platform</li>
                <li>DNS resolution endpoint</li>
                <li>Attack impact demonstration</li>
            </ul>
        </div>
    </div>

    <script>
        // Auto-refresh page every 30 seconds
        setTimeout(function() {
            location.reload();
        }, 30000);
        
        // Update timestamp
        document.addEventListener('DOMContentLoaded', function() {
            const now = new Date();
            const timeString = now.toLocaleString();
            document.body.insertAdjacentHTML('beforeend', 
                '<div style="text-align: center; margin-top: 20px; color: #666;">' +
                'Last updated: ' + timeString + '</div>'
            );
        });
    </script>
</body>
</html>
EOF

# Tạo thêm các trang API
mkdir -p /var/www/html/api

cat > /var/www/html/api/status << 'EOF'
{
    "status": "online",
    "server": "192.168.85.135",
    "service": "legitimate-web-server",
    "timestamp": "2024-01-01T12:00:00Z",
    "uptime": "24h",
    "dns_server": "192.168.85.130",
    "dashboard": "http://192.168.85.135:5000"
}
EOF

cat > /var/www/html/server-info << 'EOF'
<!DOCTYPE html>
<html>
<head><title>Server Information</title></head>
<body>
<h1>Server Information</h1>
<pre>
Server: Apache/2.4.x (Ubuntu)
IP: 192.168.85.135
Role: Legitimate Web Server
DNS: 192.168.85.130
Status: Active
</pre>
</body>
</html>
EOF

# Cài đặt Python packages cho dashboard
echo "Cài đặt Python packages cho dashboard..."
pip3 install flask plotly pandas numpy requests colorama tabulate watchdog

# Tạo thư mục cho dashboard
mkdir -p /home/$(logname)/dashboard
chown -R $(logname):$(logname) /home/$(logname)/dashboard

# Tạo dashboard config
cat > /home/$(logname)/dashboard/config.py << 'EOF'
# Dashboard Configuration
DNS_SERVER_IP = "192.168.85.130"
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000

# Log sync settings
LOG_SYNC_ENABLED = True
LOG_SYNC_INTERVAL = 10  # seconds

# Remote log paths (from DNS server)
REMOTE_LOGS = {
    "dns_server": "192.168.85.130",
    "log_path": "/home/user/dns_ddos_monitor/logs/",
    "alerts_file": "alerts.json",
    "stats_file": "stats.json"
}
EOF

# Tạo script sync logs từ DNS server
cat > /home/$(logname)/dashboard/sync_logs.sh << 'EOF'
#!/bin/bash

# Script to sync logs from DNS server
DNS_SERVER="192.168.85.130"
DNS_USER="user"  # Change this to actual username
LOCAL_LOG_DIR="./logs"

mkdir -p $LOCAL_LOG_DIR

while true; do
    # Sync alerts
    scp -q $DNS_USER@$DNS_SERVER:~/dns_ddos_monitor/logs/alerts.json $LOCAL_LOG_DIR/ 2>/dev/null
    
    # Sync stats  
    scp -q $DNS_USER@$DNS_SERVER:~/dns_ddos_monitor/logs/stats.json $LOCAL_LOG_DIR/ 2>/dev/null
    
    # Sync block actions
    scp -q $DNS_USER@$DNS_SERVER:~/dns_ddos_monitor/logs/block_actions.json $LOCAL_LOG_DIR/ 2>/dev/null
    
    sleep 10
done
EOF

chmod +x /home/$(logname)/dashboard/sync_logs.sh
chown $(logname):$(logname) /home/$(logname)/dashboard/sync_logs.sh

# Tạo systemd service cho dashboard
cat > /etc/systemd/system/dns-dashboard.service << 'EOF'
[Unit]
Description=DNS DDoS Monitor Dashboard
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/user/dashboard
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Restart Apache
systemctl restart apache2

echo ""
echo "=== Web Server Setup Completed! ==="
echo ""
echo "Services configured:"
echo "✅ Apache Web Server - http://192.168.85.135"
echo "✅ Dashboard ready - http://192.168.85.135:5000"
echo "✅ API endpoints available"
echo "✅ Firewall configured"
echo ""
echo "Next steps:"
echo "1. Copy dashboard files from DNS server:"
echo "   scp -r user@192.168.85.130:~/dns_ddos_monitor/dashboard/* ~/dashboard/"
echo ""
echo "2. Start dashboard:"
echo "   cd ~/dashboard && python3 app.py"
echo ""
echo "3. Start log sync (optional):"
echo "   ./sync_logs.sh &"
echo ""
echo "4. Test web server:"
echo "   curl http://192.168.85.135"
echo ""
echo "Web server is ready for DNS DDoS testing!"