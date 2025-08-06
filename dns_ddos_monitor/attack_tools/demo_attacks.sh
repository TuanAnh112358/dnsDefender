#!/bin/bash

# Demo Script cho Báo cáo Đề tài DNS DDoS Monitor
# Chạy các cuộc tấn công tuần tự để demo

DNS_TARGET="192.168.85.130"

echo "🎓 DNS DDoS Monitor - Demo Script"
echo "=================================="
echo "Target DNS Server: $DNS_TARGET"
echo "Mục đích: Demo cho báo cáo đề tài"
echo ""

# Hàm hiển thị progress
show_progress() {
    local duration=$1
    local message=$2
    
    for ((i=1; i<=duration; i++)); do
        echo -ne "\r$message... ${i}/${duration}s"
        sleep 1
    done
    echo ""
}

# Hàm test connectivity trước khi demo
test_connectivity() {
    echo "📡 Testing connectivity to DNS server..."
    
    if dig @$DNS_TARGET test.local +short > /dev/null 2>&1; then
        echo "✅ DNS server is reachable"
    else
        echo "❌ Cannot reach DNS server. Please check:"
        echo "   - DNS server is running on $DNS_TARGET"
        echo "   - Firewall allows DNS traffic"
        echo "   - Network connectivity"
        exit 1
    fi
}

# Demo Phase 1: Baseline Testing
demo_phase1() {
    echo ""
    echo "📊 PHASE 1: Baseline Testing (30s)"
    echo "Mục đích: Hiển thị hoạt động DNS bình thường"
    echo "----------------------------------------"
    
    echo "Sending normal DNS queries..."
    for i in {1..30}; do
        dig @$DNS_TARGET test.local +short > /dev/null 2>&1
        dig @$DNS_TARGET www.test.local +short > /dev/null 2>&1
        sleep 1
        echo -ne "\rBaseline queries: $i/30"
    done
    echo ""
    echo "✅ Phase 1 completed - Check monitor for normal traffic"
    echo ""
    read -p "Press Enter to continue to Phase 2..."
}

# Demo Phase 2: Light DNS Flood
demo_phase2() {
    echo ""
    echo "🚀 PHASE 2: Light DNS Flood Attack (45s)"
    echo "Mục đích: Trigger first alerts"
    echo "----------------------------------------"
    
    python3 advanced_dns_attacks.py --attack flood --duration 45 --qps 300 &
    ATTACK_PID=$!
    
    show_progress 45 "DNS Flood Attack running"
    
    wait $ATTACK_PID
    echo "✅ Phase 2 completed - Check monitor for yellow alerts"
    echo ""
    read -p "Press Enter to continue to Phase 3..."
}

# Demo Phase 3: NXDOMAIN Attack
demo_phase3() {
    echo ""
    echo "💥 PHASE 3: NXDOMAIN Flood Attack (60s)"
    echo "Mục đích: Demonstrate NXDOMAIN detection"
    echo "----------------------------------------"
    
    python3 advanced_dns_attacks.py --attack nxdomain --duration 60 --qps 400 &
    ATTACK_PID=$!
    
    show_progress 60 "NXDOMAIN Attack running"
    
    wait $ATTACK_PID
    echo "✅ Phase 3 completed - Check monitor for NXDOMAIN alerts"
    echo ""
    read -p "Press Enter to continue to Phase 4..."
}

# Demo Phase 4: Heavy Mixed Attack
demo_phase4() {
    echo ""
    echo "🎭 PHASE 4: Heavy Mixed Attack (90s)"
    echo "Mục đích: Trigger IP blocking"
    echo "----------------------------------------"
    
    echo "Starting multiple attack vectors..."
    
    # DNS Flood
    python3 advanced_dns_attacks.py --attack flood --duration 90 --qps 800 &
    FLOOD_PID=$!
    
    sleep 10
    
    # NXDOMAIN Attack
    python3 advanced_dns_attacks.py --attack nxdomain --duration 80 --qps 500 &
    NXDOMAIN_PID=$!
    
    sleep 10
    
    # UDP Flood
    python3 advanced_dns_attacks.py --attack udp-flood --duration 70 --pps 600 &
    UDP_PID=$!
    
    show_progress 90 "Mixed Attack running"
    
    # Đợi tất cả attacks kết thúc
    wait $FLOOD_PID 2>/dev/null
    wait $NXDOMAIN_PID 2>/dev/null
    wait $UDP_PID 2>/dev/null
    
    echo "✅ Phase 4 completed - Check for IP blocking"
    echo ""
    read -p "Press Enter to continue to Phase 5..."
}

# Demo Phase 5: Verification
demo_phase5() {
    echo ""
    echo "🔍 PHASE 5: Attack Verification"
    echo "Mục đích: Verify blocking is working"
    echo "----------------------------------------"
    
    echo "Testing if IP is blocked..."
    
    # Test DNS queries (should fail or timeout)
    echo "Attempting DNS queries (should be blocked)..."
    timeout 5 dig @$DNS_TARGET test.local +short
    
    if [ $? -eq 124 ]; then
        echo "✅ DNS queries are being blocked (timeout)"
    else
        echo "⚠️  DNS queries still working (may not be blocked yet)"
    fi
    
    echo ""
    echo "Testing web connectivity to 192.168.85.135..."
    timeout 5 curl -s http://192.168.85.135 > /dev/null
    
    if [ $? -eq 124 ]; then
        echo "✅ Web access is blocked"
    else
        echo "⚠️  Web access still working"
    fi
    
    echo ""
    echo "✅ Phase 5 completed - Verification done"
}

# Main demo function
run_demo() {
    echo "Starting automated demo in 5 seconds..."
    echo "Make sure DNS Monitor and Auto Blocker are running!"
    sleep 5
    
    test_connectivity
    demo_phase1
    demo_phase2
    demo_phase3
    demo_phase4
    demo_phase5
    
    echo ""
    echo "🎉 DEMO COMPLETED!"
    echo "=================="
    echo ""
    echo "📈 Results to show:"
    echo "1. DNS Server Console: Real-time alerts and statistics"
    echo "2. Web Dashboard: http://192.168.85.135:5000"
    echo "   - Timeline chart showing attack phases"
    echo "   - Attack types pie chart"
    echo "   - Top attackers (192.168.85.100 should be #1)"
    echo "3. IP Blocking verification:"
    echo "   sudo iptables -L INPUT -n | grep 192.168.85.100"
    echo "4. Log files:"
    echo "   - cat ~/dns_ddos_monitor/logs/alerts.json | jq ."
    echo "   - cat ~/dns_ddos_monitor/logs/block_actions.json | jq ."
    echo ""
    echo "🎓 Demo script completed successfully!"
}

# Menu
echo "Demo Options:"
echo "1. 🎬 Run Full Demo (Auto)"
echo "2. 🎯 Run Individual Phases"
echo "3. 📊 Quick Connectivity Test"
echo "4. ❌ Exit"
echo ""

read -p "Choose option (1-4): " option

case $option in
    1)
        echo ""
        echo "🎬 Starting Full Automated Demo..."
        run_demo
        ;;
    
    2)
        echo ""
        echo "🎯 Individual Phase Menu:"
        echo "1. Phase 1: Baseline Testing"
        echo "2. Phase 2: Light DNS Flood"
        echo "3. Phase 3: NXDOMAIN Attack"
        echo "4. Phase 4: Heavy Mixed Attack"
        echo "5. Phase 5: Verification"
        echo ""
        
        read -p "Choose phase (1-5): " phase
        
        case $phase in
            1) test_connectivity && demo_phase1 ;;
            2) test_connectivity && demo_phase2 ;;
            3) test_connectivity && demo_phase3 ;;
            4) test_connectivity && demo_phase4 ;;
            5) demo_phase5 ;;
            *) echo "Invalid phase selected" ;;
        esac
        ;;
    
    3)
        test_connectivity
        echo ""
        echo "📊 Quick connectivity test completed"
        ;;
    
    4)
        echo "👋 Goodbye!"
        exit 0
        ;;
    
    *)
        echo "❌ Invalid option"
        ;;
esac