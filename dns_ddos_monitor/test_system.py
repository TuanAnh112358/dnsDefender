#!/usr/bin/env python3
"""
Simple test script to verify DNS DDoS Monitor components
"""

import sys
import os
import json
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

def test_log_reader():
    """Test DNS log reader"""
    print("Testing DNS Log Reader...")
    try:
        from core.log_reader import DNSLogReader
        
        log_reader = DNSLogReader('data/query.log')
        queries = log_reader.read_recent_logs(60)  # Last 60 minutes
        
        print(f"✓ Found {len(queries)} queries in log")
        
        if queries:
            analysis = log_reader.analyze_queries(queries)
            print(f"✓ Analysis complete: {analysis['total_queries']} total queries")
            print(f"  - Unique IPs: {analysis['unique_ips']}")
            print(f"  - Unique domains: {analysis['unique_domains']}")
            print(f"  - Suspicious domains: {len(analysis['suspicious_domains'])}")
            
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_dga_classifier():
    """Test DGA classifier"""
    print("\nTesting DGA Classifier...")
    try:
        from core.dga_classifier import DGAClassifier
        
        classifier = DGAClassifier()
        
        # Test domains
        test_domains = [
            "google.com",  # Legitimate
            "facebook.com",  # Legitimate
            "xkjdlaksjd.com",  # DGA-like
            "qwerty123456.net",  # DGA-like
            "randomstring.org"  # DGA-like
        ]
        
        for domain in test_domains:
            result = classifier.classify_domain(domain)
            status = "DGA" if result.is_dga else "Legitimate"
            print(f"  {domain}: {status} (confidence: {result.confidence:.2f})")
            
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_threshold_detector():
    """Test threshold detector"""
    print("\nTesting Threshold Detector...")
    try:
        from core.threshold_detector import ThresholdDetector
        from core.log_reader import DNSLogReader
        
        # Load config
        with open('config/monitor_config.json', 'r') as f:
            config = json.load(f)
            
        detector = ThresholdDetector(config)
        log_reader = DNSLogReader('data/query.log')
        
        queries = log_reader.read_recent_logs(60)
        if queries:
            results = detector.run_all_detections(queries)
            print(f"✓ Processed {len(queries)} queries")
            print(f"✓ Found {len(results)} potential threats")
            
            for result in results:
                print(f"  - {result.threat_type} from {result.source_ip} (severity: {result.severity})")
        else:
            print("✓ No recent queries to analyze")
            
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_alert_sender():
    """Test alert sender"""
    print("\nTesting Alert Sender...")
    try:
        from core.alert_sender import AlertSender
        
        # Load config
        with open('config/monitor_config.json', 'r') as f:
            config = json.load(f)
            
        alert_sender = AlertSender(config)
        
        # Test sending a system alert (won't actually send email in test)
        success = alert_sender.send_system_alert(
            "Test alert from DNS DDoS Monitor",
            severity='INFO'
        )
        
        print(f"✓ Alert system initialized")
        print(f"✓ Test alert created (email sending depends on SMTP config)")
        
        # Get stats
        stats = alert_sender.get_alert_stats()
        print(f"✓ Alert stats: {stats.get('total_alerts', 0)} total alerts")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_config_loading():
    """Test configuration loading"""
    print("\nTesting Configuration Loading...")
    try:
        # Test monitor config
        with open('config/monitor_config.json', 'r') as f:
            monitor_config = json.load(f)
        print("✓ Monitor configuration loaded successfully")
        
        # Test attack config
        with open('config/attack_config.json', 'r') as f:
            attack_config = json.load(f)
        print("✓ Attack configuration loaded successfully")
        
        # Validate required fields
        required_monitor_fields = ['log_file', 'thresholds', 'alert_email']
        for field in required_monitor_fields:
            if field in monitor_config:
                print(f"  ✓ {field}: {monitor_config[field]}")
            else:
                print(f"  ✗ Missing required field: {field}")
                return False
                
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("=== DNS DDoS Monitor System Test ===\n")
    
    tests = [
        test_config_loading,
        test_log_reader,
        test_dga_classifier,
        test_threshold_detector,
        test_alert_sender
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Status: {'✓ ALL TESTS PASSED' if passed == total else '✗ SOME TESTS FAILED'}")
    
    if passed == total:
        print("\n🎉 System is ready for deployment!")
        print("\nNext steps:")
        print("1. Configure BIND9 with query logging")
        print("2. Set up email SMTP settings in config/monitor_config.json")
        print("3. Run: python3 main.py")
        print("4. Optional: Start web dashboard with python3 dashboard/app.py")
    else:
        print("\n⚠️  Please fix the failing tests before deployment")

if __name__ == "__main__":
    main()