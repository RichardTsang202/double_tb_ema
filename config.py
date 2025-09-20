"""
配置文件 - 管理API密钥和系统配置
"""

import os
from typing import List, Dict

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

# 环境变量配置示例（可以创建 .env 文件）
ENV_TEMPLATE = """
# Binance API配置
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key

# OKX API配置
OKX_API_KEY=your_okx_api_key
OKX_SECRET_KEY=your_okx_secret_key
OKX_PASSPHRASE=your_okx_passphrase

# Telegram配置
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL_ID=your_telegram_channel_id
"""

if __name__ == "__main__":
    # 测试配置
    print("配置验证结果:", Config.validate_config())
    print("监控交易对:", Config.SYMBOLS)
    print("币安交易对映射:", Config.get_symbol_mapping("binance"))
    print("OKX交易对映射:", Config.get_symbol_mapping("okx"))
    
    # 创建目录
    Config.create_directories()