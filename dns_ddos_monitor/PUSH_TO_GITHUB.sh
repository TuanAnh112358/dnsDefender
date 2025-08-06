#!/bin/bash

echo "🚀 SCRIPT ĐẨY CODE LÊN GITHUB"
echo "=================================="
echo ""

# Kiểm tra xem đã có remote origin chưa
if git remote get-url origin 2>/dev/null; then
    echo "✅ Remote origin đã tồn tại"
else
    echo "❌ Chưa có remote origin. Hãy chạy lệnh sau:"
    echo ""
    echo "HTTPS (dễ dàng hơn):"
    echo "git remote add origin https://github.com/YOUR_USERNAME/dns-ddos-monitor.git"
    echo ""
    echo "SSH (bảo mật hơn, cần setup SSH key):"
    echo "git remote add origin git@github.com:YOUR_USERNAME/dns-ddos-monitor.git"
    echo ""
    echo "Thay YOUR_USERNAME bằng username GitHub của bạn"
    exit 1
fi

echo "🔄 Đang push code lên GitHub..."

# Push code lên GitHub
git push -u origin main

if [ $? -eq 0 ]; then
    echo "✅ Push code thành công!"
else
    echo "❌ Lỗi khi push code. Kiểm tra:"
    echo "1. Đã tạo repository trên GitHub chưa?"
    echo "2. URL remote có đúng không?"
    echo "3. Có quyền truy cập repository không?"
    exit 1
fi

echo ""
echo "🏷️ Đang push tags..."

# Push tags lên GitHub
git push origin --tags

if [ $? -eq 0 ]; then
    echo "✅ Push tags thành công!"
else
    echo "⚠️ Lỗi khi push tags (không quan trọng lắm)"
fi

echo ""
echo "🎉 HOÀN THÀNH!"
echo "==============="
echo "✅ Code đã được đẩy lên GitHub thành công!"
echo "✅ Repository: https://github.com/YOUR_USERNAME/dns-ddos-monitor"
echo "✅ Version tag: v1.0.0"
echo ""
echo "🔗 Các bước tiếp theo:"
echo "1. Truy cập repository trên GitHub"
echo "2. Tạo Release từ tag v1.0.0"
echo "3. Thêm topics/tags cho repository"
echo "4. Cấu hình repository settings"
echo ""
echo "📖 Xem thêm hướng dẫn chi tiết trong GITHUB_UPLOAD_GUIDE.md"