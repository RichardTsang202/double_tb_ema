"""
Telegram Bot模块 - 发送交易信号到Telegram频道
"""

import requests
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import os
from config import Config

class TelegramBot:
    """Telegram Bot类，负责发送消息和图片到频道"""
    
    def __init__(self, bot_token: str = None, channel_id: str = None):
        """
        初始化Telegram Bot
        
        Args:
            bot_token: Telegram Bot Token
            channel_id: Telegram频道ID
        """
        self.bot_token = bot_token or Config.TELEGRAM_BOT_TOKEN
        self.channel_id = channel_id or Config.TELEGRAM_CHANNEL_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.logger = logging.getLogger("TelegramBot")
        
        # 验证配置
        if not self.bot_token or not self.channel_id:
            self.logger.error("Telegram Bot Token或Channel ID未配置")
            raise ValueError("Telegram配置不完整")
    
    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """
        发送文本消息到频道
        
        Args:
            text: 消息内容
            parse_mode: 解析模式 (Markdown/HTML)
            
        Returns:
            bool: 发送是否成功
        """
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": self.channel_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(url, json=payload, timeout=Config.REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    self.logger.info("消息发送成功")
                    return True
                else:
                    self.logger.error(f"消息发送失败: {result.get('description')}")
                    return False
            else:
                self.logger.error(f"HTTP错误: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"发送消息异常: {str(e)}")
            return False
    
    def send_photo(self, photo_path: str, caption: str = "", parse_mode: str = "Markdown") -> bool:
        """
        发送图片到频道
        
        Args:
            photo_path: 图片文件路径
            caption: 图片说明
            parse_mode: 解析模式
            
        Returns:
            bool: 发送是否成功
        """
        if not os.path.exists(photo_path):
            self.logger.error(f"图片文件不存在: {photo_path}")
            return False
        
        # 检查文件大小（Telegram限制50MB）
        file_size = os.path.getsize(photo_path)
        if file_size > 50 * 1024 * 1024:  # 50MB
            self.logger.error(f"图片文件过大: {file_size} bytes")
            return False
        
        url = f"{self.base_url}/sendPhoto"
        
        try:
            with open(photo_path, 'rb') as photo_file:
                files = {'photo': photo_file}
                data = {
                    'chat_id': self.channel_id,
                    'caption': caption[:1024] if caption else "",  # Telegram限制1024字符
                    'parse_mode': parse_mode
                }
                
                self.logger.info(f"发送图片: {photo_path}, 大小: {file_size} bytes")
                response = requests.post(url, files=files, data=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        self.logger.info(f"图片发送成功: {photo_path}")
                        return True
                    else:
                        error_desc = result.get('description', 'Unknown error')
                        self.logger.error(f"图片发送失败: {error_desc}")
                        return False
                else:
                    try:
                        error_detail = response.json()
                        self.logger.error(f"HTTP错误: {response.status_code}, 详情: {error_detail}")
                    except:
                        self.logger.error(f"HTTP错误: {response.status_code}, 响应: {response.text[:200]}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"发送图片异常: {str(e)}")
            return False
    
    def send_signal_alert(self, signal_info: Dict[str, Any], chart_path: str = None) -> bool:
        """
        发送交易信号警报
        
        Args:
            signal_info: 信号信息字典
            chart_path: 图表文件路径（可选）
            
        Returns:
            bool: 发送是否成功
        """
        # 构建消息文本
        message = self._format_signal_message(signal_info)
        
        # 先发送文本消息
        text_sent = self.send_message(message)
        
        # 如果有图表，发送图表
        photo_sent = True
        if chart_path and os.path.exists(chart_path):
            caption = f"📊 {signal_info['symbol']} - {signal_info['type']} 信号图表"
            photo_sent = self.send_photo(chart_path, caption)
        
        return text_sent and photo_sent
    
    def _format_signal_message(self, signal_info: Dict[str, Any]) -> str:
        """
        格式化信号消息
        
        Args:
            signal_info: 信号信息
            
        Returns:
            str: 格式化后的消息
        """
        symbol = signal_info.get('symbol', 'Unknown')
        signal_type = signal_info.get('type', 'Unknown')
        price = signal_info.get('price', 0)
        timestamp = signal_info.get('timestamp', datetime.now())
        
        # 信号类型映射
        signal_names = {
            'double_top': '🔴 双顶形态',
            'double_bottom': '🟢 双底形态',
            'uptrend': '📈 上升趋势',
            'downtrend': '📉 下降趋势'
        }
        
        signal_name = signal_names.get(signal_type, signal_type)
        
        # 格式化时间
        if isinstance(timestamp, str):
            time_str = timestamp
        else:
            time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        message = f"""
🚨 **交易信号警报** 🚨

**交易对**: `{symbol}`
**信号类型**: {signal_name}
**当前价格**: `${price:.4f}`
**检测时间**: `{time_str}`

**技术指标**:
• EMA21: `{signal_info.get('ema21', 0):.4f}`
• EMA55: `{signal_info.get('ema55', 0):.4f}`
• ATR: `{signal_info.get('atr', 0):.4f}`

⚠️ *此信号仅供参考，请结合其他分析做出投资决策*
        """.strip()
        
        return message
    
    def send_system_status(self, status: str, details: str = "") -> bool:
        """
        发送系统状态消息
        
        Args:
            status: 状态类型 (started/stopped/error)
            details: 详细信息
            
        Returns:
            bool: 发送是否成功
        """
        status_icons = {
            'started': '🟢',
            'stopped': '🔴',
            'error': '⚠️',
            'info': 'ℹ️'
        }
        
        icon = status_icons.get(status, 'ℹ️')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        message = f"""
{icon} **系统状态更新**

**状态**: {status.upper()}
**时间**: `{timestamp}`
**详情**: {details}
        """.strip()
        
        return self.send_message(message)
    
    def test_connection(self) -> bool:
        """
        测试Telegram Bot连接
        
        Returns:
            bool: 连接是否正常
        """
        url = f"{self.base_url}/getMe"
        
        try:
            response = requests.get(url, timeout=Config.REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    bot_info = result.get("result", {})
                    self.logger.info(f"Bot连接正常: {bot_info.get('username', 'Unknown')}")
                    return True
                else:
                    self.logger.error(f"Bot连接失败: {result.get('description')}")
                    return False
            else:
                self.logger.error(f"HTTP错误: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"测试连接异常: {str(e)}")
            return False
    
    def get_chat_info(self) -> Optional[Dict]:
        """
        获取频道信息
        
        Returns:
            Dict: 频道信息，失败返回None
        """
        url = f"{self.base_url}/getChat"
        
        payload = {
            "chat_id": self.channel_id
        }
        
        try:
            response = requests.post(url, json=payload, timeout=Config.REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    return result.get("result")
                else:
                    self.logger.error(f"获取频道信息失败: {result.get('description')}")
                    return None
            else:
                self.logger.error(f"HTTP错误: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"获取频道信息异常: {str(e)}")
            return None

# 测试函数
def test_telegram_bot():
    """测试Telegram Bot功能"""
    try:
        bot = TelegramBot()
        
        print("测试Bot连接...")
        if bot.test_connection():
            print("✅ Bot连接正常")
        else:
            print("❌ Bot连接失败")
            return
        
        print("测试发送消息...")
        test_message = "🧪 这是一条测试消息"
        if bot.send_message(test_message):
            print("✅ 消息发送成功")
        else:
            print("❌ 消息发送失败")
        
        print("测试系统状态消息...")
        if bot.send_system_status("started", "K线监控系统启动测试"):
            print("✅ 状态消息发送成功")
        else:
            print("❌ 状态消息发送失败")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

if __name__ == "__main__":
    test_telegram_bot()