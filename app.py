# -*- coding: utf-8 -*-
"""
K线信号实时监控系统
功能：监控双顶/双底形态和EMA均线趋势
版本：1.0
"""

import requests
import pandas as pd
import numpy as np
import time
import logging
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import os

# 配置管理类 - 集成自config.py
class Config:
    """配置管理类"""
    
    # 交易所API配置
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', 'lXsXOr3LITEDlRfTgt6OeDTKS97eTzwZWZFb3un59vhfZOxMwDg0ZSb1l33Z0mcw')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', 'hEV1bJBTSWKi2jROWLlX6rEhQiulCWnzssfPaEZOtn04giAMLwiQwHBtcV3roH8n')
    
    OKX_API_KEY = os.getenv('OKX_API_KEY', '088e881b-046d-436d-9222-fc035f1392ef')
    OKX_SECRET_KEY = os.getenv('OKX_SECRET_KEY', '0ED348032873BD4CE12515575049A02F')
    OKX_PASSPHRASE = os.getenv('OKX_PASSPHRASE', '')  # OKX需要passphrase
    
    # Telegram配置
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8079021434:AAGcoQXZOxaBgkXPd6L9TKARegltWzTP3DU')
    TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID', '-1002434065698')
    
    # 监控配置
    SYMBOLS = [
        "BTCUSDT", "ETHUSDT", "XRPUSDT", "ADAUSDT", "DOTUSDT",
        "BNBUSDT", "SOLUSDT", "MATICUSDT", "AVAXUSDT", "LINKUSDT"
    ]
    
    # 技术指标参数
    ATR_PERIOD = 14
    EMA_PERIODS = [21, 55, 200]
    
    # 双顶/双底检测参数
    DOUBLE_PATTERN_ATR_THRESHOLD = 0.8  # A与B点差值阈值（ATR倍数）
    DOUBLE_PATTERN_DEPTH_THRESHOLD = 2.3  # C点深度阈值（ATR倍数）
    
    # EMA趋势检测参数
    EMA_CONVERGENCE_THRESHOLD = 0.5  # EMA聚合度阈值
    EMA_CONVERGENCE_LOOKBACK = 21  # 回溯周期
    
    # 数据缓存配置
    CACHE_A_POINT_START = 13  # A点范围开始（从最新收盘K线往左数）
    CACHE_A_POINT_END = 34    # A点范围结束
    CACHE_KLINES_COUNT = 200  # 缓存K线数量
    CHART_KLINES_COUNT = 55   # 图表显示K线数量
    
    # API请求配置
    REQUEST_TIMEOUT = 10  # 请求超时时间（秒）
    REQUEST_INTERVAL = 3  # 请求间隔时间（秒）
    MAX_RETRIES = 2       # 最大重试次数
    UPDATE_INTERVAL = 300 # 检测间隔时间（秒，默认5分钟）
    
    # 文件路径配置
    LOG_DIR = os.getenv('LOG_DIR', "logs")
    CHART_DIR = os.getenv('CHART_DIR', "charts")
    DATA_DIR = os.getenv('DATA_DIR', "data")
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')  # 日志级别配置
    
    # 交易所API端点
    EXCHANGE_ENDPOINTS = {
        "binance": {
            "klines": "https://api.binance.com/api/v3/klines"
        },
        "okx": {
            "klines": "https://www.okx.com/api/v5/market/candles"
        }
    }
    
    # MACD参数
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # RSI参数
    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    
    @classmethod
    def validate_config(cls) -> bool:
        """验证配置是否完整"""
        required_fields = [
            'BINANCE_API_KEY', 'BINANCE_SECRET_KEY',
            'OKX_API_KEY', 'OKX_SECRET_KEY',
            'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHANNEL_ID'
        ]
        
        for field in required_fields:
            if not getattr(cls, field):
                print(f"警告: 配置项 {field} 未设置")
                return False
        
        return True
    
    @classmethod
    def get_symbol_mapping(cls, exchange: str) -> Dict[str, str]:
        """获取交易对映射"""
        if exchange == "binance":
            # 币安不需要转换
            return {symbol: symbol for symbol in cls.SYMBOLS}
        elif exchange == "okx":
            # OKX使用不同的交易对格式
            mapping = {}
            for symbol in cls.SYMBOLS:
                if symbol.endswith("USDT"):
                    # BTCUSDT -> BTC-USDT
                    base = symbol[:-4]
                    mapping[symbol] = f"{base}-USDT"
                else:
                    mapping[symbol] = symbol
            return mapping
        else:
            return {symbol: symbol for symbol in cls.SYMBOLS}
    
    @classmethod
    def create_directories(cls):
        """创建必要的目录"""
        directories = [cls.LOG_DIR, cls.CHART_DIR, cls.DATA_DIR]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"创建目录: {directory}")

# TelegramBot类 - 集成自telegram_bot.py
class TelegramBot:
    """Telegram Bot功能类"""
    
    def __init__(self):
        """初始化Telegram Bot"""
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.channel_id = Config.TELEGRAM_CHANNEL_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.logger = logging.getLogger("TelegramBot")
    
    def test_connection(self) -> bool:
        """测试Bot连接"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    self.logger.info("Telegram Bot连接测试成功")
                    return True
            
            self.logger.error(f"Bot连接测试失败: {response.status_code}")
            return False
            
        except Exception as e:
            self.logger.error(f"Bot连接测试异常: {str(e)}")
            return False
    
    def send_message(self, text: str, parse_mode: str = None) -> bool:
        """发送文本消息"""
        try:
            url = f"{self.base_url}/sendMessage"
            
            payload = {
                'chat_id': self.channel_id,
                'text': text
            }
            
            # 只在明确指定时添加parse_mode
            if parse_mode:
                payload['parse_mode'] = parse_mode
            
            response = requests.post(url, json=payload, timeout=30)
            
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
    
    def send_photo(self, photo_path: str, caption: str = "", parse_mode: str = None) -> bool:
        """发送图片"""
        try:
            if not os.path.exists(photo_path):
                self.logger.error(f"图片文件不存在: {photo_path}")
                return False
            
            # 获取文件大小
            file_size = os.path.getsize(photo_path)
            self.logger.info(f"发送图片: {photo_path}, 大小: {file_size} bytes")
            
            url = f"{self.base_url}/sendPhoto"
            
            with open(photo_path, 'rb') as photo_file:
                files = {'photo': photo_file}
                
                data = {
                    'chat_id': self.channel_id,
                    'caption': caption
                }
                
                # 只在明确指定时添加parse_mode
                if parse_mode:
                    data['parse_mode'] = parse_mode
                
                response = requests.post(url, files=files, data=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    self.logger.info("图片发送成功")
                    return True
                else:
                    self.logger.error(f"图片发送失败: {result.get('description')}")
                    return False
            else:
                self.logger.error(f"HTTP错误: {response.status_code}, 详情: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"发送图片异常: {str(e)}")
            return False
    
    def send_signal_alert(self, signal_info: Dict, chart_path: str = None) -> bool:
        """发送信号提醒"""
        try:
            # 格式化消息
            message = self._format_signal_message(signal_info)
            
            # 先发送文本消息
            if not self.send_message(message):
                return False
            
            # 如果有图表，发送图片
            if chart_path and os.path.exists(chart_path):
                caption = f"{signal_info['symbol']} {signal_info['type']} 信号图表"
                return self.send_photo(chart_path, caption)
            
            return True
            
        except Exception as e:
            self.logger.error(f"发送信号提醒异常: {str(e)}")
            return False
    
    def send_system_status(self, status: str, message: str = "") -> bool:
        """发送系统状态"""
        try:
            status_icons = {
                "started": "🟢",
                "stopped": "🔴", 
                "error": "❌",
                "warning": "⚠️"
            }
            
            icon = status_icons.get(status, "ℹ️")
            text = f"{icon} 系统状态: {status.upper()}"
            
            if message:
                text += f"\n{message}"
            
            text += f"\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return self.send_message(text)
            
        except Exception as e:
            self.logger.error(f"发送系统状态异常: {str(e)}")
            return False
    
    def _format_signal_message(self, signal_info: Dict) -> str:
        """格式化信号消息"""
        try:
            symbol = signal_info['symbol']
            signal_type = signal_info['type']
            price = signal_info['price']
            timestamp = signal_info['timestamp']
            
            # 信号类型映射
            type_mapping = {
                'double_top': '双顶信号',
                'double_bottom': '双底信号',
                'uptrend': 'EMA上升趋势',
                'downtrend': 'EMA下降趋势'
            }
            
            signal_name = type_mapping.get(signal_type, signal_type)
            
            # 使用纯文本格式，避免特殊字符和Markdown解析错误
            message = f"[信号] {signal_name}\n"
            message += f"交易对: {symbol}\n"
            message += f"价格: {price:.4f}\n"
            
            if 'ema21' in signal_info and signal_info['ema21']:
                message += f"EMA21: {signal_info['ema21']:.4f}\n"
            
            if 'ema55' in signal_info and signal_info['ema55']:
                message += f"EMA55: {signal_info['ema55']:.4f}\n"
            
            if 'atr' in signal_info and signal_info['atr']:
                message += f"ATR: {signal_info['atr']:.4f}\n"
            
            # 解析时间戳
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                message += f"时间: {dt.strftime('%Y-%m-%d %H:%M:%S')}"
            except:
                message += f"时间: {timestamp}"
            
            return message
            
        except Exception as e:
            self.logger.error(f"格式化信号消息失败: {str(e)}")
            return f"信号提醒: {signal_info.get('symbol', 'Unknown')} - {signal_info.get('type', 'Unknown')}"

# 配置matplotlib支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 配置日志系统
def setup_logging():
    """设置日志配置"""
    # 确保日志目录存在
    if not os.path.exists(Config.LOG_DIR):
        os.makedirs(Config.LOG_DIR)
        
    log_file = os.path.join(Config.LOG_DIR, "kline_monitor.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("KlineMonitor")

class KlineMonitor:
    """
    主监控类，负责协调所有功能模块
    """
    
    def __init__(self, symbols: List[str]):
        """
        初始化监控器
        """
        self.symbols = symbols
        self.data_cache = {}
        self.signals = {}
        self.logger = setup_logging()
        
        # 初始化Telegram Bot
        try:
            self.telegram_bot = TelegramBot()
            self.logger.info("Telegram Bot初始化成功")
        except Exception as e:
            self.logger.warning(f"Telegram Bot初始化失败: {str(e)}")
            self.telegram_bot = None
        
        # 交易所API配置
        self.exchanges = {
            "binance": "https://api.binance.com/api/v3/klines",
            "okx": "https://www.okx.com/api/v5/market/candles"
        }
        self.current_exchange = "binance"
        
        # 初始化数据结构
        for symbol in symbols:
            self.data_cache[symbol] = {
                'klines': [],
                'A_top': None,
                'A_bottom': None,
                'A_top_index': None,
                'A_bottom_index': None,
                'ema21': None,
                'ema55': None,
                'atr': None,
                'last_update': None
            }
    
    def run(self):
        """主运行循环"""
        self.logger.info("启动K线信号监控系统")
        
        # 发送系统启动通知
        if self.telegram_bot:
            try:
                symbols_str = ", ".join(self.symbols)
                self.telegram_bot.send_system_status(
                    "started", 
                    f"监控交易对: {symbols_str}"
                )
                self.logger.info("系统启动通知已发送")
            except Exception as e:
                self.logger.error(f"发送启动通知失败: {str(e)}")
        
        # 步骤1：初始化所有交易对
        for symbol in self.symbols:
            self.logger.info(f"初始化交易对: {symbol}")
            if not self.initialize_symbol(symbol):
                self.logger.error(f"初始化失败: {symbol}")
                continue
            time.sleep(2)  # 避免API限制
        
        # 步骤2：开始实时监控循环
        while True:
            try:
                for symbol in self.symbols:
                    self.logger.info(f"检查交易对: {symbol}")
                    
                    # 步骤3：更新数据
                    if not self.update_symbol_data(symbol):
                        self.logger.error(f"数据更新失败: {symbol}")
                        continue
                    
                    # 步骤4：检查双顶/双底形态
                    pattern_signal = self.check_double_pattern(symbol)
                    if pattern_signal:
                        self.handle_signal(symbol, pattern_signal)
                    
                    # 步骤5：检查EMA趋势
                    trend_signal = self.check_ema_trend(symbol)
                    if trend_signal:
                        self.handle_signal(symbol, trend_signal)
                    
                    time.sleep(3)  # 每个交易对间隔3秒
                
                # 保存信号数据
                self.save_signals_to_file()
                
                # 等待下一个小时的05秒
                self.wait_for_next_hour()
                
            except Exception as e:
                self.logger.error(f"监控循环异常: {str(e)}")
                time.sleep(60)  # 出错后等待1分钟
    
    def wait_for_next_hour(self):
        """等待到下一个小时的05秒"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        # 计算下一个小时的05秒
        next_hour = now.replace(minute=0, second=5, microsecond=0) + timedelta(hours=1)
        
        # 如果当前时间已经过了本小时的05秒，则等待到下一个小时的05秒
        if now.second >= 5 and now.minute == 0:
            # 如果当前正好是某小时的05秒之后，等待到下一个小时
            pass
        elif now.minute == 0 and now.second < 5:
            # 如果当前是某小时的00-04秒，等待到本小时的05秒
            next_hour = now.replace(second=5, microsecond=0)
        
        wait_seconds = (next_hour - now).total_seconds()
        
        self.logger.info(f"本轮检测完成，等待到 {next_hour.strftime('%H:%M:%S')} 开始下一轮检测...")
        self.logger.info(f"等待时间: {wait_seconds:.1f} 秒")
        
        time.sleep(wait_seconds)
    
    def switch_exchange(self):
        """切换交易所"""
        if self.current_exchange == "binance":
            self.current_exchange = "okx"
        else:
            self.current_exchange = "binance"
        self.logger.info(f"切换到交易所: {self.current_exchange}")
    
    def fetch_klines(self, symbol: str, interval: str = "1h", limit: int = 300) -> Optional[List]:
        """获取K线数据"""
        try:
            if self.current_exchange == "binance":
                url = self.exchanges["binance"]
                params = {
                    'symbol': symbol,
                    'interval': interval,
                    'limit': limit
                }
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    return [{
                        'timestamp': int(item[0]),
                        'open': float(item[1]),
                        'high': float(item[2]),
                        'low': float(item[3]),
                        'close': float(item[4]),
                        'volume': float(item[5])
                    } for item in data]
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取K线数据失败 {symbol}: {str(e)}")
            return None
    
    def initialize_symbol(self, symbol: str) -> bool:
        """步骤1：初始化交易对，缓存200根K线并找出A点"""
        klines = self.fetch_klines(symbol, "1h", 200)
        if not klines or len(klines) < 200:
            return False
        
        self.data_cache[symbol]['klines'] = klines
        self._calculate_ab_points(symbol)
        self._calculate_indicators(symbol)
        
        self.logger.info(f"{symbol} 初始化完成，缓存了 {len(klines)} 根K线")
        return True
    
    def _calculate_ab_points(self, symbol: str):
        """计算A点（从最新收盘K线往左数第13到34根K线的最高价和最低价）"""
        klines = self.data_cache[symbol]['klines']
        if len(klines) < 34:
            return
        
        # 从最新收盘K线往左数第13到34根K线中找A点
        # 倒数第34根对应索引len-34，倒数第13根对应索引len-13
        start_index = len(klines) - 34
        end_index = len(klines) - 13
        
        if start_index < 0:
            start_index = 0
        if end_index >= len(klines):
            end_index = len(klines) - 1
            
        search_range = klines[start_index:end_index + 1]
        
        if not search_range:
            return
        
        # 找最高价作为A_top
        max_high = max(k['high'] for k in search_range)
        for i, k in enumerate(search_range):
            if k['high'] == max_high:
                self.data_cache[symbol]['A_top'] = max_high
                self.data_cache[symbol]['A_top_index'] = start_index + i
                break
        
        # 找最低价作为A_bottom
        min_low = min(k['low'] for k in search_range)
        for i, k in enumerate(search_range):
            if k['low'] == min_low:
                self.data_cache[symbol]['A_bottom'] = min_low
                self.data_cache[symbol]['A_bottom_index'] = start_index + i
                break
        
        self.logger.info(f"{symbol} A点计算完成 - A_top: {self.data_cache[symbol]['A_top']:.4f}, "
                        f"A_bottom: {self.data_cache[symbol]['A_bottom']:.4f}, "
                        f"A_top_index: {self.data_cache[symbol].get('A_top_index')}, "
                        f"A_bottom_index: {self.data_cache[symbol].get('A_bottom_index')}")
    
    def _calculate_indicators(self, symbol: str):
        """计算技术指标"""
        klines = self.data_cache[symbol]['klines']
        closes = [k['close'] for k in klines]
        
        # 计算EMA
        if len(closes) >= 21:
            self.data_cache[symbol]['ema21'] = self.calculate_ema(closes, 21)
        if len(closes) >= 55:
            self.data_cache[symbol]['ema55'] = self.calculate_ema(closes, 55)
        if len(closes) >= 144:
            self.data_cache[symbol]['ema144'] = self.calculate_ema(closes, 144)
        
        # 计算ATR
        self.data_cache[symbol]['atr'] = self.calculate_atr(klines)
        
        self.logger.info(f"{symbol} 指标计算完成")
    
    def update_symbol_data(self, symbol: str) -> bool:
        """步骤3：获取实时最新收盘K线并更新缓存"""
        try:
            # 获取最新的K线数据
            new_klines = self.fetch_klines(symbol, "1h", 5)  # 获取最新5根
            if not new_klines:
                return False
            
            # 获取当前缓存的K线
            cached_klines = self.data_cache[symbol]['klines']
            
            # 合并新数据，去重并保持200根
            all_klines = cached_klines + new_klines
            
            # 按时间戳去重
            unique_klines = {}
            for kline in all_klines:
                unique_klines[kline['timestamp']] = kline
            
            # 按时间排序并保持最新200根
            sorted_klines = sorted(unique_klines.values(), key=lambda x: x['timestamp'])
            old_klines_len = len(cached_klines)
            new_klines_data = sorted_klines[-200:]
            new_klines_len = len(new_klines_data)
            
            # 计算K线数据变化量，调整A点索引
            if old_klines_len > 0 and new_klines_len > 0:
                # 计算数据偏移量
                offset = new_klines_len - old_klines_len
                
                # 调整A点索引（如果存在）
                if 'A_top_index' in self.data_cache[symbol] and self.data_cache[symbol]['A_top_index'] is not None:
                    old_a_top_index = self.data_cache[symbol]['A_top_index']
                    new_a_top_index = old_a_top_index + offset
                    # 确保索引在有效范围内
                    if 0 <= new_a_top_index < new_klines_len:
                        self.data_cache[symbol]['A_top_index'] = new_a_top_index
                    else:
                        # 如果A点索引超出范围，重新计算A点
                        self.data_cache[symbol]['klines'] = new_klines_data
                        self._calculate_ab_points(symbol)
                        
                if 'A_bottom_index' in self.data_cache[symbol] and self.data_cache[symbol]['A_bottom_index'] is not None:
                    old_a_bottom_index = self.data_cache[symbol]['A_bottom_index']
                    new_a_bottom_index = old_a_bottom_index + offset
                    # 确保索引在有效范围内
                    if 0 <= new_a_bottom_index < new_klines_len:
                        self.data_cache[symbol]['A_bottom_index'] = new_a_bottom_index
                    else:
                        # 如果A点索引超出范围，重新计算A点
                        self.data_cache[symbol]['klines'] = new_klines_data
                        self._calculate_ab_points(symbol)
            
            self.data_cache[symbol]['klines'] = new_klines_data
            
            # 检查缓存有效性
            if not self.check_cache_validity(symbol):
                self.logger.warning(f"{symbol} 缓存无效，重新初始化")
                return self.initialize_symbol(symbol)
            
            # 更新指标
            self._calculate_indicators(symbol)
            self.data_cache[symbol]['last_update'] = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.error(f"{symbol} 数据更新失败: {str(e)}")
            return False
    
    def check_cache_validity(self, symbol: str) -> bool:
        """检查缓存数据有效性"""
        klines = self.data_cache[symbol]['klines']
        
        # 检查数量
        if len(klines) < 200:
            return False
        
        # 检查时间连续性（允许少量缺失）
        timestamps = [k['timestamp'] for k in klines]
        time_diffs = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        
        # 1小时 = 3600000毫秒，允许一定误差
        expected_diff = 3600000
        valid_diffs = sum(1 for diff in time_diffs if abs(diff - expected_diff) < 600000)  # 10分钟误差
        
        return valid_diffs / len(time_diffs) > 0.9  # 90%的数据连续性
    
    def calculate_atr(self, klines: List, period: int = 14) -> float:
        """计算ATR（平均真实波幅）"""
        if len(klines) < period + 1:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(klines)):
            high = klines[i]['high']
            low = klines[i]['low']
            prev_close = klines[i-1]['close']
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_ranges.append(max(tr1, tr2, tr3))
        
        # 计算ATR（简单移动平均）
        if len(true_ranges) >= period:
            return sum(true_ranges[-period:]) / period
        else:
            return sum(true_ranges) / len(true_ranges)
    
    def calculate_ema_series(self, prices: List[float], period: int) -> List[float]:
        """计算EMA序列"""
        if len(prices) < period:
            return []
        
        ema_values = []
        multiplier = 2 / (period + 1)
        
        # 第一个EMA值使用SMA
        sma = sum(prices[:period]) / period
        ema_values.append(sma)
        
        # 计算后续EMA值
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)
        
        return ema_values
    
    def calculate_ema(self, prices: List[float], period: int) -> float:
        """计算单个EMA值"""
        if len(prices) < period:
            return 0.0
        
        multiplier = 2 / (period + 1)
        
        # 第一个EMA值使用SMA
        ema = sum(prices[:period]) / period
        
        # 计算后续EMA值
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def calculate_ema_convergence(self, klines: List, atr: float) -> float:
        """计算EMA收敛度 - 使用21根K线回溯窗口均值法"""
        if len(klines) < 144:  # 需要足够的数据计算EMA144
            return 1.0  # 返回高值表示不收敛
        
        closes = [k['close'] for k in klines]
        
        # 计算过去21根K线的平均相对聚合度
        ratios = []
        
        # 从最新K线开始往前21根
        for i in range(21):
            # 计算当前位置的EMA值
            current_closes = closes[:-(i) if i > 0 else len(closes)]
            
            if len(current_closes) < 144:
                continue
                
            ema21 = self.calculate_ema(current_closes, 21)
            ema55 = self.calculate_ema(current_closes, 55)
            ema144 = self.calculate_ema(current_closes, 144)
            
            # 计算均线瞬时宽度
            span = max(ema21, ema55, ema144) - min(ema21, ema55, ema144)
            
            # 计算相对聚合度
            if atr > 0:
                ratio = span / atr
                ratios.append(ratio)
        
        if not ratios:
            return 1.0
        
        # 计算窗口期内的平均聚合水平
        avg_ratio = sum(ratios) / len(ratios)
        return avg_ratio
    
    def check_double_pattern(self, symbol: str) -> Optional[str]:
        """步骤4：检查双顶/双底形态"""
        try:
            klines = self.data_cache[symbol]['klines']
            if len(klines) < 200:
                return None
            
            A_top = self.data_cache[symbol]['A_top']
            A_bottom = self.data_cache[symbol]['A_bottom']
            A_top_index = self.data_cache[symbol]['A_top_index']
            A_bottom_index = self.data_cache[symbol]['A_bottom_index']
            atr = self.data_cache[symbol]['atr']
            ema21 = self.data_cache[symbol]['ema21']
            ema55 = self.data_cache[symbol]['ema55']
            ema144 = self.data_cache[symbol]['ema144']
            
            if not all([A_top, A_bottom, atr, ema21, ema55, ema144]):
                return None
            
            # B点定义：最新收盘K线（倒数第二根K线，因为最后一根可能未收盘）
            latest_closed_kline = klines[-2]  # 最新收盘K线
            B_top = latest_closed_kline['high']
            B_bottom = latest_closed_kline['low']
            
            # 双顶检测
            if abs(A_top - B_top) <= 0.8 * atr:
                # 寻找C_bottom：A_top与B_top之间的最低点
                B_top_index = len(klines) - 2  # B点索引（最新收盘K线）
                
                # 确保A点在B点之前（时间顺序）
                if A_top_index >= B_top_index:
                    return None  # A点应该在B点之前
                
                start_index = A_top_index
                end_index = B_top_index
                
                if start_index < end_index:
                    c_range = klines[start_index + 1:end_index]  # A和B之间的K线，不包括A和B本身
                    if c_range:  # 确保A和B之间有K线
                        C_bottom = min(k['low'] for k in c_range)
                        
                        # 检查C_bottom与A_top和B_top的差值（C点应该明显低于A、B点）
                        if (A_top - C_bottom) >= 2.3 * atr and (B_top - C_bottom) >= 2.3 * atr:
                            # 检查EMA条件：不满足ema21>ema55>ema144
                            if not (ema21 > ema55 > ema144):
                                # 缓存B点和C点信息用于绘图
                                self.data_cache[symbol]['B_top'] = B_top
                                self.data_cache[symbol]['B_top_index'] = B_top_index
                                self.data_cache[symbol]['C_bottom'] = C_bottom
                                # 找到C_bottom对应的索引（选择第一个匹配的）
                                c_bottom_index = None
                                for i, k in enumerate(c_range):
                                    if k['low'] == C_bottom:
                                        c_bottom_index = start_index + 1 + i
                                        break
                                if c_bottom_index is not None:
                                    self.data_cache[symbol]['C_bottom_index'] = c_bottom_index
                                return 'double_top'
            
            # 双底检测
            if abs(A_bottom - B_bottom) <= 0.8 * atr:
                # 寻找C_top：A_bottom与B_bottom之间的最高点
                B_bottom_index = len(klines) - 2  # B点索引（最新收盘K线）
                
                # 确保A点在B点之前（时间顺序）
                if A_bottom_index >= B_bottom_index:
                    return None  # A点应该在B点之前
                
                start_index = A_bottom_index
                end_index = B_bottom_index
                
                if start_index < end_index:
                    c_range = klines[start_index + 1:end_index]  # A和B之间的K线，不包括A和B本身
                    if c_range:  # 确保A和B之间有K线
                        C_top = max(k['high'] for k in c_range)
                        
                        # 检查C_top与A_bottom和B_bottom的差值（C点应该明显高于A、B点）
                        if (C_top - A_bottom) >= 2.3 * atr and (C_top - B_bottom) >= 2.3 * atr:
                            # 检查EMA条件：不满足ema21<ema55<ema144
                            if not (ema21 < ema55 < ema144):
                                # 缓存B点和C点信息用于绘图
                                self.data_cache[symbol]['B_bottom'] = B_bottom
                                self.data_cache[symbol]['B_bottom_index'] = B_bottom_index
                                self.data_cache[symbol]['C_top'] = C_top
                                # 找到C_top对应的索引（选择第一个匹配的）
                                c_top_index = None
                                for i, k in enumerate(c_range):
                                    if k['high'] == C_top:
                                        c_top_index = start_index + 1 + i
                                        break
                                if c_top_index is not None:
                                    self.data_cache[symbol]['C_top_index'] = c_top_index
                                return 'double_bottom'
            
            return None
            
        except Exception as e:
            self.logger.error(f"{symbol} 双顶双底检查失败: {str(e)}")
            return None
    
    def check_ema_trend(self, symbol: str) -> Optional[str]:
        """步骤5：检查EMA趋势"""
        try:
            # 获取缓存数据
            if symbol not in self.data_cache:
                return None
            
            klines = self.data_cache[symbol]['klines']
            if len(klines) < 144:  # 需要足够数据计算EMA144
                return None
            
            # 获取当前和前一根K线的EMA值
            closes = [k['close'] for k in klines]
            
            # 当前K线的EMA
            current_ema21 = self.calculate_ema(closes, 21)
            current_ema55 = self.calculate_ema(closes, 55)
            current_ema144 = self.calculate_ema(closes, 144)
            
            # 前一根K线的EMA
            prev_closes = closes[:-1]
            if len(prev_closes) < 144:
                return None
            
            prev_ema21 = self.calculate_ema(prev_closes, 21)
            prev_ema55 = self.calculate_ema(prev_closes, 55)
            prev_ema144 = self.calculate_ema(prev_closes, 144)
            
            # 检查上升趋势
            current_uptrend = current_ema21 > current_ema55 > current_ema144
            prev_uptrend = prev_ema21 > prev_ema55 > prev_ema144
            
            # 检查下降趋势
            current_downtrend = current_ema21 < current_ema55 < current_ema144
            prev_downtrend = prev_ema21 < prev_ema55 < prev_ema144
            
            # 二次筛选条件：检查EMA收敛度
            atr = self.data_cache[symbol]['atr']
            convergence_ratio = self.calculate_ema_convergence(klines, atr)
            
            # 判断趋势启动
            if current_uptrend and not prev_uptrend and convergence_ratio < 0.5:
                return "上升趋势"
            elif current_downtrend and not prev_downtrend and convergence_ratio < 0.5:
                return "下降趋势"
            
            return None
            
        except Exception as e:
            self.logger.error(f"EMA趋势检查失败: {str(e)}")
            return None
    
    def handle_signal(self, symbol: str, signal_type: str):
        """处理信号"""
        try:
            current_price = self.data_cache[symbol]['klines'][-1]['close']
            
            signal_info = {
                'symbol': symbol,
                'type': signal_type,
                'price': current_price,
                'timestamp': datetime.now().isoformat(),
                'ema21': self.data_cache[symbol]['ema21'],
                'ema55': self.data_cache[symbol]['ema55'],
                'atr': self.data_cache[symbol]['atr']
            }
            
            # 存储信号
            if symbol not in self.signals:
                self.signals[symbol] = []
            self.signals[symbol].append(signal_info)
            
            # 生成图表
            chart_path = self.plot_signal(symbol, signal_type)
            
            # 发送Telegram通知
            if self.telegram_bot:
                try:
                    success = self.telegram_bot.send_signal_alert(signal_info, chart_path)
                    if success:
                        self.logger.info(f"Telegram通知发送成功: {symbol} {signal_type}")
                    else:
                        self.logger.warning(f"Telegram通知发送失败: {symbol} {signal_type}")
                except Exception as e:
                    self.logger.error(f"发送Telegram通知时出错: {str(e)}")
            
            self.logger.info(f"📊 {symbol} {signal_type} 信号 - 价格: {current_price:.4f}")
            
        except Exception as e:
            self.logger.error(f"处理信号失败: {str(e)}")
    
    def calculate_macd(self, closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9):
        """计算MACD指标"""
        if len(closes) < slow:
            return [], [], []
        
        # 计算EMA
        ema_fast = self.calculate_ema_series(closes, fast)
        ema_slow = self.calculate_ema_series(closes, slow)
        
        # 对齐长度
        min_len = min(len(ema_fast), len(ema_slow))
        if min_len == 0:
            return [], [], []
        
        ema_fast = ema_fast[-min_len:]
        ema_slow = ema_slow[-min_len:]
        
        # 计算MACD线
        macd_line = [ema_fast[i] - ema_slow[i] for i in range(min_len)]
        
        # 计算信号线
        if len(macd_line) >= signal:
            signal_line = self.calculate_ema_series(macd_line, signal)
        else:
            signal_line = []
        
        # 计算柱状图
        if len(signal_line) > 0:
            histogram = [macd_line[i] - signal_line[i] for i in range(len(signal_line))]
        else:
            histogram = []
        
        return macd_line, signal_line, histogram
    
    def calculate_rsi(self, closes: List[float], period: int = 14):
        """计算RSI指标"""
        if len(closes) < period + 1:
            return []
        
        # 计算价格变化
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        # 分离上涨和下跌
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        rsi_values = []
        
        # 计算第一个RSI值
        if len(gains) >= period:
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period
            
            if avg_loss == 0:
                rsi_values.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                rsi_values.append(rsi)
            
            # 计算后续RSI值
            for i in range(period, len(gains)):
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
                
                if avg_loss == 0:
                    rsi_values.append(100)
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                    rsi_values.append(rsi)
        
        return rsi_values
    
    def plot_signal(self, symbol: str, signal_type: str):
        """步骤7：生成信号图表（基于55根K线）"""
        try:
            # 获取最近55根K线用于绘图
            all_klines = self.data_cache[symbol]['klines']
            chart_klines = all_klines[-55:]
            
            closes = [k['close'] for k in chart_klines]
            highs = [k['high'] for k in chart_klines]
            lows = [k['low'] for k in chart_klines]
            volumes = [k['volume'] for k in chart_klines]
            
            # 计算指标 - 使用全部300根K线数据计算，然后取最后55个值
            all_closes = [k['close'] for k in all_klines]
            
            # 计算EMA序列（使用全部数据）
            ema21_full = self.calculate_ema_series(all_closes, 21)
            ema55_full = self.calculate_ema_series(all_closes, 55)
            ema144_full = self.calculate_ema_series(all_closes, 144)
            
            # 取最后55个值用于绘图
            ema21_series = ema21_full[-55:] if len(ema21_full) >= 55 else ema21_full
            ema55_series = ema55_full[-55:] if len(ema55_full) >= 55 else ema55_full
            ema144_series = ema144_full[-55:] if len(ema144_full) >= 55 else ema144_full
            
            # 计算MACD和RSI（使用全部数据）
            macd_line_full, signal_line_full, histogram_full = self.calculate_macd(all_closes)
            rsi_values_full = self.calculate_rsi(all_closes)
            
            # 取最后55个值用于绘图
            macd_line = macd_line_full[-55:] if len(macd_line_full) >= 55 else macd_line_full
            signal_line = signal_line_full[-55:] if len(signal_line_full) >= 55 else signal_line_full
            histogram = histogram_full[-55:] if len(histogram_full) >= 55 else histogram_full
            rsi_values = rsi_values_full[-55:] if len(rsi_values_full) >= 55 else rsi_values_full
            
            # 创建图表
            fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(15, 16), 
                                                   gridspec_kw={'height_ratios': [3, 0.8, 1, 1]})
            
            # 主图：K线图
            x_range = range(len(chart_klines))
            
            # 绘制K线 - 绿涨红跌
            for i in x_range:
                color = 'green' if closes[i] >= chart_klines[i]['open'] else 'red'
                ax1.plot([i, i], [lows[i], highs[i]], color='black', linewidth=0.8)
                ax1.plot([i, i], [chart_klines[i]['open'], closes[i]], color=color, linewidth=3)
            
            # 绘制EMA线 - 确保x轴对齐
            chart_len = len(chart_klines)
            
            if len(ema21_series) > 0:
                # 计算EMA21的起始位置
                ema21_start = max(0, chart_len - len(ema21_series))
                ema21_x = range(ema21_start, chart_len)
                ax1.plot(ema21_x, ema21_series, 'yellow', label='EMA21', linewidth=1.5)
            
            if len(ema55_series) > 0:
                # 计算EMA55的起始位置
                ema55_start = max(0, chart_len - len(ema55_series))
                ema55_x = range(ema55_start, chart_len)
                ax1.plot(ema55_x, ema55_series, 'green', label='EMA55', linewidth=1.5)
            
            if len(ema144_series) > 0:
                # 计算EMA144的起始位置
                ema144_start = max(0, chart_len - len(ema144_series))
                ema144_x = range(ema144_start, chart_len)
                ax1.plot(ema144_x, ema144_series, 'red', label='EMA144', linewidth=1.5)
            
            # 标记关键点（如果是双顶/双底信号）
            if signal_type in ['double_top', 'double_bottom']:
                self._mark_pattern_points(ax1, symbol, signal_type, all_klines, chart_klines)
            
            ax1.set_title(f'{symbol} - {signal_type} 信号 - {datetime.now().strftime("%Y-%m-%d %H:%M")}', fontsize=14)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 成交量图 - 绿涨红跌
            colors = ['green' if closes[i] >= chart_klines[i]['open'] else 'red' for i in range(len(chart_klines))]
            ax2.bar(x_range, volumes, color=colors, alpha=0.7)
            
            # 连接BC点对应的成交量柱状图顶点
            if signal_type in ['double_top', 'double_bottom']:
                self._mark_volume_connection(ax2, symbol, signal_type, all_klines, chart_klines, volumes)
            
            ax2.set_title('成交量')
            ax2.grid(True, alpha=0.3)
            
            # MACD图 - 确保x轴对齐
            if len(macd_line) > 0:
                macd_start = max(0, chart_len - len(macd_line))
                macd_x = range(macd_start, macd_start + len(macd_line))
                ax3.plot(macd_x, macd_line, 'blue', label='MACD', linewidth=1.5)
            
            if len(signal_line) > 0:
                signal_start = max(0, chart_len - len(signal_line))
                signal_x = range(signal_start, signal_start + len(signal_line))
                ax3.plot(signal_x, signal_line, 'red', label='Signal', linewidth=1.5)
            
            if len(histogram) > 0:
                hist_start = max(0, chart_len - len(histogram))
                hist_x = range(hist_start, hist_start + len(histogram))
                ax3.bar(hist_x, histogram, color=['green' if x >= 0 else 'red' for x in histogram], 
                       alpha=0.7, label='Histogram')
            
            # 连接BC点对应的MACD柱状图顶点
            if signal_type in ['double_top', 'double_bottom']:
                self._mark_macd_connection(ax3, symbol, signal_type, all_klines, chart_klines, histogram, hist_start if len(histogram) > 0 else 0)
            
            ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax3.set_title('MACD')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # RSI图 - 确保x轴对齐
            if len(rsi_values) > 0:
                rsi_start = max(0, chart_len - len(rsi_values))
                rsi_x = range(rsi_start, rsi_start + len(rsi_values))
                ax4.plot(rsi_x, rsi_values, 'purple', label='RSI', linewidth=1.5)
            
            # 连接BC点对应的RSI点
            if signal_type in ['double_top', 'double_bottom']:
                self._mark_rsi_connection(ax4, symbol, signal_type, all_klines, chart_klines, rsi_values, rsi_start if len(rsi_values) > 0 else 0)
            
            ax4.axhline(y=70, color='red', linestyle='--', alpha=0.7, label='超买')
            ax4.axhline(y=30, color='green', linestyle='--', alpha=0.7, label='超卖')
            ax4.axhline(y=50, color='black', linestyle='-', alpha=0.3)
            ax4.set_ylim(0, 100)
            ax4.set_title('RSI')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            
            # 保存图表
            if not os.path.exists(Config.CHART_DIR):
                os.makedirs(Config.CHART_DIR)
            
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(Config.CHART_DIR, f"{symbol}_{signal_type}_{timestamp_str}.png")
            plt.tight_layout()
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"图表已生成: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"{symbol} 生成图表失败: {str(e)}")
            return ""
    
    def _mark_pattern_points(self, ax, symbol: str, signal_type: str, all_klines: List, chart_klines: List):
        """标记双顶/双底的关键点ABC并连接相关点"""
        try:
            # 获取缓存中的关键点数据
            B_top = self.data_cache[symbol].get('B_top')
            B_bottom = self.data_cache[symbol].get('B_bottom')
            B_top_index = self.data_cache[symbol].get('B_top_index')
            B_bottom_index = self.data_cache[symbol].get('B_bottom_index')
            C_top = self.data_cache[symbol].get('C_top')
            C_bottom = self.data_cache[symbol].get('C_bottom')
            C_top_index = self.data_cache[symbol].get('C_top_index')
            C_bottom_index = self.data_cache[symbol].get('C_bottom_index')
            A_top = self.data_cache[symbol].get('A_top')
            A_bottom = self.data_cache[symbol].get('A_bottom')
            A_top_index = self.data_cache[symbol].get('A_top_index')
            A_bottom_index = self.data_cache[symbol].get('A_bottom_index')
            
            # 计算在55根K线图表中的相对位置
            all_klines_len = len(all_klines)
            chart_start_index = all_klines_len - 55  # 图表开始的索引位置
            
            if signal_type == 'double_top':
                # 标记A点（红色）
                if A_top and A_top_index is not None and A_top_index >= chart_start_index:
                    a_chart_pos = A_top_index - chart_start_index
                    ax.scatter(a_chart_pos, A_top, color='red', s=100, marker='o', zorder=5)
                    ax.annotate('A', (a_chart_pos, A_top), xytext=(5, 10), 
                               textcoords='offset points', fontsize=12, color='red', weight='bold')
                
                # 标记B点（蓝色）- 最新收盘K线的最高点
                if B_top and B_top_index is not None and B_top_index >= chart_start_index:
                    b_chart_pos = B_top_index - chart_start_index
                    ax.scatter(b_chart_pos, B_top, color='blue', s=100, marker='o', zorder=5)
                    ax.annotate('B', (b_chart_pos, B_top), xytext=(5, 10), 
                               textcoords='offset points', fontsize=12, color='blue', weight='bold')
                
                # 标记C点（绿色）- A_top与B_top之间的最低点
                if C_bottom and C_bottom_index is not None and C_bottom_index >= chart_start_index:
                    c_chart_pos = C_bottom_index - chart_start_index
                    ax.scatter(c_chart_pos, C_bottom, color='green', s=100, marker='o', zorder=5)
                    ax.annotate('C', (c_chart_pos, C_bottom), xytext=(5, -15), 
                               textcoords='offset points', fontsize=12, color='green', weight='bold')
                    
                    # 连接C_bottom和B_top两个点
                    if B_top and B_top_index is not None and B_top_index >= chart_start_index:
                        b_chart_pos = B_top_index - chart_start_index
                        ax.plot([c_chart_pos, b_chart_pos], [C_bottom, B_top], 
                               color='orange', linewidth=2, linestyle='-', alpha=0.8, label='C-B连线')
                
                # 画双顶参考线
                if A_top:
                    ax.axhline(y=A_top, color='red', linestyle='--', alpha=0.5, label='双顶线')
            
            elif signal_type == 'double_bottom':
                # 标记A点（红色）
                if A_bottom and A_bottom_index is not None and A_bottom_index >= chart_start_index:
                    a_chart_pos = A_bottom_index - chart_start_index
                    ax.scatter(a_chart_pos, A_bottom, color='red', s=100, marker='o', zorder=5)
                    ax.annotate('A', (a_chart_pos, A_bottom), xytext=(5, -15), 
                               textcoords='offset points', fontsize=12, color='red', weight='bold')
                
                # 标记B点（蓝色）- 最新收盘K线的最低点
                if B_bottom and B_bottom_index is not None and B_bottom_index >= chart_start_index:
                    b_chart_pos = B_bottom_index - chart_start_index
                    ax.scatter(b_chart_pos, B_bottom, color='blue', s=100, marker='o', zorder=5)
                    ax.annotate('B', (b_chart_pos, B_bottom), xytext=(5, -15), 
                               textcoords='offset points', fontsize=12, color='blue', weight='bold')
                
                # 标记C点（绿色）- A_bottom与B_bottom之间的最高点
                if C_top and C_top_index is not None and C_top_index >= chart_start_index:
                    c_chart_pos = C_top_index - chart_start_index
                    ax.scatter(c_chart_pos, C_top, color='green', s=100, marker='o', zorder=5)
                    ax.annotate('C', (c_chart_pos, C_top), xytext=(5, 10), 
                               textcoords='offset points', fontsize=12, color='green', weight='bold')
                    
                    # 连接C_top和B_bottom两个点
                    if B_bottom and B_bottom_index is not None and B_bottom_index >= chart_start_index:
                        b_chart_pos = B_bottom_index - chart_start_index
                        ax.plot([c_chart_pos, b_chart_pos], [C_top, B_bottom], 
                               color='orange', linewidth=2, linestyle='-', alpha=0.8, label='C-B连线')
                
                # 画双底参考线
                if A_bottom:
                    ax.axhline(y=A_bottom, color='green', linestyle='--', alpha=0.5, label='双底线')
                
        except Exception as e:
            self.logger.error(f"标记关键点失败: {str(e)}")
    
    def _mark_volume_connection(self, ax, symbol: str, signal_type: str, all_klines: List, chart_klines: List, volumes: List):
        """连接BC点对应的成交量柱状图顶点"""
        try:
            # 获取BC点的索引
            B_top_index = self.data_cache[symbol].get('B_top_index')
            B_bottom_index = self.data_cache[symbol].get('B_bottom_index')
            C_top_index = self.data_cache[symbol].get('C_top_index')
            C_bottom_index = self.data_cache[symbol].get('C_bottom_index')
            
            # 计算在55根K线图表中的相对位置
            all_klines_len = len(all_klines)
            chart_start_index = all_klines_len - 55
            
            if signal_type == 'double_top':
                # 双顶：连接C_bottom和B_top对应的成交量
                if (B_top_index is not None and C_bottom_index is not None and 
                    B_top_index >= chart_start_index and C_bottom_index >= chart_start_index):
                    b_chart_pos = B_top_index - chart_start_index
                    c_chart_pos = C_bottom_index - chart_start_index
                    if 0 <= b_chart_pos < len(volumes) and 0 <= c_chart_pos < len(volumes):
                        ax.plot([c_chart_pos, b_chart_pos], [volumes[c_chart_pos], volumes[b_chart_pos]], 
                               color='orange', linewidth=2, linestyle='-', alpha=0.8, label='C-B成交量连线')
            
            elif signal_type == 'double_bottom':
                # 双底：连接C_top和B_bottom对应的成交量
                if (B_bottom_index is not None and C_top_index is not None and 
                    B_bottom_index >= chart_start_index and C_top_index >= chart_start_index):
                    b_chart_pos = B_bottom_index - chart_start_index
                    c_chart_pos = C_top_index - chart_start_index
                    if 0 <= b_chart_pos < len(volumes) and 0 <= c_chart_pos < len(volumes):
                        ax.plot([c_chart_pos, b_chart_pos], [volumes[c_chart_pos], volumes[b_chart_pos]], 
                               color='orange', linewidth=2, linestyle='-', alpha=0.8, label='C-B成交量连线')
                        
        except Exception as e:
            self.logger.error(f"连接成交量点失败: {str(e)}")
    
    def _mark_macd_connection(self, ax, symbol: str, signal_type: str, all_klines: List, chart_klines: List, histogram: List, hist_start: int):
        """连接BC点对应的MACD柱状图顶点"""
        try:
            # 获取BC点的索引
            B_top_index = self.data_cache[symbol].get('B_top_index')
            B_bottom_index = self.data_cache[symbol].get('B_bottom_index')
            C_top_index = self.data_cache[symbol].get('C_top_index')
            C_bottom_index = self.data_cache[symbol].get('C_bottom_index')
            
            # 计算在55根K线图表中的相对位置
            all_klines_len = len(all_klines)
            chart_start_index = all_klines_len - 55
            
            if len(histogram) == 0:
                return
            
            if signal_type == 'double_top':
                # 双顶：连接C_bottom和B_top对应的MACD柱状图
                if (B_top_index is not None and C_bottom_index is not None and 
                    B_top_index >= chart_start_index and C_bottom_index >= chart_start_index):
                    b_chart_pos = B_top_index - chart_start_index
                    c_chart_pos = C_bottom_index - chart_start_index
                    
                    # 转换为MACD数据的索引
                    b_macd_pos = b_chart_pos - hist_start
                    c_macd_pos = c_chart_pos - hist_start
                    
                    if 0 <= b_macd_pos < len(histogram) and 0 <= c_macd_pos < len(histogram):
                        ax.plot([c_chart_pos, b_chart_pos], [histogram[c_macd_pos], histogram[b_macd_pos]], 
                               color='orange', linewidth=2, linestyle='-', alpha=0.8, label='C-B MACD连线')
            
            elif signal_type == 'double_bottom':
                # 双底：连接C_top和B_bottom对应的MACD柱状图
                if (B_bottom_index is not None and C_top_index is not None and 
                    B_bottom_index >= chart_start_index and C_top_index >= chart_start_index):
                    b_chart_pos = B_bottom_index - chart_start_index
                    c_chart_pos = C_top_index - chart_start_index
                    
                    # 转换为MACD数据的索引
                    b_macd_pos = b_chart_pos - hist_start
                    c_macd_pos = c_chart_pos - hist_start
                    
                    if 0 <= b_macd_pos < len(histogram) and 0 <= c_macd_pos < len(histogram):
                        ax.plot([c_chart_pos, b_chart_pos], [histogram[c_macd_pos], histogram[b_macd_pos]], 
                               color='orange', linewidth=2, linestyle='-', alpha=0.8, label='C-B MACD连线')
                        
        except Exception as e:
            self.logger.error(f"连接MACD点失败: {str(e)}")
    
    def _mark_rsi_connection(self, ax, symbol: str, signal_type: str, all_klines: List, chart_klines: List, rsi_values: List, rsi_start: int):
        """连接BC点对应的RSI点"""
        try:
            # 获取BC点的索引
            B_top_index = self.data_cache[symbol].get('B_top_index')
            B_bottom_index = self.data_cache[symbol].get('B_bottom_index')
            C_top_index = self.data_cache[symbol].get('C_top_index')
            C_bottom_index = self.data_cache[symbol].get('C_bottom_index')
            
            # 计算在55根K线图表中的相对位置
            all_klines_len = len(all_klines)
            chart_start_index = all_klines_len - 55
            
            if len(rsi_values) == 0:
                return
            
            if signal_type == 'double_top':
                # 双顶：连接C_bottom和B_top对应的RSI
                if (B_top_index is not None and C_bottom_index is not None and 
                    B_top_index >= chart_start_index and C_bottom_index >= chart_start_index):
                    b_chart_pos = B_top_index - chart_start_index
                    c_chart_pos = C_bottom_index - chart_start_index
                    
                    # 转换为RSI数据的索引
                    b_rsi_pos = b_chart_pos - rsi_start
                    c_rsi_pos = c_chart_pos - rsi_start
                    
                    if 0 <= b_rsi_pos < len(rsi_values) and 0 <= c_rsi_pos < len(rsi_values):
                        ax.plot([c_chart_pos, b_chart_pos], [rsi_values[c_rsi_pos], rsi_values[b_rsi_pos]], 
                               color='orange', linewidth=2, linestyle='-', alpha=0.8, label='C-B RSI连线')
            
            elif signal_type == 'double_bottom':
                # 双底：连接C_top和B_bottom对应的RSI
                if (B_bottom_index is not None and C_top_index is not None and 
                    B_bottom_index >= chart_start_index and C_top_index >= chart_start_index):
                    b_chart_pos = B_bottom_index - chart_start_index
                    c_chart_pos = C_top_index - chart_start_index
                    
                    # 转换为RSI数据的索引
                    b_rsi_pos = b_chart_pos - rsi_start
                    c_rsi_pos = c_chart_pos - rsi_start
                    
                    if 0 <= b_rsi_pos < len(rsi_values) and 0 <= c_rsi_pos < len(rsi_values):
                        ax.plot([c_chart_pos, b_chart_pos], [rsi_values[c_rsi_pos], rsi_values[b_rsi_pos]], 
                               color='orange', linewidth=2, linestyle='-', alpha=0.8, label='C-B RSI连线')
                        
        except Exception as e:
            self.logger.error(f"连接RSI点失败: {str(e)}")
    
    def get_signal_summary(self, symbol: str = None) -> Dict:
        """获取信号汇总"""
        if symbol:
            return self.signals.get(symbol, [])
        return self.signals
    
    def save_signals_to_file(self):
        """保存信号数据到文件"""
        try:
            if not os.path.exists(Config.DATA_DIR):
                os.makedirs(Config.DATA_DIR)
            
            filename = os.path.join(Config.DATA_DIR, f"signals_{datetime.now().strftime('%Y%m%d')}.json")
            
            # 准备保存的数据
            save_data = {
                'last_update': datetime.now().isoformat(),
                'signals': self.signals
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"信号数据已保存到: {filename}")
            
        except Exception as e:
            self.logger.error(f"保存信号数据失败: {str(e)}")

# 主程序入口
if __name__ == "__main__":
    # 设置日志系统
    logger = setup_logging()
    logger.info("=" * 50)
    logger.info("K线信号实时监控系统启动")
    logger.info("=" * 50)
    
    try:
        # 创建监控实例
        symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
            'DOGEUSDT', 'ADAUSDT', 'TRXUSDT', 'AVAXUSDT', 'TONUSDT',
            'LINKUSDT', 'DOTUSDT', 'POLUSDT', 'ICPUSDT', 'NEARUSDT',
            'UNIUSDT', 'LTCUSDT', 'APTUSDT', 'FILUSDT', 'ETCUSDT',
            'ATOMUSDT', 'HBARUSDT', 'BCHUSDT', 'INJUSDT', 'SUIUSDT',
            'ARBUSDT', 'OPUSDT', 'FTMUSDT', 'IMXUSDT', 'STRKUSDT',
            'MANAUSDT', 'VETUSDT', 'ALGOUSDT', 'GRTUSDT', 'SANDUSDT',
            'AXSUSDT', 'FLOWUSDT', 'THETAUSDT', 'CHZUSDT', 'APEUSDT',
            'MKRUSDT', 'AAVEUSDT', 'SNXUSDT', 'QNTUSDT',
            'GALAUSDT', 'ROSEUSDT', 'KLAYUSDT', 'ENJUSDT', 'RUNEUSDT',
            'WIFUSDT', 'BONKUSDT', 'FLOKIUSDT', 'NOTUSDT',
            'PEOPLEUSDT', 'JUPUSDT', 'WLDUSDT', 'ORDIUSDT', 'SEIUSDT',
            'TIAUSDT', 'RENDERUSDT', 'FETUSDT', 'ARKMUSDT',
            'PENGUUSDT', 'PNUTUSDT', 'ACTUSDT', 'NEIROUSDT',
            'RAYUSDT', 'BOMEUSDT', 'MEMEUSDT', 'MOVEUSDT',
            'EIGENUSDT', 'DYDXUSDT', 'TURBOUSDT', 'PYTHUSDT', 'JASMYUSDT',
            'COMPUSDT', 'CRVUSDT', 'LRCUSDT', 'SUSHIUSDT', 'YGGUSDT',
            'CAKEUSDT', 'OGUSDT', 'STORJUSDT', 'KNCUSDT', 'YFIUSDT',
            'ZRXUSDT', 'XLMUSDT', 'XMRUSDT', 'XTZUSDT', 'BAKEUSDT',
            'ONDOUSDT', 'NMRUSDT', 'BBUSDT', 'ZECUSDT'
        ]
        
        # 初始化监控器
        monitor = KlineMonitor(symbols)
        
        print("K线信号实时监控系统启动中...")
        print("=" * 50)
        print("监控的交易对:", ", ".join(symbols))
        print("监控信号类型:")
        print("  1. 双顶形态 (double_top)")
        print("  2. 双底形态 (double_bottom)")
        print("  3. EMA上升趋势 (uptrend)")
        print("  4. EMA下降趋势 (downtrend)")
        print("=" * 50)
        print("系统将在每小时整点进行检测...")
        print("按 Ctrl+C 停止监控")
        print("=" * 50)
        
        # 启动监控
        try:
            monitor.run()
        except KeyboardInterrupt:
            print("\n程序被用户中断")
            # 发送系统停止通知
            if monitor.telegram_bot:
                try:
                    monitor.telegram_bot.send_system_status("stopped", "系统被用户手动停止")
                    print("系统停止通知已发送")
                except Exception as e:
                    print(f"发送停止通知失败: {str(e)}")
            monitor.save_signals_to_file()
            print("信号数据已保存，程序退出")
        except Exception as e:
            print(f"程序运行出错: {e}")
            # 发送系统错误通知
            if monitor.telegram_bot:
                try:
                    monitor.telegram_bot.send_system_status("error", f"系统运行出错: {str(e)}")
                    print("系统错误通知已发送")
                except Exception as te:
                    print(f"发送错误通知失败: {str(te)}")
            monitor.save_signals_to_file()
            print("信号数据已保存")
            
    except Exception as e:
        logger.error(f"系统启动失败: {str(e)}")
        print(f"系统启动失败: {str(e)}")
