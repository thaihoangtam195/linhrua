"""
Facebook Messenger Chatbot Engine
Sử dụng Gemini API + Dữ liệu từ Excel
Author: Claude AI Assistant
"""

import os
import json
import re
import pandas as pd
import google.generativeai as genai
from typing import Optional, Dict, List, Tuple
from pathlib import Path
import difflib

class ChatbotEngine:
    def __init__(self, api_key: str, data_folder: str = "data"):
        """
        Khởi tạo Chatbot Engine
        
        Args:
            api_key: Gemini API Key
            data_folder: Thư mục chứa file Excel dữ liệu
        """
        self.api_key = api_key
        self.data_folder = data_folder
        self.knowledge_base = []
        self.conversation_history = {}  # Lưu lịch sử chat theo user_id
        
        # Cấu hình Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Từ điển viết tắt tiếng Việt phổ biến
        self.abbreviations = {
            'sp': 'sản phẩm',
            'đh': 'đơn hàng',
            'vc': 'vận chuyển',
            'ship': 'vận chuyển',
            'tk': 'tài khoản',
            'stk': 'số tài khoản',
            'ck': 'chuyển khoản',
            'cod': 'thanh toán khi nhận hàng',
            'sl': 'số lượng',
            'sz': 'size',
            'ms': 'mã số',
            'dt': 'điện thoại',
            'sdt': 'số điện thoại',
            'đc': 'địa chỉ',
            'dc': 'địa chỉ',
            'a': 'anh',
            'e': 'em',
            'c': 'chị',
            'mn': 'mọi người',
            'ns': 'nói',
            'bt': 'bình thường',
            'tl': 'trả lời',
            'rep': 'trả lời',
            'fb': 'facebook',
            'zl': 'zalo',
            'k': 'không',
            'ko': 'không',
            'hok': 'không',
            'dc': 'được',
            'đc': 'được',
            'đ': 'đồng',
            'vnd': 'đồng',
            'tr': 'triệu',
            'ntn': 'như thế nào',
            'lm': 'làm',
            'lsao': 'làm sao',
            'sn': 'sinh nhật',
            'hsd': 'hạn sử dụng',
            'nsx': 'ngày sản xuất',
            'bh': 'bảo hành',
            'đổi trả': 'đổi trả',
            'fship': 'freeship',
            'mfree': 'miễn phí',
            'tks': 'cảm ơn',
            'thanks': 'cảm ơn',
            'ok': 'đồng ý',
            'oki': 'đồng ý',
            'okie': 'đồng ý',
            'ak': 'à',
            'ạ': 'ạ',
            'ng': 'người',
            'nyc': 'người yêu cũ',
            'ny': 'người yêu',
            'bn': 'bao nhiêu',
            'nhiu': 'nhiêu',
            'bnh': 'bao nhiêu',
            'bnhiu': 'bao nhiêu',
            'z': 'vậy',
            'v': 'vậy',
            'r': 'rồi',
            'đi': 'đi',
            'nha': 'nha',
            'nhé': 'nhé',
            'lun': 'luôn',
            'luon': 'luôn',
            'iu': 'yêu',
            'ck': 'chồng',
            'vk': 'vợ',
            'gđ': 'gia đình',
            'hàng': 'hàng',
            'hg': 'hàng',
            'mik': 'mình',
            'mk': 'mình',
            'bạn': 'bạn',
            'bn': 'bạn',
            'b': 'bạn',
            'cj': 'chị',
            'aj': 'anh',
            'chào': 'chào',
            'hi': 'chào',
            'hello': 'chào',
            'alo': 'chào',
        }
        
        # Load dữ liệu
        self.load_data()
    
    def expand_abbreviations(self, text: str) -> str:
        """Mở rộng các từ viết tắt trong tin nhắn"""
        words = text.lower().split()
        expanded = []
        for word in words:
            # Loại bỏ dấu câu để check
            clean_word = re.sub(r'[^\w\s]', '', word)
            if clean_word in self.abbreviations:
                expanded.append(self.abbreviations[clean_word])
            else:
                expanded.append(word)
        return ' '.join(expanded)
    
    def load_data(self):
        """Load tất cả file Excel từ thư mục data"""
        self.knowledge_base = []
        data_path = Path(self.data_folder)
        
        if not data_path.exists():
            data_path.mkdir(parents=True)
            print(f"Đã tạo thư mục {self.data_folder}")
            return
        
        for file in data_path.glob("*.xlsx"):
            try:
                df = pd.read_excel(file)
                # Chuẩn hóa tên cột
                df.columns = [col.lower().strip() for col in df.columns]
                
                for _, row in df.iterrows():
                    entry = {
                        'source_file': file.name,
                        'question': str(row.get('câu hỏi', row.get('question', ''))).strip(),
                        'answer': str(row.get('câu trả lời', row.get('answer', ''))).strip(),
                        'image': str(row.get('hình ảnh', row.get('image', ''))).strip(),
                        'keywords': str(row.get('từ khóa', row.get('keywords', ''))).strip(),
                        'category': str(row.get('danh mục', row.get('category', ''))).strip(),
                    }
                    if entry['question'] and entry['question'] != 'nan':
                        self.knowledge_base.append(entry)
                        
                print(f"✅ Đã load {len(df)} dòng từ {file.name}")
            except Exception as e:
                print(f"❌ Lỗi khi đọc {file.name}: {e}")
        
        print(f"📚 Tổng cộng: {len(self.knowledge_base)} câu hỏi-trả lời")
    
    def reload_data(self):
        """Reload dữ liệu (khi cập nhật file Excel)"""
        self.load_data()
        return len(self.knowledge_base)
    
    def find_best_match(self, user_message: str) -> Optional[Dict]:
        """
        Tìm câu trả lời phù hợp nhất từ knowledge base
        Sử dụng fuzzy matching
        """
        if not self.knowledge_base:
            return None
        
        # Mở rộng viết tắt
        expanded_message = self.expand_abbreviations(user_message)
        
        best_match = None
        best_score = 0
        
        for entry in self.knowledge_base:
            question = entry['question'].lower()
            expanded_question = self.expand_abbreviations(question)
            
            # So sánh với cả tin nhắn gốc và tin nhắn đã mở rộng
            score1 = difflib.SequenceMatcher(None, user_message.lower(), question).ratio()
            score2 = difflib.SequenceMatcher(None, expanded_message, expanded_question).ratio()
            
            # Kiểm tra từ khóa
            keywords = entry.get('keywords', '').lower().split(',')
            keyword_match = any(kw.strip() in expanded_message for kw in keywords if kw.strip())
            
            # Tính điểm tổng hợp
            score = max(score1, score2)
            if keyword_match:
                score += 0.3  # Bonus nếu match từ khóa
            
            if score > best_score:
                best_score = score
                best_match = entry
        
        # Chỉ trả về nếu độ tương đồng đủ cao
        if best_score >= 0.5:
            return best_match
        return None
    
    def build_context(self) -> str:
        """Xây dựng context từ knowledge base cho Gemini"""
        context_parts = []
        
        # Nhóm theo category
        categories = {}
        for entry in self.knowledge_base:
            cat = entry.get('category', 'Chung') or 'Chung'
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(entry)
        
        for cat, entries in categories.items():
            context_parts.append(f"\n=== {cat.upper()} ===")
            for e in entries[:50]:  # Giới hạn để không quá dài
                q = e['question']
                a = e['answer']
                context_parts.append(f"Hỏi: {q}\nTrả lời: {a}")
        
        return "\n".join(context_parts)
    
    def get_response(self, user_id: str, user_message: str) -> Tuple[str, Optional[str]]:
        """
        Xử lý tin nhắn và trả về câu trả lời
        
        Args:
            user_id: ID người dùng (để lưu lịch sử)
            user_message: Tin nhắn từ khách hàng
            
        Returns:
            Tuple[str, Optional[str]]: (câu trả lời, đường dẫn hình ảnh nếu có)
        """
        # Mở rộng viết tắt
        expanded_message = self.expand_abbreviations(user_message)
        
        # Tìm trong knowledge base trước
        direct_match = self.find_best_match(user_message)
        
        # Lấy lịch sử chat
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        history = self.conversation_history[user_id]
        
        # Xây dựng prompt cho Gemini
        system_prompt = f"""Bạn là nhân viên tư vấn bán hàng chuyên nghiệp, thân thiện.
Nhiệm vụ: Trả lời câu hỏi của khách hàng dựa trên thông tin sản phẩm/dịch vụ được cung cấp.

QUY TẮC QUAN TRỌNG:
1. Trả lời ngắn gọn, thân thiện, dùng emoji phù hợp
2. Xưng hô: "em" (nhân viên) - "anh/chị" hoặc "mình" (khách hàng)
3. Nếu không có thông tin, nói "Em sẽ kiểm tra và phản hồi anh/chị sau ạ"
4. Nếu khách hỏi giá, luôn trả lời cụ thể nếu có trong dữ liệu
5. Cuối câu thường thêm "ạ" hoặc "nha" để thân thiện
6. KHÔNG bịa thông tin không có trong dữ liệu

THÔNG TIN SẢN PHẨM/DỊCH VỤ:
{self.build_context()}
"""

        # Thêm câu trả lời trực tiếp nếu tìm thấy
        if direct_match:
            system_prompt += f"""

TÌM THẤY CÂU TRẢ LỜI TRỰC TIẾP:
Câu hỏi mẫu: {direct_match['question']}
Câu trả lời mẫu: {direct_match['answer']}
(Hãy dựa vào câu trả lời mẫu này để trả lời, có thể điều chỉnh cho tự nhiên hơn)
"""

        # Xây dựng messages
        messages = []
        
        # Thêm lịch sử (giới hạn 10 tin nhắn gần nhất)
        for msg in history[-10:]:
            messages.append(msg)
        
        # Thêm tin nhắn hiện tại
        user_content = f"Khách hàng: {user_message}"
        if expanded_message != user_message.lower():
            user_content += f"\n(Hiểu là: {expanded_message})"
        
        try:
            # Gọi Gemini API
            chat = self.model.start_chat(history=[])
            full_prompt = f"{system_prompt}\n\n{user_content}\n\nTrả lời:"
            
            response = chat.send_message(full_prompt)
            answer = response.text.strip()
            
            # Lưu lịch sử
            history.append({'role': 'user', 'parts': [user_message]})
            history.append({'role': 'model', 'parts': [answer]})
            
            # Giới hạn lịch sử
            if len(history) > 20:
                self.conversation_history[user_id] = history[-20:]
            
            # Trả về kèm hình ảnh nếu có
            image_path = None
            if direct_match and direct_match.get('image') and direct_match['image'] != 'nan':
                image_path = direct_match['image']
            
            return answer, image_path
            
        except Exception as e:
            print(f"Lỗi Gemini API: {e}")
            
            # Fallback: dùng câu trả lời trực tiếp nếu có
            if direct_match:
                return direct_match['answer'], direct_match.get('image')
            
            return "Xin lỗi anh/chị, em đang gặp sự cố kỹ thuật. Anh/chị vui lòng thử lại sau ạ! 🙏", None
    
    def update_api_key(self, new_api_key: str):
        """Cập nhật API key mới"""
        self.api_key = new_api_key
        genai.configure(api_key=new_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Đã cập nhật API key mới")
    
    def add_abbreviation(self, abbr: str, full: str):
        """Thêm từ viết tắt mới"""
        self.abbreviations[abbr.lower()] = full.lower()
    
    def get_stats(self) -> Dict:
        """Lấy thống kê"""
        return {
            'total_qa': len(self.knowledge_base),
            'total_conversations': len(self.conversation_history),
            'total_abbreviations': len(self.abbreviations),
        }


# Test
if __name__ == "__main__":
    # Test với API key giả
    print("🤖 Chatbot Engine đã sẵn sàng!")
    print("Để sử dụng, cần tạo instance với API key thật:")
    print("  bot = ChatbotEngine('your-gemini-api-key')")
    print("  response, image = bot.get_response('user123', 'Giá sản phẩm bao nhiêu?')")
