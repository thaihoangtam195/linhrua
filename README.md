# 🤖 Facebook Messenger Chatbot - Hướng Dẫn Cài Đặt

## 📋 Mô tả
Hệ thống chatbot tự động trả lời tin nhắn Facebook Messenger, tích hợp:
- **Gemini AI** để trả lời thông minh
- **Dữ liệu từ Excel** (giá cả, sản phẩm, chính sách...)
- **Hiểu viết tắt tiếng Việt** (sp, đh, vc, bn, k, ko...)
- **Giao diện quản lý web** dễ sử dụng

---

## 🚀 CÁCH 1: Deploy lên Railway (MIỄN PHÍ - Khuyến nghị)

### Chi phí: **$0 - $5/tháng** (200 tin nhắn/ngày thừa sức dùng free tier)

### Bước 1: Chuẩn bị
1. Tạo tài khoản [Railway.app](https://railway.app) (đăng nhập bằng GitHub)
2. Tạo tài khoản [GitHub](https://github.com) nếu chưa có

### Bước 2: Upload code lên GitHub
```bash
# Tạo repository mới trên GitHub, sau đó:
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/fb-chatbot.git
git push -u origin main
```

### Bước 3: Deploy trên Railway
1. Vào [Railway.app](https://railway.app) → New Project
2. Chọn "Deploy from GitHub repo"
3. Chọn repository vừa tạo
4. Railway sẽ tự động detect Python và deploy
5. Vào Settings → Generate Domain để lấy URL

### Bước 4: Cấu hình
1. Truy cập URL Railway (VD: `https://fb-chatbot-xxx.up.railway.app`)
2. Nhập Gemini API Key và Facebook credentials
3. Done!

---

## 🚀 CÁCH 2: Deploy lên Render (MIỄN PHÍ)

### Chi phí: **$0/tháng** (Free tier có thể sleep sau 15 phút không hoạt động)

### Bước 1: Tạo file render.yaml
```yaml
services:
  - type: web
    name: fb-chatbot
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT
```

### Bước 2: Deploy
1. Vào [render.com](https://render.com) → New Web Service
2. Kết nối GitHub repository
3. Chọn Free tier
4. Deploy!

---

## 🚀 CÁCH 3: Deploy lên VPS (Khuyến nghị cho production)

### Chi phí: **~$5/tháng** (DigitalOcean, Vultr, Linode...)

### Bước 1: Thuê VPS
Các lựa chọn rẻ:
- [DigitalOcean](https://digitalocean.com) - $4/tháng
- [Vultr](https://vultr.com) - $5/tháng  
- [Contabo](https://contabo.com) - €4/tháng
- [Hetzner](https://hetzner.com) - €4/tháng

Chọn: Ubuntu 22.04, 1GB RAM, 1 CPU

### Bước 2: Cài đặt môi trường
```bash
# SSH vào VPS
ssh root@YOUR_IP

# Cập nhật hệ thống
apt update && apt upgrade -y

# Cài Python
apt install python3 python3-pip python3-venv git nginx -y

# Clone code
cd /var/www
git clone https://github.com/YOUR_USERNAME/fb-chatbot.git
cd fb-chatbot

# Tạo virtual environment
python3 -m venv venv
source venv/bin/activate

# Cài dependencies
pip install -r requirements.txt
```

### Bước 3: Cấu hình Gunicorn service
```bash
# Tạo file service
cat > /etc/systemd/system/chatbot.service << 'EOF'
[Unit]
Description=FB Chatbot
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/fb-chatbot
Environment="PATH=/var/www/fb-chatbot/venv/bin"
ExecStart=/var/www/fb-chatbot/venv/bin/gunicorn --workers 2 --bind unix:chatbot.sock app:app

[Install]
WantedBy=multi-user.target
EOF

# Khởi động service
systemctl start chatbot
systemctl enable chatbot
```

### Bước 4: Cấu hình Nginx
```bash
cat > /etc/nginx/sites-available/chatbot << 'EOF'
server {
    listen 80;
    server_name YOUR_DOMAIN.com;

    location / {
        proxy_pass http://unix:/var/www/fb-chatbot/chatbot.sock;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

ln -s /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### Bước 5: Cài SSL (miễn phí với Let's Encrypt)
```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d YOUR_DOMAIN.com
```

---

## 📱 CẤU HÌNH FACEBOOK

### Bước 1: Tạo Facebook App
1. Truy cập [developers.facebook.com](https://developers.facebook.com)
2. My Apps → Create App
3. Chọn "Business" → Next
4. Điền thông tin app → Create App

### Bước 2: Thêm Messenger
1. Vào Dashboard → Add Products
2. Tìm "Messenger" → Set Up
3. Trong "Access Tokens":
   - Chọn Page của bạn
   - Click "Generate Token"
   - Copy token này (dùng cho `fb_page_token`)

### Bước 3: Cấu hình Webhook
1. Trong Messenger Settings → Webhooks
2. Click "Add Callback URL"
3. Điền:
   - Callback URL: `https://YOUR_DOMAIN.com/webhook`
   - Verify Token: `my_secret_verify_token` (hoặc token bạn tự đặt)
4. Click "Verify and Save"
5. Trong "Webhook Fields", chọn: `messages`, `messaging_postbacks`
6. Click "Subscribe"

### Bước 4: Lấy App Secret
1. Vào Settings → Basic
2. Copy "App Secret" (dùng cho `fb_app_secret`)

### Bước 5: Lấy Gemini API Key
1. Truy cập [aistudio.google.com](https://aistudio.google.com)
2. Get API Key → Create API Key
3. Copy key

---

## 📊 CHUẨN BỊ DỮ LIỆU EXCEL

### Cấu trúc file Excel:
| câu hỏi | câu trả lời | hình ảnh | từ khóa | danh mục |
|---------|-------------|----------|---------|----------|
| Giá sp bao nhiêu? | Dạ 150k/cái ạ | https://... | giá, tiền, bn | Giá cả |
| Ship bn? | 30k toàn quốc | | ship, vc, giao | Vận chuyển |

### Lưu ý:
- Cột bắt buộc: `câu hỏi`, `câu trả lời`
- Cột tùy chọn: `hình ảnh`, `từ khóa`, `danh mục`
- Hình ảnh phải là URL public (có thể upload lên Imgur, Google Drive public)
- Từ khóa cách nhau bằng dấu phẩy
- Có thể upload nhiều file Excel (theo chủ đề khác nhau)

---

## 🔧 SỬ DỤNG

### Giao diện Admin
1. Truy cập `https://YOUR_DOMAIN.com`
2. Nhập API keys
3. Upload file Excel dữ liệu
4. Test chatbot ngay trên giao diện
5. Khi khách nhắn tin vào Page → Bot tự động trả lời!

### Cập nhật dữ liệu
1. Upload file Excel mới
2. Click "Reload dữ liệu"
3. Done!

### Cập nhật API Key
1. Vào Admin Panel
2. Sửa Gemini API Key
3. Click "Lưu cấu hình"

---

## ❓ FAQ

**Q: Làm sao để bot trả lời chính xác hơn?**
A: Thêm nhiều câu hỏi mẫu với từ khóa đa dạng trong file Excel

**Q: Bot có hiểu viết tắt không?**
A: Có! Bot đã được train với 50+ từ viết tắt phổ biến (sp, đh, bn, k, vc...)

**Q: Chi phí Gemini API?**
A: Free tier: 60 requests/phút, đủ dùng cho 200 tin nhắn/ngày

**Q: Làm sao khi Gemini API key hết hạn?**
A: Vào Admin Panel → Nhập key mới → Lưu

**Q: Có thể gửi hình ảnh không?**
A: Có! Điền URL hình vào cột `hình ảnh` trong Excel

---

## 📞 HỖ TRỢ

Nếu gặp vấn đề, kiểm tra:
1. Logs trên Railway/Render/VPS
2. Facebook Webhook status
3. Gemini API quota

---

## 📁 CẤU TRÚC PROJECT

```
fb-chatbot/
├── app.py              # Web server chính
├── chatbot_engine.py   # Logic xử lý AI
├── requirements.txt    # Dependencies
├── config.json         # Cấu hình (tự tạo khi chạy)
├── data/               # Thư mục chứa file Excel
│   ├── gia_ca.xlsx
│   ├── san_pham.xlsx
│   └── chinh_sach.xlsx
└── README.md           # File này
```

---

**Chúc bạn thành công! 🚀**
