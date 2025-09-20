# K线信号实时监控系统

基于EMA双顶双底形态的加密货币K线信号实时监控系统，支持OKX交易所API和Telegram通知。

## 功能特性

- 🔍 **实时监控**: 支持多个交易对的实时K线数据监控
- 📊 **技术指标**: EMA、ATR、RSI、MACD等多种技术指标计算
- 🎯 **信号识别**: 基于EMA双顶双底形态的智能信号识别
- 📱 **Telegram通知**: 实时信号推送和系统状态通知
- 📈 **图表生成**: 自动生成包含技术指标的K线图表
- 🔄 **异常处理**: 完善的错误处理和自动重试机制
- 📝 **日志系统**: 详细的日志记录和调试信息

## 安装配置

### 1. 环境要求

- Python 3.8+
- 依赖包见 `requirements.txt`

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填入相应配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入以下配置：

- **OKX API配置**: 在OKX交易所申请API密钥
- **Telegram配置**: 创建Telegram Bot并获取Token和Chat ID
- **监控参数**: 设置要监控的交易对和技术指标参数

### 4. 目录结构

```
ema_double_t_b/
├── app.py              # 主程序
├── config.py           # 配置管理
├── telegram_bot.py     # Telegram Bot功能
├── requirements.txt    # 依赖包
├── .env.example       # 环境变量示例
├── README.md          # 说明文档
├── charts/            # 图表输出目录
├── data/              # 数据存储目录
└── logs/              # 日志文件目录
```

## 使用方法

### 启动监控

```bash
python app.py
```

### 主要功能

1. **实时监控**: 系统会按设定间隔获取K线数据并分析
2. **信号识别**: 当检测到EMA双顶双底形态时自动生成信号
3. **图表生成**: 为每个信号生成包含技术指标的K线图表
4. **Telegram通知**: 实时推送信号和系统状态到Telegram

### 信号类型

- **双顶信号**: 价格在EMA阻力位形成双顶形态，可能下跌
- **双底信号**: 价格在EMA支撑位形成双底形态，可能上涨

## 技术指标说明

### EMA (指数移动平均线)
- EMA21: 短期趋势
- EMA55: 中期趋势  
- EMA200: 长期趋势

### ATR (平均真实波幅)
- 用于衡量价格波动性
- 帮助确定止损位置

### RSI (相对强弱指数)
- 范围: 0-100
- >70: 超买区域
- <30: 超卖区域

### MACD (指数平滑移动平均线)
- MACD线: 快线EMA - 慢线EMA
- 信号线: MACD线的EMA
- 柱状图: MACD线 - 信号线

## 配置参数

### 监控配置
- `SYMBOLS`: 监控的交易对列表
- `TIMEFRAME`: K线时间周期
- `UPDATE_INTERVAL`: 更新间隔(秒)

### 技术指标参数
- `EMA_PERIODS`: EMA周期参数
- `ATR_PERIOD`: ATR计算周期
- `RSI_PERIOD`: RSI计算周期
- `MACD_FAST/SLOW/SIGNAL`: MACD参数

### 系统配置
- `LOG_LEVEL`: 日志级别
- `CHART_WIDTH/HEIGHT`: 图表尺寸
- `FILE_RETENTION_DAYS`: 文件保留天数

## 日志系统

系统提供三级日志记录：

1. **详细日志**: `logs/kline_monitor_YYYYMMDD.log`
2. **控制台输出**: 重要信息实时显示
3. **错误日志**: `logs/errors_YYYYMMDD.log`

## 异常处理

- **网络异常**: 自动重试机制，最多重试3次
- **API限制**: 智能延时和错误处理
- **数据异常**: 数据验证和清洗
- **系统异常**: 完整的错误日志和恢复机制

## 注意事项

1. **API限制**: 注意OKX API的调用频率限制
2. **网络稳定**: 确保网络连接稳定，避免频繁断线
3. **资源占用**: 监控多个交易对时注意系统资源占用
4. **数据备份**: 重要信号数据会自动保存到文件

## 故障排除

### 常见问题

1. **API连接失败**
   - 检查API密钥配置
   - 确认网络连接正常
   - 查看错误日志详情

2. **Telegram通知失败**
   - 检查Bot Token和Chat ID
   - 确认Bot已添加到对应群组
   - 检查网络连接

3. **图表生成失败**
   - 检查matplotlib依赖
   - 确认charts目录权限
   - 查看详细错误日志

### 日志查看

```bash
# 查看实时日志
tail -f logs/kline_monitor_$(date +%Y%m%d).log

# 查看错误日志
tail -f logs/errors_$(date +%Y%m%d).log
```

## 版本历史

- **v2.0**: 完整重构，添加配置管理、Telegram Bot、异常处理
- **v1.0**: 基础K线监控和信号识别功能

## 许可证

本项目仅供学习和研究使用，请勿用于实际交易决策。