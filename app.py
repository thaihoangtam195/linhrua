"""
Facebook Messenger Chatbot - Web Server
Giao diện quản lý + Webhook nhận tin nhắn
"""

from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
import os
import json
import hmac
import hashlib
import requests
from chatbot_engine import ChatbotEngine
from werkzeug.utils import secure_filename
import threading
import time

app = Flask(__name__)
CORS(app)

# Cấu hình
UPLOAD_FOLDER = 'data'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Biến global
chatbot = None
config = {
    'gemini_api_key': '',
    'fb_page_token': '',
    'fb_verify_token': 'my_secret_verify_token',  # Tự đặt
    'fb_app_secret': '',
}

def load_config():
    """Load cấu hình từ file"""
    global config
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            config.update(json.load(f))

def save_config():
    """Lưu cấu hình"""
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)

def init_chatbot():
    """Khởi tạo chatbot"""
    global chatbot
    if config['gemini_api_key']:
        chatbot = ChatbotEngine(config['gemini_api_key'], UPLOAD_FOLDER)
        return True
    return False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_messenger_message(recipient_id: str, message_text: str, image_url: str = None):
    """Gửi tin nhắn qua Facebook Messenger API"""
    if not config['fb_page_token']:
        print("Chưa cấu hình Facebook Page Token")
        return False
    
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={config['fb_page_token']}"
    
    # Gửi text
    if message_text:
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text}
        }
        try:
            response = requests.post(url, json=payload)
            print(f"Sent message: {response.status_code}")
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    # Gửi hình ảnh nếu có
    if image_url:
        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "attachment": {
                    "type": "image",
                    "payload": {"url": image_url, "is_reusable": True}
                }
            }
        }
        try:
            response = requests.post(url, json=payload)
            print(f"Sent image: {response.status_code}")
        except Exception as e:
            print(f"Error sending image: {e}")
    
    return True

# ==================== GIAO DIỆN WEB ====================

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 Chatbot Admin Panel</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #5B8DEE;
            --secondary-color: #7C3AED;
        }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', sans-serif;
        }
        .main-container {
            padding: 20px;
        }
        .card {
            border: none;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .card-header {
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            border-radius: 15px 15px 0 0 !important;
            padding: 15px 20px;
        }
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            transition: transform 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-icon {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: var(--primary-color);
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            border: none;
        }
        .btn-primary:hover {
            background: linear-gradient(135deg, var(--secondary-color), var(--primary-color));
        }
        .chat-test {
            height: 400px;
            overflow-y: auto;
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
        }
        .message {
            margin-bottom: 10px;
            padding: 10px 15px;
            border-radius: 15px;
            max-width: 80%;
        }
        .message.user {
            background: var(--primary-color);
            color: white;
            margin-left: auto;
        }
        .message.bot {
            background: white;
            border: 1px solid #ddd;
        }
        .file-list {
            max-height: 200px;
            overflow-y: auto;
        }
        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px;
            border-bottom: 1px solid #eee;
        }
        .status-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
        }
        .status-active {
            background: #d4edda;
            color: #155724;
        }
        .status-inactive {
            background: #f8d7da;
            color: #721c24;
        }
        .navbar-brand {
            font-weight: bold;
            font-size: 1.5rem;
        }
        .form-control:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 0.2rem rgba(91, 141, 238, 0.25);
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark" style="background: rgba(0,0,0,0.2);">
        <div class="container-fluid">
            <span class="navbar-brand">🤖 FB Messenger Chatbot</span>
            <span class="status-badge {{ 'status-active' if status == 'active' else 'status-inactive' }}">
                {{ '🟢 Đang hoạt động' if status == 'active' else '🔴 Chưa cấu hình' }}
            </span>
        </div>
    </nav>

    <div class="container main-container">
        <!-- Stats -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-icon">📚</div>
                    <div class="stat-number" id="stat-qa">{{ stats.total_qa }}</div>
                    <div class="text-muted">Câu hỏi-Trả lời</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-icon">💬</div>
                    <div class="stat-number" id="stat-conv">{{ stats.total_conversations }}</div>
                    <div class="text-muted">Cuộc hội thoại</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-icon">📝</div>
                    <div class="stat-number" id="stat-abbr">{{ stats.total_abbreviations }}</div>
                    <div class="text-muted">Từ viết tắt</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-icon">📁</div>
                    <div class="stat-number" id="stat-files">{{ files|length }}</div>
                    <div class="text-muted">File dữ liệu</div>
                </div>
            </div>
        </div>

        <div class="row">
            <!-- Cấu hình -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-cog"></i> Cấu hình API
                    </div>
                    <div class="card-body">
                        <form id="configForm">
                            <div class="mb-3">
                                <label class="form-label">Gemini API Key</label>
                                <div class="input-group">
                                    <input type="password" class="form-control" id="geminiKey" 
                                           value="{{ config.gemini_api_key }}" placeholder="AIza...">
                                    <button class="btn btn-outline-secondary" type="button" 
                                            onclick="togglePassword('geminiKey')">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Facebook Page Access Token</label>
                                <div class="input-group">
                                    <input type="password" class="form-control" id="fbToken" 
                                           value="{{ config.fb_page_token }}" placeholder="EAAx...">
                                    <button class="btn btn-outline-secondary" type="button" 
                                            onclick="togglePassword('fbToken')">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Facebook App Secret</label>
                                <div class="input-group">
                                    <input type="password" class="form-control" id="fbSecret" 
                                           value="{{ config.fb_app_secret }}" placeholder="abc123...">
                                    <button class="btn btn-outline-secondary" type="button" 
                                            onclick="togglePassword('fbSecret')">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Webhook Verify Token</label>
                                <input type="text" class="form-control" id="verifyToken" 
                                       value="{{ config.fb_verify_token }}">
                                <small class="text-muted">Dùng khi cấu hình webhook trên Facebook</small>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">
                                <i class="fas fa-save"></i> Lưu cấu hình
                            </button>
                        </form>
                    </div>
                </div>

                <!-- Upload file -->
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-upload"></i> Upload dữ liệu Excel
                    </div>
                    <div class="card-body">
                        <form id="uploadForm" enctype="multipart/form-data">
                            <div class="mb-3">
                                <input type="file" class="form-control" id="excelFile" 
                                       accept=".xlsx,.xls" required>
                                <small class="text-muted">
                                    File Excel cần có cột: câu hỏi, câu trả lời, hình ảnh (tùy chọn)
                                </small>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">
                                <i class="fas fa-cloud-upload-alt"></i> Upload
                            </button>
                        </form>
                        
                        <hr>
                        <h6>File đã upload:</h6>
                        <div class="file-list">
                            {% for file in files %}
                            <div class="file-item">
                                <span><i class="fas fa-file-excel text-success"></i> {{ file }}</span>
                                <button class="btn btn-sm btn-outline-danger" 
                                        onclick="deleteFile('{{ file }}')">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                            {% endfor %}
                        </div>
                        <button class="btn btn-outline-primary w-100 mt-3" onclick="reloadData()">
                            <i class="fas fa-sync"></i> Reload dữ liệu
                        </button>
                    </div>
                </div>
            </div>

            <!-- Test chatbot -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-comment-dots"></i> Test Chatbot
                    </div>
                    <div class="card-body">
                        <div class="chat-test" id="chatBox">
                            <div class="message bot">
                                Xin chào! Em là chatbot tư vấn. Anh/chị cần hỗ trợ gì ạ? 😊
                            </div>
                        </div>
                        <div class="input-group mt-3">
                            <input type="text" class="form-control" id="testMessage" 
                                   placeholder="Nhập tin nhắn test...">
                            <button class="btn btn-primary" onclick="sendTestMessage()">
                                <i class="fas fa-paper-plane"></i>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Hướng dẫn -->
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-book"></i> Hướng dẫn cấu hình Facebook
                    </div>
                    <div class="card-body">
                        <ol class="mb-0">
                            <li>Truy cập <a href="https://developers.facebook.com" target="_blank">developers.facebook.com</a></li>
                            <li>Tạo App mới → Chọn "Business"</li>
                            <li>Thêm sản phẩm "Messenger"</li>
                            <li>Liên kết Page và lấy Page Access Token</li>
                            <li>Cấu hình Webhook:
                                <ul>
                                    <li>URL: <code>{{ webhook_url }}/webhook</code></li>
                                    <li>Verify Token: <code>{{ config.fb_verify_token }}</code></li>
                                    <li>Subscriptions: <code>messages</code></li>
                                </ul>
                            </li>
                            <li>Lấy App Secret từ Settings → Basic</li>
                        </ol>
                    </div>
                </div>

                <!-- Template Excel -->
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-download"></i> Template Excel
                    </div>
                    <div class="card-body">
                        <p>Tải template mẫu để nhập dữ liệu:</p>
                        <a href="/download-template" class="btn btn-success w-100">
                            <i class="fas fa-file-excel"></i> Tải Template
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function togglePassword(id) {
            const input = document.getElementById(id);
            input.type = input.type === 'password' ? 'text' : 'password';
        }

        document.getElementById('configForm').onsubmit = async function(e) {
            e.preventDefault();
            const data = {
                gemini_api_key: document.getElementById('geminiKey').value,
                fb_page_token: document.getElementById('fbToken').value,
                fb_app_secret: document.getElementById('fbSecret').value,
                fb_verify_token: document.getElementById('verifyToken').value,
            };
            
            const res = await fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            
            const result = await res.json();
            alert(result.message);
            if (result.success) location.reload();
        };

        document.getElementById('uploadForm').onsubmit = async function(e) {
            e.preventDefault();
            const formData = new FormData();
            formData.append('file', document.getElementById('excelFile').files[0]);
            
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await res.json();
            alert(result.message);
            if (result.success) location.reload();
        };

        async function deleteFile(filename) {
            if (!confirm(`Xóa file ${filename}?`)) return;
            
            const res = await fetch('/api/delete-file', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({filename})
            });
            
            const result = await res.json();
            alert(result.message);
            if (result.success) location.reload();
        }

        async function reloadData() {
            const res = await fetch('/api/reload');
            const result = await res.json();
            alert(result.message);
            location.reload();
        }

        async function sendTestMessage() {
            const input = document.getElementById('testMessage');
            const message = input.value.trim();
            if (!message) return;
            
            const chatBox = document.getElementById('chatBox');
            chatBox.innerHTML += `<div class="message user">${message}</div>`;
            input.value = '';
            chatBox.scrollTop = chatBox.scrollHeight;
            
            const res = await fetch('/api/test', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message})
            });
            
            const result = await res.json();
            chatBox.innerHTML += `<div class="message bot">${result.response}</div>`;
            if (result.image) {
                chatBox.innerHTML += `<div class="message bot"><img src="${result.image}" style="max-width:200px;border-radius:10px;"></div>`;
            }
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        document.getElementById('testMessage').onkeypress = function(e) {
            if (e.key === 'Enter') sendTestMessage();
        };
    </script>
</body>
</html>
"""

# ==================== ROUTES ====================

@app.route('/')
def admin_panel():
    """Trang quản lý chính"""
    load_config()
    init_chatbot()
    
    stats = chatbot.get_stats() if chatbot else {'total_qa': 0, 'total_conversations': 0, 'total_abbreviations': 0}
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(('.xlsx', '.xls'))] if os.path.exists(UPLOAD_FOLDER) else []
    status = 'active' if config['gemini_api_key'] and config['fb_page_token'] else 'inactive'
    
    # Tạo webhook URL (thay đổi khi deploy)
    webhook_url = request.host_url.rstrip('/')
    
    return render_template_string(ADMIN_HTML, 
                                  config=config, 
                                  stats=stats, 
                                  files=files,
                                  status=status,
                                  webhook_url=webhook_url)

@app.route('/api/config', methods=['POST'])
def update_config():
    """Cập nhật cấu hình"""
    global config
    data = request.json
    
    config['gemini_api_key'] = data.get('gemini_api_key', '')
    config['fb_page_token'] = data.get('fb_page_token', '')
    config['fb_app_secret'] = data.get('fb_app_secret', '')
    config['fb_verify_token'] = data.get('fb_verify_token', 'my_secret_verify_token')
    
    save_config()
    init_chatbot()
    
    return jsonify({'success': True, 'message': '✅ Đã lưu cấu hình!'})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload file Excel"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Không có file'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Chưa chọn file'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        
        # Reload chatbot data
        if chatbot:
            chatbot.reload_data()
        
        return jsonify({'success': True, 'message': f'✅ Đã upload {filename}'})
    
    return jsonify({'success': False, 'message': 'File không hợp lệ (chỉ chấp nhận .xlsx, .xls)'})

@app.route('/api/delete-file', methods=['POST'])
def delete_file():
    """Xóa file dữ liệu"""
    filename = request.json.get('filename')
    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(filename))
    
    if os.path.exists(filepath):
        os.remove(filepath)
        if chatbot:
            chatbot.reload_data()
        return jsonify({'success': True, 'message': f'✅ Đã xóa {filename}'})
    
    return jsonify({'success': False, 'message': 'File không tồn tại'})

@app.route('/api/reload')
def reload_data():
    """Reload dữ liệu từ file Excel"""
    if chatbot:
        count = chatbot.reload_data()
        return jsonify({'success': True, 'message': f'✅ Đã reload {count} câu hỏi-trả lời'})
    return jsonify({'success': False, 'message': 'Chatbot chưa được khởi tạo'})

@app.route('/api/test', methods=['POST'])
def test_chatbot():
    """Test chatbot"""
    if not chatbot:
        return jsonify({'response': '⚠️ Vui lòng cấu hình Gemini API Key trước', 'image': None})
    
    message = request.json.get('message', '')
    response, image = chatbot.get_response('test_user', message)
    
    return jsonify({'response': response, 'image': image})

@app.route('/download-template')
def download_template():
    """Tải template Excel mẫu"""
    import pandas as pd
    from io import BytesIO
    
    # Tạo template
    data = {
        'câu hỏi': [
            'Giá sản phẩm bao nhiêu?',
            'Có ship COD không?',
            'Bảo hành bao lâu?',
            'Có màu gì?',
        ],
        'câu trả lời': [
            'Dạ giá sản phẩm là 150.000đ/cái ạ',
            'Dạ có ship COD toàn quốc ạ, phí ship 30k',
            'Sản phẩm được bảo hành 12 tháng ạ',
            'Dạ có màu đen, trắng, xanh, hồng ạ',
        ],
        'hình ảnh': ['', '', '', ''],
        'từ khóa': ['giá, tiền, bao nhiêu', 'ship, cod, giao hàng', 'bảo hành', 'màu, color'],
        'danh mục': ['Giá cả', 'Vận chuyển', 'Chính sách', 'Sản phẩm'],
    }
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    output.seek(0)
    
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='chatbot_template.xlsx'
    )

# ==================== FACEBOOK WEBHOOK ====================

@app.route('/webhook', methods=['GET'])
def webhook_verify():
    """Xác thực webhook từ Facebook"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == config['fb_verify_token']:
        print("✅ Webhook verified!")
        return challenge, 200
    
    return 'Forbidden', 403

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Xử lý tin nhắn từ Facebook Messenger"""
    data = request.json
    
    if data.get('object') == 'page':
        for entry in data.get('entry', []):
            for event in entry.get('messaging', []):
                sender_id = event.get('sender', {}).get('id')
                
                # Xử lý tin nhắn text
                if 'message' in event and 'text' in event['message']:
                    message_text = event['message']['text']
                    print(f"📩 Received: {message_text} from {sender_id}")
                    
                    if chatbot:
                        # Xử lý trong thread riêng để không block
                        def process_message():
                            response, image = chatbot.get_response(sender_id, message_text)
                            send_messenger_message(sender_id, response, image)
                        
                        thread = threading.Thread(target=process_message)
                        thread.start()
    
    return 'OK', 200

# ==================== MAIN ====================

if __name__ == '__main__':
    # Tạo thư mục data
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Load cấu hình
    load_config()
    init_chatbot()
    
    print("=" * 50)
    print("🤖 Facebook Messenger Chatbot Server")
    print("=" * 50)
    print(f"📍 Admin Panel: http://localhost:5000")
    print(f"📍 Webhook URL: http://localhost:5000/webhook")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
