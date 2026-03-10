# -*- coding: utf-8 -*-
"""
股票组合模拟交易 - Python Web版（带同花顺实时行情）
"""
from flask import Flask, render_template_string, request, jsonify, send_file
import json
from datetime import datetime, timedelta
import os
import sys
import threading
import time
import pandas as pd

# Excel文件路径 - WSL环境路径
STOCK_INFO_FILE = '/home/openclaw/.openclaw/workspace/实时监控！/全部A股.xlsx'

# 同花顺接口 - WSL环境路径
ifind_path = '/home/openclaw/.openclaw/workspace/bin64'
print(f"尝试加载同花顺接口，路径: {ifind_path}")
print(f"路径是否存在: {os.path.exists(ifind_path)}")

sys.path.insert(0, ifind_path)
try:
    from iFinDPy import *
    HAS_IFIND = True
    print("同花顺接口已加载成功")
except ImportError as e:
    HAS_IFIND = False
    print(f"同花顺接口导入失败 - ImportError: {e}")
except Exception as e:
    HAS_IFIND = False
    print(f"同花顺接口加载失败 - 其他错误: {e}")

app = Flask(__name__)

# 配置文件
DATA_FILE = '/home/openclaw/.openclaw/workspace/实时监控！/portfolio_data.json'
IFIND_USER = 'tpy1539'
IFIND_PASS = 'Z07510751c'

# 汇率
HKD_CNY_RATE = 0.92

# 线程锁
price_lock = threading.Lock()

# 简单的价格缓存（运行时动态填充，不预置数据）
CLOSE_PRICES = {}

# 投资组合数据
portfolio = {
    'initialCash': 0,
    'cash': 0,
    'positions': [],
    'trades': [],
    'netValue': 1.0,
    'previousNetValue': 1.0,
    'peakNetValue': 1.0  # 净值最高点
}

def load_portfolio():
    global portfolio
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                portfolio = json.load(f)
        except:
            pass

def save_portfolio():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)

def get_stock_name_from_excel(code):
    """从Excel文件获取股票名称"""
    try:
        if os.path.exists(STOCK_INFO_FILE):
            # 读取Excel文件
            df = pd.read_excel(STOCK_INFO_FILE)
            
            # Excel列名是固定的：'证券代码', '证券简称'
            if '证券代码' in df.columns and '证券简称' in df.columns:
                # 首先尝试完整代码匹配
                stock_info = df[df['证券代码'].astype(str) == code]
                if not stock_info.empty:
                    name = stock_info['证券简称'].iloc[0]
                    return name
                
                # 如果没找到，尝试添加交易所后缀
                if '.' not in code:
                    # 根据代码开头数字判断交易所
                    if code.startswith('6') or code.startswith('5'):
                        full_code = code + '.SH'
                    elif code.startswith('00') or code.startswith('30'):
                        full_code = code + '.SZ'
                    elif code.startswith('8') or code.startswith('4'):
                        full_code = code + '.BJ'
                    else:
                        full_code = code
                    
                    stock_info = df[df['证券代码'].astype(str) == full_code]
                    if not stock_info.empty:
                        name = stock_info['证券简称'].iloc[0]
                        return name
                
                # 最后尝试模糊匹配（去掉后缀）
                if '.' in code:
                    base_code = code.split('.')[0]
                    stock_info = df[df['证券代码'].astype(str).str.startswith(base_code + '.', na=False)]
                    if not stock_info.empty:
                        name = stock_info['证券简称'].iloc[0]
                        return name
            else:
                print(f"Excel列名不匹配: {list(df.columns)}")
        else:
            print("Excel文件不存在")
                    
    except Exception as e:
        print(f"读取Excel文件失败: {e}")
    
    return None

def calculate_net_value_drawdown():
    """
    计算净值回撤幅度
    从组合净值最高点到当前低点的累计下跌幅度，每次创新高后重新计算
    返回: 回撤幅度（负数百分比，如 -6% 返回 -6.0）
    """
    if portfolio.get('initialCash', 0) <= 0:
        return 0.0
    
    # 获取历史净值的最高点
    peak_net_value = portfolio.get('peakNetValue', portfolio.get('netValue', 1.0))
    current_net_value = portfolio.get('netValue', 1.0)
    
    # 如果当前净值创新高，更新峰值
    if current_net_value > peak_net_value:
        portfolio['peakNetValue'] = current_net_value
        portfolio['peakNetValueDate'] = datetime.now().strftime('%Y-%m-%d')
        peak_net_value = current_net_value
        # 创新高后回撤归零
        return 0.0
    
    # 计算回撤幅度 (最高点到当前点的下跌)
    if peak_net_value > 0:
        drawdown = (current_net_value - peak_net_value) / peak_net_value * 100
        return round(drawdown, 2)
    
    return 0.0

def calculate_position_control(asset_growth, net_value_drawdown):
    """
    计算仓位控制
    规则:
    1. 资产增长<=5% 或 净值回撤幅度<=-6%时，持仓占比只能40%（或关系，满足任一即执行）
    2. (资产增长幅度*3+40%)>100% 并且 净值回撤幅度>-2%时，持仓占比可以达到100%（不受约束）
    3. 其他情况：持仓占比 = min((资产增长幅度*3+40%), ((净值回撤幅度+2%)*15+100%))
    
    参数:
        asset_growth: 资产增长百分比（如 10 表示 10%）
        net_value_drawdown: 净值回撤幅度负数百分比（如 -6 表示 -6%）
    
    返回: 允许的最大持仓占比
    """
    # 条件①：资产增长<=5% 或 净值回撤幅度<=-6%时，持仓占比只能40%
    if asset_growth <= 5 or net_value_drawdown <= -6:
        return 40.0
    
    # 条件②：(资产增长幅度*3+40%)>100% 并且 净值回撤幅度>-2%时，持仓占比可以达到100%
    if (asset_growth * 3 + 40) > 100 and net_value_drawdown > -2:
        return 100.0
    
    # 条件③：其他情况，取最小值
    # min((资产增长幅度*3+40%), ((净值回撤幅度+2%)*15+100%))
    position_from_growth = asset_growth * 3 + 40
    position_from_drawdown = (net_value_drawdown + 2) * 15 + 100
    
    max_position = min(position_from_growth, position_from_drawdown)
    
    # 确保在有效范围内
    max_position = max(0, min(100, max_position))
    
    return round(max_position, 1)

def calculate_position_value(pos):
    """计算持仓市值"""
    code = pos['code']
    close_info = CLOSE_PRICES.get(code, {})
    current_price = close_info.get('price', pos.get('buyPrice', 0))
    
    market = pos.get('market', 'A股')
    
    # 如果本地价格为空或为0，尝试刷新价格
    if current_price == 0:
        if HAS_IFIND:
            try:
                THS_iFinDLogin(IFIND_USER, IFIND_PASS)
                from datetime import datetime, timedelta
                current_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                result = THS_HQ(code, 'preclose,high,low,last,thsname,close', '', start_date, current_date, 'format:dataframe')
                if result and result.errorcode == 0 and result.data is not None and len(result.data) > 0:
                    df = result.data
                    if hasattr(df, 'iloc'):
                        latest = df.iloc[-1]
                        # 优先使用收盘价close
                    if 'close' in latest.index and pd.notna(latest.get('close')) and latest.get('close') != 0:
                        current_price = float(latest.get('close', 0))
                    else:
                        current_price = 0
                        # 更新本地缓存
                        name = close_info.get('name', code)
                        CLOSE_PRICES[code] = {'price': current_price, 'name': name, 'market': market}
            except Exception as e:
                print(f"同花顺刷新持仓价格失败 {code}: {e}")
        else:
            # 如果没有同花顺接口，使用买入价格
            current_price = pos.get('buyPrice', 0)
    
    if market == '港股':
        market_value = pos['shares'] * current_price * HKD_CNY_RATE
        # 实际买入成本 = 实际买入股数 * 买入价格 * 汇率
        buy_amount_cny = pos['shares'] * pos['buyPrice'] * HKD_CNY_RATE
    else:
        market_value = pos['shares'] * current_price
        # 实际买入成本 = 实际买入股数 * 买入价格
        buy_amount_cny = pos['shares'] * pos['buyPrice']
    
    # 变动 = 当前市值 - 实际买入成本
    change = market_value - buy_amount_cny
    
    return {
        'marketValue': market_value,
        'buyAmountCNY': buy_amount_cny,
        'currentPrice': current_price,
        'change': change,
    }

def update_summary():
    """计算汇总数据"""
    total_stock_value = 0
    total_change = 0
    
    position_details = []
    
    for pos in portfolio.get('positions', []):
        detail = calculate_position_value(pos)
        
        change_pct = (detail['change'] / detail['buyAmountCNY'] * 100) if detail['buyAmountCNY'] > 0 else 0
        contribution = (detail['change'] / portfolio['initialCash'] * 100) if portfolio['initialCash'] > 0 else 0
        # 单个股票的持仓比例计算放在总资产计算后（需要先知道total_assets）
        
        position_details.append({
            'code': pos['code'],
            'name': pos['name'],
            'market': pos['market'],
            'shares': pos['shares'],
            'buyPrice': pos['buyPrice'],
            'currentPrice': detail['currentPrice'],
            'marketValue': detail['marketValue'],
            'change': detail['change'],
            'changePct': change_pct,
            'contribution': contribution,
            'positionRatio': 0  # 先设为0，后面计算总资产后再更新
        })
        
        total_stock_value += detail['marketValue']
        total_change += detail['change']
    
    total_assets = total_stock_value + portfolio['cash']
    
    # 现在计算每个股票的正确持仓比例
    for detail in position_details:
        detail['positionRatio'] = (detail['marketValue'] / total_assets * 100) if total_assets > 0 else 0
    
    # 资产变动 = 总资产 - 初始资金
    asset_change = total_assets - portfolio['initialCash']
    
    # 资产增长 = (总资产 - 初始资金) / 初始资金 * 100%
    asset_growth = (asset_change / portfolio['initialCash'] * 100) if portfolio['initialCash'] > 0 else 0
    
    # 持仓占比 = 股票市值 / 总资产
    position_ratio_total = (total_stock_value / total_assets * 100) if total_assets > 0 else 0
    
    # 现金占比 = 现金 / 总资产
    cash_ratio = (portfolio['cash'] / total_assets * 100) if total_assets > 0 else 0
    
    # 组合净值 = 总资产 / 初始资金
    portfolio['netValue'] = total_assets / portfolio['initialCash'] if portfolio['initialCash'] > 0 else 1.0
    
    # 计算净值回撤幅度
    net_value_drawdown = calculate_net_value_drawdown()
    
    # 计算仓位控制
    position_control = calculate_position_control(asset_growth, net_value_drawdown)
    
    return {
        'initialCash': portfolio['initialCash'],
        'totalAssets': round(total_assets),
        'assetChange': round(asset_change),
        'assetGrowth': round(asset_growth, 1),
        'netValue': round(portfolio['netValue'], 4),
        'netValueDrawdown': net_value_drawdown,
        'positionControl': position_control,
        'stockValue': round(total_stock_value),
        'positionRatio': round(position_ratio_total, 1),
        'cash': round(portfolio['cash']),
        'cashRatio': round(cash_ratio, 1),
        'positions': position_details,
        'exchangeRate': HKD_CNY_RATE
    }

# 简化HTML模板
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>股票组合模拟交易</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #fff; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 20px; color: #00d4ff; font-size: 24px; }
        .card { background: rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
        .card h2 { color: #00d4ff; margin-bottom: 16px; font-size: 16px; display: flex; align-items: center; justify-content: space-between; }
        .portfolio-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
        .summary-item { background: rgba(0,212,255,0.08); border-radius: 8px; padding: 14px; text-align: center; }
        .summary-item .label { color: #8b9dc3; font-size: 12px; margin-bottom: 6px; }
        .summary-item .value { font-size: 20px; font-weight: bold; color: #00d4ff; }
        .summary-item .value.positive { color: #00ff88; }
        .summary-item .value.negative { color: #ff4757; }
        .form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 12px; }
        .form-group { display: flex; flex-direction: column; }
        .form-group label { color: #8b9dc3; font-size: 12px; margin-bottom: 6px; }
        .form-group input, .form-group select { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; padding: 10px; color: #fff; font-size: 14px; }
        .form-group select option { background: #1a1a2e; color: #fff; }
        .form-group input:focus, .form-group select:focus { outline: none; border-color: #00d4ff; }
        .btn { background: linear-gradient(135deg, #00d4ff, #0099cc); border: none; border-radius: 6px; padding: 10px 18px; color: #fff; font-size: 14px; font-weight: bold; cursor: pointer; }
        .btn:hover { transform: translateY(-1px); }
        .btn-secondary { background: linear-gradient(135deg, #667eea, #764ba2); }
        .btn-danger { background: linear-gradient(135deg, #ff4757, #c0392b); }
        .btn-group { display: flex; gap: 10px; margin-top: 12px; }
        .tabs { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
        .tab { background: rgba(255,255,255,0.1); border: none; border-radius: 6px; padding: 10px 18px; color: #8b9dc3; cursor: pointer; font-size: 14px; }
        .tab.active { background: linear-gradient(135deg, #00d4ff, #0099cc); color: #fff; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .alert { padding: 10px 14px; border-radius: 6px; margin-bottom: 12px; font-size: 13px; }
        .alert-warning { background: rgba(255,193,7,0.15); border: 1px solid #ffc107; color: #ffc107; }
        .alert-error { background: rgba(255,71,87,0.15); border: 1px solid #ff4757; color: #ff4757; }
        .alert-success { background: rgba(0,255,136,0.15); border: 1px solid #00ff88; color: #00ff88; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { padding: 10px 8px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
        th { color: #8b9dc3; font-weight: 500; font-size: 11px; }
        .positive { color: #00ff88; }
        .negative { color: #ff4757; }
        .market-tag { display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 10px; }
        .market-tag.A股 { background: rgba(255,193,7,0.2); color: #ffc107; }
        .market-tag.港股 { background: rgba(0,212,255,0.2); color: #00d4ff; }
        .empty-state { text-align: center; padding: 30px; color: #8b9dc3; }
        .exchange-rate { font-size: 12px; color: #8b9dc3; }
        .position-hint { font-size: 14px; color: #ffc107; font-weight: bold; margin-top: 4px; }
        .summary-item .value.warning { color: #ffc107; }
        .summary-item .value.safe { color: #00ff88; }
        .alert-info { background: rgba(0,212,255,0.15); border: 1px solid #00d4ff; color: #00d4ff; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 股票组合模拟交易 - 安全垫及净值回撤体系（同花顺实时版）</h1>
        <div class="card">
            <h2><span>组合概况</span><span class="exchange-rate" id="exchangeRate">汇率: 1HKD=¥0.9200</span></h2>
            <div class="portfolio-summary">
                <div class="summary-item"><div class="label">初始资金</div><div class="value" id="initialCash">¥0</div></div>
                <div class="summary-item"><div class="label">总资产</div><div class="value" id="totalAssets">¥0</div></div>
                <div class="summary-item"><div class="label">资产变动</div><div class="value" id="assetChange">¥0</div></div>
                <div class="summary-item"><div class="label">资产增长</div><div class="value" id="assetGrowth">0.0%</div></div>
                <div class="summary-item"><div class="label">组合净值</div><div class="value" id="netValue">1.0000</div></div>
                <div class="summary-item"><div class="label">净值回撤幅度</div><div class="value" id="netValueDrawdown">0.0%</div></div>
                <div class="summary-item"><div class="label">股票市值</div><div class="value" id="stockValue">¥0</div></div>
                <div class="summary-item"><div class="label">持仓占比 <span id="positionControlHint" style="font-size:14px;color:#ffc107;font-weight:bold;">（仓位控制100%）</span></div><div class="value" id="positionRatio">0%</div></div>
                <div class="summary-item"><div class="label">现金</div><div class="value" id="cash">¥0</div></div>
                <div class="summary-item"><div class="label">现金占比</div><div class="value" id="cashRatio">0%</div></div>
            </div>
            <div id="positionControlAlert" style="margin-top:12px;"></div>
        </div>
        <div class="tabs">
            <button class="tab active" onclick="switchTab('建仓')">建仓</button>
            <button class="tab" onclick="switchTab('持仓')">持仓</button>
            <button class="tab" onclick="switchTab('卖出')">卖出</button>
            <button class="tab" onclick="switchTab('记录')">记录</button>
            <button class="tab" onclick="switchTab('导入导出')">导入导出</button>
        </div>
        <div class="tab-content active" id="tab-建仓">
            <div class="card">
                <h2>初始资金配置</h2>
                <div style="display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap;">
                    <div class="form-group" style="flex:1;min-width:150px;">
                        <label>初始资金（人民币）</label>
                        <input type="number" id="initialCashInput" value="5000000" disabled>
                    </div>
                    <button class="btn" id="btnSetup" onclick="setupInitialCash()">确认设置</button>
                    <button class="btn btn-secondary" id="btnReset" onclick="resetPortfolio()" style="display:none;">重新设置</button>
                </div>
            </div>
            <div class="card" id="addStockCard" style="display:none;">
                <h2>添加股票</h2>
                <div class="form-row">
                    <div class="form-group"><label>交易所</label>
                        <select id="exchange" onchange="updateExchange()">
                            <option value="SZ">深交所(SZ)</option>
                            <option value="SH">上交所(SH)</option>
                            <option value="BJ">北交所(BJ)</option>
                            <option value="HK">港交所(HK)</option>
                        </select>
                    </div>
                    <div class="form-group"><label>股票代码</label><input type="text" id="stockCode" placeholder="如: 300249" onblur="autoMatchName()"></div>
                    <div class="form-group"><label>公司名称</label><input type="text" id="stockName" placeholder="自动匹配"></div>
                    <div class="form-group"><label>买入时间</label><input type="date" id="buyDate"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>买入价格</label><input type="number" id="buyPrice" step="0.01"></div>
                    <div class="form-group"><label>买入占比(%)</label><input type="number" id="buyRatio" placeholder="如: 10"></div>
                    <div class="form-group"><label>&nbsp;</label><button class="btn" onclick="fetchPrice()">获取现价</button></div>
                </div>
                <div id="priceInfo" style="font-size:12px;color:#8b9dc3;margin-bottom:12px;"></div>
                <div class="btn-group">
                    <button class="btn" onclick="addStock()">确认建仓</button>
                    <button class="btn btn-secondary" onclick="addAnotherStock()">+ 继续添加</button>
                </div>
                <div id="buildAlert"></div>
            </div>
        </div>
        <div class="tab-content" id="tab-持仓">
            <div class="card">
                <h2>
                    <span>当前持仓</span>
                    <button class="btn btn-secondary" onclick="updateAllPrices()" style="font-size: 12px; padding: 8px 12px;">🔄 刷新所有价格</button>
                </h2>
                <div id="positionsAlert"></div>
                <div id="positionsTable"><div class="empty-state">暂无持仓</div></div>
            </div>
        </div>
        <div class="tab-content" id="tab-卖出">
            <div class="card">
                <h2>卖出股票</h2>
                <div class="form-row">
                    <div class="form-group"><label>选择股票</label><select id="sellStockSelect"><option value="">请选择</option></select></div>
                    <div class="form-group"><label>卖出时间</label><input type="date" id="sellDate"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>卖出方式</label>
                        <select id="sellMethod" onchange="handleSellMethodChange(); updateSellPreview()">
                            <option value="asset">按持仓比例</option>
                            <option value="all">全部卖出</option>
                        </select>
                    </div>
                    <div class="form-group"><label>持仓比例(%)</label><input type="number" id="sellRatio" placeholder="如: 5" oninput="updateSellPreview()"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>卖出价格 (<span id="sellPriceUnit">¥</span>)</label><input type="number" id="sellPrice" step="0.01" oninput="updateSellPriceChange()"></div>
                </div>
                <div id="sellPreview" style="background: rgba(0,212,255,0.08); border-radius: 6px; padding: 12px; margin-bottom: 12px; font-size: 13px; color: #8b9dc3; display: none;">
                    <div id="sellPreviewContent"></div>
                </div>
                <div class="btn-group">
                    <button class="btn btn-danger" onclick="sellStock()">确认卖出</button>
                    <button class="btn btn-secondary" onclick="quickSellAll()" style="background: linear-gradient(135deg, #ff6b6b, #ee5a24);">🔥 一键清仓</button>
                </div>
                <div id="sellAlert"></div>
            </div>
        </div>
        <div class="tab-content" id="tab-记录">
            <div class="card"><h2>交易记录</h2><div id="tradeHistory"><div class="empty-state">暂无记录</div></div></div>
        </div>
        <div class="tab-content" id="tab-导入导出">
            <div class="card">
                <h2>导出持仓</h2>
                <p style="color: #8b9dc3; margin-bottom: 16px;">导出当前持仓为Excel文件，包含股票代码、股票名称、买入价格、买入占比</p>
                <button class="btn" onclick="exportPositions()">📥 导出持仓Excel</button>
                <div id="exportAlert" style="margin-top: 12px;"></div>
            </div>
            <div class="card" style="margin-top: 16px;">
                <h2>导入建仓</h2>
                <p style="color: #8b9dc3; margin-bottom: 16px;">从Excel文件批量导入股票建仓信息。Excel格式：股票代码、买入价格、买入占比(%)</p>
                <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 16px;">
                    <input type="file" id="importFile" accept=".xlsx,.xls" style="display: none;" onchange="handleFileSelect(event)">
                    <button class="btn" onclick="document.getElementById('importFile').click()">📤 选择Excel文件</button>
                    <span id="fileName" style="color: #8b9dc3;">未选择文件</span>
                </div>
                <button class="btn" onclick="importPositions()" id="importBtn" disabled>🚀 开始导入</button>
                <div id="importAlert" style="margin-top: 12px;"></div>
            </div>
            <div class="card" style="margin-top: 16px;">
                <h2>Excel格式说明</h2>
                <div style="background: rgba(0,212,255,0.08); border-radius: 6px; padding: 16px; margin-bottom: 12px;">
                    <h4 style="color: #00d4ff; margin-bottom: 12px;">导出格式（4列）：股票代码、股票名称、买入价格、买入占比</h4>
                    <table style="font-size: 13px;">
                        <tr><th style="text-align: left; padding: 8px;">列名</th><th style="text-align: left; padding: 8px;">说明</th><th style="text-align: left; padding: 8px;">示例</th></tr>
                        <tr><td style="padding: 6px;">股票代码</td><td style="padding: 6px;">如：000001、600000、HK00700</td><td style="padding: 6px;">000001</td></tr>
                        <tr><td style="padding: 6px;">买入价格</td><td style="padding: 6px;">买入成本价</td><td style="padding: 6px;">10.50</td></tr>
                        <tr><td style="padding: 6px;">买入占比(%)</td><td style="padding: 6px;">占总资金比例</td><td style="padding: 6px;">5.0</td></tr>
                    </table>
                </div>
                <div style="background: rgba(0,255,136,0.08); border-radius: 6px; padding: 16px;">
                    <h4 style="color: #00ff88; margin-bottom: 12px;">导入格式（3列，必填）：</h4>
                    <table style="font-size: 13px;">
                        <tr><th style="text-align: left; padding: 8px;">列名</th><th style="text-align: left; padding: 8px;">说明</th><th style="text-align: left; padding: 8px;">示例</th></tr>
                        <tr><td style="padding: 6px;">股票代码</td><td style="padding: 6px;">必须带交易所后缀</td><td style="padding: 6px;">300438.SZ</td></tr>
                        <tr><td style="padding: 6px;">买入价格</td><td style="padding: 6px;">买入价格</td><td style="padding: 6px;">10.50</td></tr>
                        <tr><td style="padding: 6px;">买入占比(%)</td><td style="padding: 6px;">占总资金比例</td><td style="padding: 6px;">5.0</td></tr>
                    </table>
                    <p style="color: #ffc107; margin-top: 12px; font-size: 12px;">
                        <strong>交易所后缀说明：</strong><br>
                        • 深交所：.SZ（如：300438.SZ）<br>
                        • 上交所：.SH（如：600498.SH）<br>
                        • 北交所：.BJ（如：920001.BJ 或 910789.BJ）<br>
                        • 港交所：.HK（如：3896.HK）
                    </p>
                </div>
            </div>
        </div>
    </div>
    <script>
        const closePrices = {{ closePrices | tojson }};
        let hkdCnyRate = {{ exchangeRate }};
        let portfolio = {{ portfolio | tojson }};
        
        document.addEventListener('DOMContentLoaded', function() {
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('buyDate').value = today;
            document.getElementById('sellDate').value = today;
            if(portfolio.initialCash > 0) {
                document.getElementById('initialCashInput').value = portfolio.initialCash;
                document.getElementById('initialCashInput').disabled = true;
                document.getElementById('btnSetup').style.display = 'none';
                document.getElementById('btnReset').style.display = 'inline-block';
                document.getElementById('addStockCard').style.display = 'block';
            }
            updateSummary();
            
            // 启动自动更新
            startAutoUpdate();
            console.log('自动更新已启动 - 每1分钟更新价格，每10秒刷新汇总');
        });
        
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
            if(tab === '持仓') renderPositions();
            if(tab === '卖出') updateSellSelect();
            if(tab === '记录') renderTradeHistory();
        }
        
        // 导出持仓功能
        function exportPositions() {
            if(portfolio.positions.length === 0) {
                showAlert('exportAlert', '当前没有持仓，无法导出', 'warning');
                return;
            }
            
            fetch('/api/export/positions')
                .then(response => {
                    if(response.ok) {
                        return response.blob();
                    }
                    throw new Error('导出失败');
                })
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `持仓导出_${new Date().toISOString().split('T')[0]}.xlsx`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    showAlert('exportAlert', '✅ 持仓导出成功！', 'success');
                })
                .catch(error => {
                    console.error('导出失败:', error);
                    showAlert('exportAlert', '❌ 导出失败，请重试', 'error');
                });
        }
        
        // 处理文件选择
        function handleFileSelect(event) {
            const file = event.target.files[0];
            if(file) {
                document.getElementById('fileName').textContent = file.name;
                document.getElementById('importBtn').disabled = false;
            } else {
                document.getElementById('fileName').textContent = '未选择文件';
                document.getElementById('importBtn').disabled = true;
            }
        }
        
        // 导入持仓功能
        function importPositions() {
            const fileInput = document.getElementById('importFile');
            const file = fileInput.files[0];
            
            if(!file) {
                showAlert('importAlert', '请先选择Excel文件', 'warning');
                return;
            }
            
            if(portfolio.initialCash <= 0) {
                showAlert('importAlert', '请先设置初始资金', 'warning');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            showAlert('importAlert', '🔄 正在导入，请稍候...', 'info');
            document.getElementById('importBtn').disabled = true;
            
            fetch('/api/import/positions', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if(data.success) {
                    showAlert('importAlert', `✅ 导入成功！共导入${data.imported_count}只股票`, 'success');
                    
                    // 更新组合数据
                    portfolio = data.portfolio;
                    
                    // 保存数据
                    fetch('/api/save', {
                        method: 'POST', 
                        headers: {'Content-Type': 'application/json'}, 
                        body: JSON.stringify(portfolio)
                    });
                    
                    // 刷新界面
                    updateSummary();
                    renderPositions();
                    updateSellSelect();
                    
                    // 清空文件选择
                    fileInput.value = '';
                    document.getElementById('fileName').textContent = '未选择文件';
                    document.getElementById('importBtn').disabled = true;
                } else {
                    showAlert('importAlert', `❌ 导入失败：${data.error}`, 'error');
                }
            })
            .catch(error => {
                console.error('导入失败:', error);
                showAlert('importAlert', '❌ 导入失败，请检查文件格式', 'error');
            })
            .finally(() => {
                document.getElementById('importBtn').disabled = false;
            });
        }
        
        function setupInitialCash() {
            const cash = parseFloat(document.getElementById('initialCashInput').value);
            if(!cash || cash <= 0) return showAlert('buildAlert', '请输入有效金额', 'error');
            portfolio.initialCash = cash;
            portfolio.cash = cash;
            portfolio.positions = [];
            portfolio.trades = [];
            portfolio.netValue = 1.0;
            fetch('/api/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(portfolio)});
            document.getElementById('initialCashInput').disabled = true;
            document.getElementById('btnSetup').style.display = 'none';
            document.getElementById('btnReset').style.display = 'inline-block';
            document.getElementById('addStockCard').style.display = 'block';
            updateSummary();
            showAlert('buildAlert', '初始资金设置成功', 'success');
        }
        
        function resetPortfolio() {
            if(confirm('确定要重新设置吗？将清空所有持仓！')) {
                portfolio = { initialCash: 0, cash: 0, positions: [], trades: [], netValue: 1.0, previousNetValue: 1.0 };
                fetch('/api/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(portfolio)});
                document.getElementById('initialCashInput').disabled = false;
                document.getElementById('btnSetup').style.display = 'inline-block';
                document.getElementById('btnReset').style.display = 'none';
                document.getElementById('addStockCard').style.display = 'none';
                updateSummary();
            }
        }
        
        function updateExchange() {
            const exchange = document.getElementById('exchange').value;
            document.getElementById('sellPriceUnit').textContent = exchange === 'HK' ? 'HK$' : '¥';
        }
        
        function validateStockCode(code, exchange) {
            // 验证股票代码与交易所是否匹配
            if (!code) return true;
            
            // 去掉可能已存在的后缀
            const cleanCode = code.split('.')[0];
            
            // 根据代码开头数字判断正确的交易所
            let expectedExchange = '';
            if (cleanCode.startsWith('6') || cleanCode.startsWith('5')) {
                expectedExchange = 'SH'; // 上交所
            } else if (cleanCode.startsWith('00') || cleanCode.startsWith('30')) {
                expectedExchange = 'SZ'; // 深交所
            } else if (cleanCode.startsWith('8') || cleanCode.startsWith('4')) {
                expectedExchange = 'BJ'; // 北交所
            } else if (cleanCode.startsWith('HK')) {
                expectedExchange = 'HK'; // 港交所
            }
            
            // 如果能推断出正确交易所，且与选择的不匹配，返回错误
            if (expectedExchange && expectedExchange !== exchange) {
                const exchangeNames = {
                    'SH': '上交所(SH)',
                    'SZ': '深交所(SZ)', 
                    'BJ': '北交所(BJ)',
                    'HK': '港交所(HK)'
                };
                return {
                    valid: false,
                    expectedExchange,
                    message: `代码 ${cleanCode} 应该属于 ${exchangeNames[expectedExchange]}，当前选择的是 ${exchangeNames[exchange]}`
                };
            }
            
            return { valid: true };
        }
        
        function autoMatchName() {
            const code = document.getElementById('stockCode').value.trim();
            const exchange = document.getElementById('exchange').value;
            if(!code) return;
            
            // 验证代码与交易所是否匹配
            const validation = validateStockCode(code, exchange);
            if (!validation.valid) {
                // 显示错误信息
                document.getElementById('stockName').value = '';
                document.getElementById('buyPrice').value = '';
                document.getElementById('priceInfo').innerHTML = `<span style="color: #ff4757;">❌ ${validation.message}</span>`;
                return;
            }
            
            const fullCode = code + '.' + exchange;
            
            // 清空之前的名称和价格
            document.getElementById('stockName').value = '';
            document.getElementById('buyPrice').value = '';
            document.getElementById('priceInfo').innerHTML = '';
            
            // 优先从Excel获取股票名称
            fetch(`/api/excel-name/${fullCode}`)
                .then(response => response.json())
                .then(excelData => {
                    console.log('从Excel获取的股票信息:', excelData);
                    
                    let stockName = excelData.name;
                    if(stockName && stockName !== code && stockName !== fullCode) {
                        document.getElementById('stockName').value = stockName;
                    }
                    
                    // 无论Excel是否有名称，都尝试获取价格
                    fetchPrice();
                })
                .catch(error => {
                    console.log('从Excel获取名称失败:', error);
                    // Excel失败时直接获取价格
                    fetchPrice();
                });
        }
        
        function fetchPrice() {
            const code = document.getElementById('stockCode').value.trim();
            const exchange = document.getElementById('exchange').value;
            if(!code) return;
            const fullCode = code + '.' + exchange;
            
            // 显示加载状态
            document.getElementById('priceInfo').innerHTML = '正在获取价格...';
            
            // 优先通过API获取价格
            fetch(`/api/price/${fullCode}`)
                .then(response => response.json())
                .then(data => {
                    if(data.price && data.price > 0) {
                        const displayPrice = exchange === 'HK' ? 'HK$' + data.price.toFixed(2) : '¥' + data.price.toFixed(2);
                        document.getElementById('priceInfo').innerHTML = '当前价格: ' + displayPrice + ' (' + data.source + ')';
                        document.getElementById('buyPrice').value = data.price;
                        
                        // 获取当前已填入的股票名称（优先Excel名称）
                        const currentName = document.getElementById('stockName').value || data.name || code;
                        
                        // 更新本地缓存，使用Excel优先的名称
                        closePrices[fullCode] = {
                            price: data.price,
                            name: currentName,
                            market: data.market
                        };
                    } else {
                        document.getElementById('priceInfo').innerHTML = '未找到价格信息 (' + data.source + ')';
                    }
                })
                .catch(error => {
                    console.error('获取价格失败:', error);
                    document.getElementById('priceInfo').innerHTML = '获取价格失败，请检查网络连接';
                });
        }
        
        function addStock() {
            const exchange = document.getElementById('exchange').value;
            const code = document.getElementById('stockCode').value.trim();
            const fullCode = code + '.' + exchange;
            const name = document.getElementById('stockName').value.trim() || code;
            const date = document.getElementById('buyDate').value;
            const price = parseFloat(document.getElementById('buyPrice').value);
            const ratio = parseFloat(document.getElementById('buyRatio').value);
            
            if(!code || !date || !price || !ratio) return showAlert('buildAlert', '请填写完整', 'error');
            
            // 验证代码与交易所是否匹配
            const validation = validateStockCode(code, exchange);
            if (!validation.valid) {
                return showAlert('buildAlert', validation.message, 'error');
            }
            
            const market = exchange === 'HK' ? '港股' : 'A股';
            const plannedAmount = portfolio.initialCash * (ratio / 100);
            
            // 检查仓位控制
            fetch('/api/summary').then(r=>r.json()).then(data => {
                const used = portfolio.positions.reduce((s,p) => s + p.buyAmount, 0);
                const total = portfolio.initialCash;
                const currentRatio = total > 0 ? ((used + plannedAmount) / total * 100) : 0;
                
                if(currentRatio > data.positionControl) {
                    return showAlert('buildAlert', '建仓后仓位将超过仓位控制限制(' + data.positionControl.toFixed(1) + '%)，请降低买入比例', 'warning');
                }
                
                if(plannedAmount > portfolio.cash) {
                    return showAlert('buildAlert', '没有足够资金', 'warning');
                }
                
                // 计算可买入股数
                let shares;
                if(market === '港股') {
                    // 港股：将人民币金额换算成港币，然后按港币价格计算股数
                    const plannedAmountCNY = plannedAmount;
                    const plannedAmountHKD = plannedAmountCNY / hkdCnyRate;
                    shares = Math.floor(plannedAmountHKD / price);
                    console.log(`港股买入计划: ${plannedAmountCNY}元 ≈ ${plannedAmountHKD.toFixed(2)}港币，可买${shares}股`);
                } else {
                    // A股：直接用人民币金额计算股数
                    shares = Math.floor(plannedAmount / price);
                    console.log(`A股买入计划: ${plannedAmount}元，可买${shares}股`);
                }
                
                if(shares <= 0) return showAlert('buildAlert', '金额过低', 'error');
                
                // 计算实际成交金额
                let actualBuyAmount = shares * price;
                let actualBuyAmountCNY;
                
                if(market === '港股') {
                    // 港股：价格是港币，需要换算成人民币存储
                    actualBuyAmountCNY = actualBuyAmount * hkdCnyRate;
                    console.log(`港股买入: ${shares}股 × ${price}港币 = ${actualBuyAmount}港币 ≈ ${actualBuyAmountCNY.toFixed(2)}人民币`);
                } else {
                    // A股：直接是人民币
                    actualBuyAmountCNY = actualBuyAmount;
                    console.log(`A股买入: ${shares}股 × ${price}元 = ${actualBuyAmount}元`);
                }
                
                const canSellDate = market === 'A股' ? new Date(date) : new Date(date);
                if(market === 'A股') canSellDate.setDate(canSellDate.getDate() + 1);
                
                // 检查是否已存在相同股票的持仓
                const existingPositionIndex = portfolio.positions.findIndex(p => p.code === fullCode);
                
                if (existingPositionIndex !== -1) {
                    // 存在相同持仓，进行合并
                    const existingPos = portfolio.positions[existingPositionIndex];
                    
                    // 计算加权平均成本价
                    const totalShares = existingPos.shares + shares;
                    const totalAmount = existingPos.buyAmount + actualBuyAmountCNY;
                    const weightedAveragePrice = totalAmount / totalShares;
                    
                    // 更新持仓信息
                    portfolio.positions[existingPositionIndex] = {
                        ...existingPos,
                        shares: totalShares,
                        buyPrice: weightedAveragePrice,
                        buyAmount: totalAmount,
                        buyDate: date  // 更新为最新买入日期
                    };
                    
                    console.log(`合并持仓: ${name} - 原持仓${existingPos.shares}股成本${existingPos.buyPrice.toFixed(2)}，新增${shares}股价格${price}，合并后${totalShares}股成本${weightedAveragePrice.toFixed(2)}`);
                } else {
                    // 新增持仓
                    const position = { code: fullCode, name, market, exchange, buyDate: date, buyPrice: price, shares, buyAmount: actualBuyAmountCNY, canSellDate: canSellDate.toISOString().split('T')[0] };
                    portfolio.positions.push(position);
                }
                
                portfolio.cash -= actualBuyAmountCNY;
                portfolio.trades.push({type: '买入', code: fullCode, name, market, date, price, shares, amount: actualBuyAmountCNY, ratio});
                
                fetch('/api/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(portfolio)});
                updateSummary();
                clearForm();
                
                // 显示成功消息
                if (existingPositionIndex !== -1) {
                    const mergedPos = portfolio.positions[existingPositionIndex];
                    showAlert('buildAlert', name + ' 加仓成功！合并持仓 ' + mergedPos.shares + '股，成本价 ¥' + mergedPos.buyPrice.toFixed(2), 'success');
                } else {
                    showAlert('buildAlert', name + ' 建仓成功 ' + shares + '股', 'success');
                }
            });
        }
        
        function addAnotherStock() {
            const used = portfolio.positions.reduce((s,p) => s + p.buyAmount, 0);
            const available = portfolio.initialCash - used;
            document.getElementById('buyRatio').value = Math.floor(available / portfolio.initialCash * 100);
        }
        
        function updateSellSelect() {
            const select = document.getElementById('sellStockSelect');
            select.innerHTML = '<option value="">请选择</option>';
            portfolio.positions.forEach((p,i) => { select.innerHTML += '<option value="' + i + '">' + p.name + '(' + p.code + ') 持有' + p.shares + '股</option>'; });
            select.onchange = function() {
                const idx = parseInt(this.value);
                if(!isNaN(idx)) {
                    const p = portfolio.positions[idx];
                    document.getElementById('sellDate').value = p.canSellDate;
                    document.getElementById('exchange').value = p.exchange || (p.market === '港股' ? 'HK' : 'SZ');
                    updateExchange();
                    if(closePrices[p.code]) document.getElementById('sellPrice').value = closePrices[p.code].price;
                    
                    // 检查是否为"全部卖出"模式，如果是则自动填入最大比例
                    const sellMethod = document.getElementById('sellMethod').value;
                    if (sellMethod === 'all') {
                        // 获取持仓比例并自动填入
                        fetch('/api/summary').then(r=>r.json()).then(data => {
                            const positionRatio = data.positions ? data.positions[idx].positionRatio : 0;
                            document.getElementById('sellRatio').value = positionRatio.toFixed(1);
                            updateSellPreview();
                        }).catch(() => {
                            document.getElementById('sellRatio').value = 100;
                            updateSellPreview();
                        });
                    }
                    
                    // 计算并显示实际可卖比例
                    calculateAvailableSellRatio(idx);
                    updateSellPreview(); // 更新预览
                }
            };
        }
        
        function updateSellPriceChange() {
            const idx = parseInt(document.getElementById('sellStockSelect').value);
            if(!isNaN(idx)) {
                // 当价格改变时，重新计算可卖比例
                calculateAvailableSellRatio(idx);
            }
            updateSellPreview();
        }
        
        function calculateAvailableSellRatio(idx) {
            // 计算基于剩余股数和当前价格的实际可卖比例
            const pos = portfolio.positions[idx];
            const price = parseFloat(document.getElementById('sellPrice').value) || 0;
            
            if(price <= 0) {
                // 清除提示信息
                const existingHint = document.getElementById('availableRatioHint');
                if (existingHint) {
                    existingHint.remove();
                }
                return;
            }
            
            // 获取当前总资产数据
            fetch('/api/summary').then(r=>r.json()).then(data => {
                const totalAssets = data.totalAssets || 0;
                
                // 计算该股票当前市值（考虑汇率）
                const currentMarketValue = pos.market === '港股' ? 
                    pos.shares * price * hkdCnyRate : 
                    pos.shares * price;
                
                // 计算实际可卖比例 = 当前市值 / 总资产 * 100%
                const availableRatio = totalAssets > 0 ? (currentMarketValue / totalAssets * 100) : 0;
                
                // 更新比例输入框的值（仅在非"全部卖出"模式下）
                const sellMethod = document.getElementById('sellMethod').value;
                if (sellMethod !== 'all') {
                    document.getElementById('sellRatio').value = availableRatio.toFixed(1);
                }
                
                // 显示实际可卖比例信息
                const ratioInput = document.getElementById('sellRatio');
                const existingHint = document.getElementById('availableRatioHint');
                if (existingHint) {
                    existingHint.remove();
                }
                
                // 添加提示信息
                const hint = document.createElement('div');
                hint.id = 'availableRatioHint';
                hint.style.cssText = 'font-size: 12px; color: #00d4ff; margin-top: 4px;';
                
                const priceUnit = pos.market === '港股' ? 'HK$' : '¥';
                const sharesValue = pos.market === '港股' ? 
                    `${pos.shares}股 × ${priceUnit}${price.toFixed(2)} × ${hkdCnyRate} = ¥${currentMarketValue.toFixed(2)}` :
                    `${pos.shares}股 × ${priceUnit}${price.toFixed(2)} = ¥${currentMarketValue.toFixed(2)}`;
                
                hint.innerHTML = `💡 基于当前价格，实际可卖比例: ${availableRatio.toFixed(1)}%<br>
                               <span style="color: #8b9dc3; font-size: 11px;">计算: ${sharesValue}</span>`;
                ratioInput.parentNode.appendChild(hint);
                
            }).catch(error => {
                console.error('计算可卖比例失败:', error);
            });
        }
        
        function handleSellMethodChange() {
            const sellMethod = document.getElementById('sellMethod').value;
            const idx = parseInt(document.getElementById('sellStockSelect').value);
            const ratioInput = document.getElementById('sellRatio');
            
            // 如果选择了"全部卖出"
            if (sellMethod === 'all') {
                // 全部卖出模式：自动填入该股票的持仓比例
                ratioInput.disabled = true;
                
                if(!isNaN(idx)) {
                    // 获取持仓比例并自动填入
                    fetch('/api/summary').then(r=>r.json()).then(data => {
                        const positionRatio = data.positions ? data.positions[idx].positionRatio : 0;
                        ratioInput.value = positionRatio.toFixed(1);
                        updateSellPreview();
                    }).catch(() => {
                        ratioInput.value = 100;
                        updateSellPreview();
                    });
                }
                
                // 隐藏实际可卖比例提示，因为全部卖出不需要这个提示
                const existingHint = document.getElementById('availableRatioHint');
                if (existingHint) {
                    existingHint.style.display = 'none';
                }
            } else if (sellMethod === 'asset') {
                // 切换回"按持仓比例"时启用输入
                ratioInput.disabled = false;
                
                // 重新计算并显示实际可卖比例
                if(!isNaN(idx)) {
                    calculateAvailableSellRatio(idx);
                }
            }
        }
        
        function updateSellPreview() {
            const idx = parseInt(document.getElementById('sellStockSelect').value);
            const price = parseFloat(document.getElementById('sellPrice').value);
            const ratio = parseFloat(document.getElementById('sellRatio').value);
            const sellMethod = document.getElementById('sellMethod').value;
            const preview = document.getElementById('sellPreview');
            const content = document.getElementById('sellPreviewContent');
            
            if(isNaN(idx) || price <= 0) {
                preview.style.display = 'none';
                return;
            }
            
            const pos = portfolio.positions[idx];
            let sellShares, actualRatio, description, maxRatioWarning = '';
            
            // 获取当前汇总数据以获取持仓比例
            fetch('/api/summary').then(r=>r.json()).then(data => {
                const positionRatio = data.positions ? data.positions[idx].positionRatio : 0;
                
                if (sellMethod === 'all') {
                    // 全部卖出模式：卖出所有股数
                    sellShares = pos.shares;
                    actualRatio = '100';
                    description = `全部卖出: 卖出所有持股`;
                    
                    const sellAmount = sellShares * price;
                    const sellAmountCNY = pos.market === '港股' ? sellAmount * hkdCnyRate : sellAmount;
                    
                    content.innerHTML = `
                        <strong>${pos.name} (${pos.code})</strong><br>
                        持仓数量: ${pos.shares}股<br>
                        持仓占比: ${positionRatio.toFixed(1)}%<br>
                        ${description}<br>
                        卖出股数: <strong style="color: #00d4ff;">${sellShares}股</strong><br>
                        卖出价格: ${pos.market === '港股' ? 'HK$' : '¥'}${price.toFixed(2)}<br>
                        预计收入: <strong style="color: #00ff88;">¥${sellAmountCNY.toFixed(2)}</strong>
                    `;
                    preview.style.display = 'block';
                } else {
                    // 按持仓比例模式
                    if(!ratio || ratio <= 0) {
                        preview.style.display = 'none';
                        return;
                    }
                    
                    const maxRatio = Math.min(ratio, positionRatio);
                    
                    // 按持仓比例计算 - 最大持仓比例
                    if(ratio > positionRatio) {
                        maxRatioWarning = `<div style="color: #ff4757; margin-top: 8px;">⚠️ 该股票持仓占比${positionRatio.toFixed(1)}%，最大可卖${positionRatio.toFixed(1)}%</div>`;
                    }
                    const targetAmount = data.totalAssets * (maxRatio / 100);
                    sellShares = Math.floor(targetAmount / price);
                    sellShares = Math.min(sellShares, pos.shares);
                    
                    actualRatio = (sellShares / pos.shares * 100).toFixed(1);
                    description = `按持仓比例: 卖出总资产的${maxRatio.toFixed(1)}%`;
                    
                    const sellAmount = sellShares * price;
                    const sellAmountCNY = pos.market === '港股' ? sellAmount * hkdCnyRate : sellAmount;
                    
                    content.innerHTML = `
                        <strong>${pos.name} (${pos.code})</strong><br>
                        持仓数量: ${pos.shares}股<br>
                        持仓占比: ${positionRatio.toFixed(1)}%<br>
                        ${description}<br>
                        卖出股数: <strong style="color: #00d4ff;">${sellShares}股</strong><br>
                        卖出价格: ${pos.market === '港股' ? 'HK$' : '¥'}${price.toFixed(2)}<br>
                        预计收入: <strong style="color: #00ff88;">¥${sellAmountCNY.toFixed(2)}</strong>
                        ${maxRatioWarning}
                    `;
                    preview.style.display = 'block';
                }
            }).catch(error => {
                console.error('获取汇总数据失败:', error);
                // 降级处理：不显示仓位控制提示
                if (sellMethod === 'all') {
                    sellShares = pos.shares;
                    actualRatio = '100';
                    description = `全部卖出: 卖出所有持股`;
                } else {
                    if(!ratio || ratio <= 0) {
                        preview.style.display = 'none';
                        return;
                    }
                    const totalAssets = portfolio.totalAssets || portfolio.initialCash;
                    const targetAmount = totalAssets * (ratio / 100);
                    sellShares = Math.floor(targetAmount / price);
                    sellShares = Math.min(sellShares, pos.shares);
                    actualRatio = (sellShares / pos.shares * 100).toFixed(1);
                    description = `按持仓比例: 卖出总资产的${ratio}%`;
                }
                
                const sellAmount = sellShares * price;
                const sellAmountCNY = pos.market === '港股' ? sellAmount * hkdCnyRate : sellAmount;
                
                content.innerHTML = `
                    <strong>${pos.name} (${pos.code})</strong><br>
                    持仓数量: ${pos.shares}股<br>
                    ${description}<br>
                    卖出股数: <strong style="color: #00d4ff;">${sellShares}股</strong><br>
                    卖出价格: ${pos.market === '港股' ? 'HK$' : '¥'}${price.toFixed(2)}<br>
                    预计收入: <strong style="color: #00ff88;">¥${sellAmountCNY.toFixed(2)}</strong>
                `;
                preview.style.display = 'block';
            });
        }
        
        function sellStock() {
            const idx = parseInt(document.getElementById('sellStockSelect').value);
            const date = document.getElementById('sellDate').value;
            const price = parseFloat(document.getElementById('sellPrice').value);
            const ratio = parseFloat(document.getElementById('sellRatio').value);
            const sellMethod = document.getElementById('sellMethod').value;
            
            if(isNaN(idx) || !date || !price) return showAlert('sellAlert', '请填写完整', 'error');
            
            const pos = portfolio.positions[idx];
            if(date < pos.canSellDate) return showAlert('sellAlert', '不可在当日卖出(A股T+1,港股T+0)', 'error');
            
            // 获取当前汇总数据进行验证
            fetch('/api/summary').then(r=>r.json()).then(data => {
                let sellShares, actualRatio, confirmMsg;
                const positionRatio = data.positions ? data.positions[idx].positionRatio : 0;
                
                // 全部卖出模式：直接卖出全部股数
                if (sellMethod === 'all') {
                    sellShares = pos.shares;  // 全部股数
                    actualRatio = '100';
                    confirmMsg = `确认卖出（全部卖出）：\n${pos.name} (${pos.code})\n卖出股数: ${sellShares}股 (全部)\n卖出价格: ${pos.market === '港股' ? 'HK$' : '¥'}${price.toFixed(2)}\n预计收入: ¥${(sellShares * price * (pos.market === '港股' ? hkdCnyRate : 1)).toFixed(2)}`;
                } else {
                    // 按持仓比例模式
                    if(!ratio || ratio <= 0) return showAlert('sellAlert', '请填写持仓比例', 'error');
                    
                    if(ratio > positionRatio) {
                        return showAlert('sellAlert', `该股票持仓占比${positionRatio.toFixed(1)}%，最大可卖${positionRatio.toFixed(1)}%`, 'error');
                    }
                    
                    // 按持仓比例计算
                    const maxRatio = Math.min(ratio, positionRatio);
                    const targetAmount = data.totalAssets * (maxRatio / 100);
                    sellShares = Math.floor(targetAmount / price);
                    sellShares = Math.min(sellShares, pos.shares);
                    actualRatio = (sellShares / pos.shares * 100).toFixed(1);
                    
                    confirmMsg = `确认卖出（按持仓比例）：\n${pos.name} (${pos.code})\n卖出总资产比例: ${maxRatio.toFixed(1)}%\n卖出股数: ${sellShares}股 (总${pos.shares}股)\n卖出价格: ${pos.market === '港股' ? 'HK$' : '¥'}${price.toFixed(2)}\n预计收入: ¥${(sellShares * price * (pos.market === '港股' ? hkdCnyRate : 1)).toFixed(2)}`;
                }
                
                if(!confirm(confirmMsg)) return;
                
                const sellAmount = sellShares * price;
                const sellAmountCNY = pos.market === '港股' ? sellAmount * hkdCnyRate : sellAmount;
                
                if(sellShares >= pos.shares) {
                    // 全部卖出
                    portfolio.positions.splice(idx, 1);
                } else {
                    // 部分卖出：按比例调整买入成本
                    const remainingRatio = (pos.shares - sellShares) / pos.shares;
                    pos.shares -= sellShares;
                    pos.buyAmount = pos.buyAmount * remainingRatio;
                }
                
                portfolio.cash += sellAmountCNY;
                portfolio.trades.push({type: '卖出', code: pos.code, name: pos.name, market: pos.market, date, price, shares: sellShares, amount: sellAmountCNY, ratio: parseFloat(actualRatio), method: sellMethod === 'all' ? '全部卖出' : 'asset'});
                
                fetch('/api/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(portfolio)});
                updateSummary();
                updateSellSelect();
                renderPositions(); // 刷新持仓界面
                showAlert('sellAlert', `${pos.name} 卖出成功 (${sellShares}股，比例${actualRatio}%，${sellMethod === 'all' ? '全部卖出' : '按持仓比例'})`, 'success');
            }).catch(error => {
                console.error('获取汇总数据失败:', error);
                // 降级处理：不进行仓位控制验证
                const totalAssets = portfolio.totalAssets || portfolio.initialCash;
                const targetAmount = totalAssets * (ratio / 100);
                let sellShares = Math.floor(targetAmount / price);
                sellShares = Math.min(sellShares, pos.shares);
                const actualRatio = (sellShares / pos.shares * 100).toFixed(1);
                
                const confirmMsg = `确认卖出（按持仓比例）：\n${pos.name} (${pos.code})\n卖出总资产比例: ${ratio}%\n卖出股数: ${sellShares}股 (总${pos.shares}股)\n卖出价格: ${pos.market === '港股' ? 'HK$' : '¥'}${price.toFixed(2)}\n预计收入: ¥${(sellShares * price * (pos.market === '港股' ? hkdCnyRate : 1)).toFixed(2)}`;
                
                if(!confirm(confirmMsg)) return;
                
                const sellAmount = sellShares * price;
                const sellAmountCNY = pos.market === '港股' ? sellAmount * hkdCnyRate : sellAmount;
                
                if(sellShares >= pos.shares) {
                    portfolio.positions.splice(idx, 1);
                } else {
                    const remainingRatio = (pos.shares - sellShares) / pos.shares;
                    pos.shares -= sellShares;
                    pos.buyAmount = pos.buyAmount * remainingRatio;
                }
                
                portfolio.cash += sellAmountCNY;
                portfolio.trades.push({type: '卖出', code: pos.code, name: pos.name, market: pos.market, date, price, shares: sellShares, amount: sellAmountCNY, ratio: parseFloat(actualRatio), method: 'asset'});
                
                fetch('/api/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(portfolio)});
                updateSummary();
                updateSellSelect();
                renderPositions();
                showAlert('sellAlert', `${pos.name} 卖出成功 (${sellShares}股，比例${actualRatio}%，按持仓比例)`, 'success');
            });
        }
        
        function renderPositions() {
            fetch('/api/summary').then(r=>r.json()).then(data => {
                const container = document.getElementById('positionsTable');
                if(!data.positions || data.positions.length === 0) { container.innerHTML = '<div class="empty-state">暂无持仓</div>'; return; }
                
                let html = '<table><thead><tr><th>市场</th><th>代码</th><th>名称</th><th>股数</th><th>成本价</th><th>现价</th><th>市值(¥)</th><th>持仓比例</th><th>变动(¥)</th><th>变动%</th><th>净值贡献</th></tr></thead><tbody>';
                
                data.positions.forEach(p => {
                    const priceDisplay = p.market === '港股' ? 'HK$' + p.currentPrice.toFixed(2) : '¥' + p.currentPrice.toFixed(2);
                    const costDisplay = p.market === '港股' ? 'HK$' + p.buyPrice.toFixed(2) : '¥' + p.buyPrice.toFixed(2);
                    const changeClass = p.change >= 0 ? 'positive' : 'negative';
                    
                    html += '<tr><td><span class="market-tag ' + p.market + '">' + p.market + '</span></td><td>' + p.code + '</td><td>' + p.name + '</td><td>' + p.shares + '</td><td>' + costDisplay + '</td><td>' + priceDisplay + '</td><td>¥' + p.marketValue.toFixed(0) + '</td><td>' + p.positionRatio.toFixed(1) + '%</td><td class="' + changeClass + '">' + (p.change>=0?'+':'') + '¥' + p.change.toFixed(0) + '</td><td class="' + changeClass + '">' + (p.changePct>=0?'+':'') + p.changePct.toFixed(1) + '%</td><td class="' + changeClass + '">' + (p.contribution>=0?'+':'') + p.contribution.toFixed(1) + '%</td></tr>';
                });
                html += '</tbody></table>';
                container.innerHTML = html;
            });
        }
        
        function renderTradeHistory() {
            const container = document.getElementById('tradeHistory');
            if(portfolio.trades.length === 0) { container.innerHTML = '<div class="empty-state">暂无记录</div>'; return; }
            
            let html = '<table><thead><tr><th>时间</th><th>类型</th><th>市场</th><th>代码</th><th>名称</th><th>价格</th><th>数量</th><th>金额(¥)</th></tr></thead><tbody>';
            [...portfolio.trades].reverse().forEach(t => {
                const priceDisplay = t.market === '港股' ? 'HK$' + t.price.toFixed(2) : '¥' + t.price.toFixed(2);
                html += '<tr><td>' + t.date + '</td><td class="' + (t.type==='买入'?'positive':'negative') + '">' + t.type + '</td><td><span class="market-tag ' + t.market + '">' + t.market + '</span></td><td>' + t.code + '</td><td>' + t.name + '</td><td>' + priceDisplay + '</td><td>' + t.shares + '</td><td>¥' + t.amount.toFixed(0) + '</td></tr>';
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        }
        
        function updateSummary() {
            fetch('/api/summary').then(r=>r.json()).then(data => {
                document.getElementById('initialCash').textContent = '¥' + data.initialCash.toLocaleString();
                document.getElementById('totalAssets').textContent = '¥' + data.totalAssets.toLocaleString();
                
                const assetChangeEl = document.getElementById('assetChange');
                assetChangeEl.textContent = (data.assetChange>=0?'+':'') + '¥' + data.assetChange.toLocaleString();
                assetChangeEl.className = 'value ' + (data.assetChange>=0?'positive':'negative');
                
                const assetGrowthEl = document.getElementById('assetGrowth');
                assetGrowthEl.textContent = (data.assetGrowth>=0?'+':'') + data.assetGrowth.toFixed(1) + '%';
                assetGrowthEl.className = 'value ' + (data.assetGrowth>=0?'positive':'negative');
                
                document.getElementById('netValue').textContent = data.netValue.toFixed(4);
                
                const drawdownEl = document.getElementById('netValueDrawdown');
                drawdownEl.textContent = data.netValueDrawdown.toFixed(1) + '%';
                drawdownEl.className = 'value ' + (data.netValueDrawdown >= 0 ? 'positive' : 'negative');
                
                document.getElementById('stockValue').textContent = '¥' + data.stockValue.toLocaleString();
                
                document.getElementById('positionRatio').textContent = data.positionRatio.toFixed(1) + '%';
                
                document.getElementById('positionControlHint').textContent = '（仓位控制' + data.positionControl.toFixed(1) + '%）';
                
                const currentRatio = data.positionRatio;
                if(currentRatio > data.positionControl) {
                    document.getElementById('positionControlAlert').innerHTML = '<div class="alert alert-warning">⚠️ 当前持仓占比已超过仓位控制限制(' + data.positionControl.toFixed(1) + '%)，请卖出部分股票</div>';
                } else if(data.positionControl < 100) {
                    document.getElementById('positionControlAlert').innerHTML = '<div class="alert alert-info">ℹ️ 当前仓位控制限制为 ' + data.positionControl.toFixed(1) + '%</div>';
                } else {
                    document.getElementById('positionControlAlert').innerHTML = '';
                }
                
                document.getElementById('cash').textContent = '¥' + data.cash.toLocaleString();
                document.getElementById('cashRatio').textContent = data.cashRatio.toFixed(1) + '%';
            });
        }
        
        function clearForm() {
            document.getElementById('stockCode').value = '';
            document.getElementById('stockName').value = '';
            document.getElementById('buyPrice').value = '';
            document.getElementById('buyRatio').value = '';
            document.getElementById('priceInfo').innerHTML = '';
        }
        
        // 自动更新所有持仓价格
        function updateAllPrices() {
            if(portfolio.positions.length === 0) {
                console.log('没有持仓，无需更新价格');
                return;
            }
            
            console.log('开始批量更新所有持仓价格...');
            
            // 显示正在更新提示
            showAlert('positionsAlert', '🔄 正在批量更新价格...', 'info');
            
            // 提取所有股票代码
            const codes = portfolio.positions.map(pos => pos.code);
            
            // 使用批量API
            fetch('/api/prices/batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ codes: codes })
            })
            .then(response => response.json())
            .then(data => {
                console.log('批量价格更新返回:', data);
                
                let updatedCount = 0;
                const results = data.results || {};
                
                // 更新本地缓存
                for (const [code, priceData] of Object.entries(results)) {
                    if(priceData.price && priceData.price > 0) {
                        closePrices[code] = {
                            price: priceData.price,
                            name: priceData.name,
                            market: priceData.market
                        };
                        updatedCount++;
                        console.log(`✓ ${priceData.name} 价格更新: ${priceData.price}`);
                    } else {
                        console.log(`✗ ${priceData.name} 价格获取失败或价格为0`);
                    }
                }
                
                console.log(`批量价格更新完成: ${updatedCount}/${codes.length}`);
                
                // 强制刷新汇总和持仓显示
                updateSummary();
                if(document.querySelector('.tab-content[id="tab-持仓"]').style.display !== 'none') {
                    renderPositions();
                }
                
                // 显示更新成功提示
                showAlert('positionsAlert', `🔄 批量价格更新完成！已更新${updatedCount}只股票`, 'success');
            })
            .catch(error => {
                console.error('批量价格更新失败:', error);
                showAlert('positionsAlert', '❌ 批量价格更新失败，请重试', 'error');
            });
        }
        
        // 启动自动更新定时器
        function startAutoUpdate() {
            // 每60秒更新一次价格
            setInterval(() => {
                if(document.visibilityState === 'visible') { // 只在页面可见时更新
                    updateAllPrices();
                }
            }, 60000); // 1分钟 = 60000毫秒
            
            // 每10秒更新一次汇总数据（不重新获取价格，只重新计算）
            setInterval(() => {
                if(document.visibilityState === 'visible') {
                    updateSummary();
                }
            }, 10000); // 10秒 = 10000毫秒
        }
        
        function showAlert(id, msg, type) {
            document.getElementById(id).innerHTML = '<div class="alert alert-'+type+'">'+msg+'</div>';
            setTimeout(() => document.getElementById(id).innerHTML = '', 3000);
        }
        
        function quickSellAll() {
            if(portfolio.positions.length === 0) {
                return showAlert('sellAlert', '当前没有持仓，无需清仓', 'warning');
            }
            
            // 计算总持仓市值
            let totalStockValue = 0;
            let positionDetails = [];
            
            portfolio.positions.forEach((pos, index) => {
                const priceInfo = closePrices[pos.code] || {price: pos.buyPrice};
                const currentPrice = priceInfo.price;
                const marketValue = pos.market === '港股' ? pos.shares * currentPrice * hkdCnyRate : pos.shares * currentPrice;
                totalStockValue += marketValue;
                
                positionDetails.push({
                    name: pos.name,
                    code: pos.code,
                    shares: pos.shares,
                    price: currentPrice,
                    marketValue: marketValue,
                    market: pos.market
                });
            });
            
            // 生成确认信息
            let confirmMsg = `⚠️ 确认一键清仓？\n\n将卖出所有持仓股票：\n\n`;
            positionDetails.forEach(pos => {
                const priceDisplay = pos.market === '港股' ? 'HK$' : '¥';
                confirmMsg += `${pos.name} (${pos.code})\n`;
                confirmMsg += `  ${pos.shares}股 × ${priceDisplay}${pos.price.toFixed(2)} = ¥${pos.marketValue.toFixed(2)}\n`;
            });
            confirmMsg += `\n总持仓市值: ¥${totalStockValue.toFixed(2)}\n`;
            confirmMsg += `预计总收入: ¥${totalStockValue.toFixed(2)}\n\n`;
            confirmMsg += `⚠️ 此操作不可撤销！`;
            
            if(!confirm(confirmMsg)) return;
            
            // 执行清仓
            const today = new Date().toISOString().split('T')[0];
            let totalSoldAmount = 0;
            let soldCount = 0;
            
            portfolio.positions.forEach((pos, index) => {
                const priceInfo = closePrices[pos.code] || {price: pos.buyPrice};
                const currentPrice = priceInfo.price;
                const sellAmount = pos.market === '港股' ? pos.shares * currentPrice * hkdCnyRate : pos.shares * currentPrice;
                
                // 添加交易记录
                portfolio.trades.push({
                    type: '卖出',
                    code: pos.code,
                    name: pos.name,
                    market: pos.market,
                    date: today,
                    price: currentPrice,
                    shares: pos.shares,
                    amount: sellAmount,
                    ratio: 100,
                    method: 'quick_sell_all'
                });
                
                totalSoldAmount += sellAmount;
                soldCount++;
            });
            
            // 清空持仓，增加现金
            portfolio.cash += totalSoldAmount;
            portfolio.positions = [];
            
            // 保存数据
            fetch('/api/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(portfolio)});
            
            // 刷新界面
            updateSummary();
            updateSellSelect();
            renderPositions();
            
            showAlert('sellAlert', `🔥 清仓成功！已卖出${soldCount}只股票，收入¥${totalSoldAmount.toFixed(2)}`, 'success');
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    load_portfolio()
    summary = update_summary()
    return render_template_string(HTML_TEMPLATE, portfolio=portfolio, summary=summary, closePrices=CLOSE_PRICES, exchangeRate=HKD_CNY_RATE)

@app.route('/api/save', methods=['POST'])
def save():
    global portfolio
    portfolio = request.json
    save_portfolio()
    return jsonify({'status': 'ok'})

@app.route('/api/summary')
def get_summary():
    load_portfolio()
    return jsonify(update_summary())

@app.route('/api/price/<code>')
def get_price(code):
    """获取股票价格 - 优先API"""
    import pandas as pd
    from datetime import datetime, timedelta
    
    # 处理代码格式
    original_code = code
    if '.' not in code:
        # 全面支持A股代码格式转换
        if code.startswith('6') or code.startswith('5'):
            # 600-699, 500-599 → 上海证券交易所 (包括688科创板)
            code = code + '.SH'
        elif code.startswith('00') or code.startswith('30'):
            # 000-009, 300-309 → 深圳证券交易所 (包括创业板300)
            code = code + '.SZ'
        elif code.startswith('8') or code.startswith('4'):
            # 8xxx, 4xxx → 北京证券交易所
            code = code + '.BJ'
        elif code.startswith('HK'):
            code = code + '.HK'
    
    # 优先从同花顺获取实时价格
    if HAS_IFIND:
        try:
            # 使用THS_RQ获取实时行情最新价
            result = THS_RQ(code, 'latest')
            if result is not None and result.errorcode == 0 and result.data is not None and len(result.data) > 0:
                # 确保是DataFrame
                df = result.data
                if hasattr(df, 'iloc'):
                    latest = df.iloc[-1]
                else:
                    latest = result.data.iloc[-1]
                
                # 获取最新价
                if 'latest' in latest.index and pd.notna(latest.get('latest')) and latest.get('latest') != 0:
                    price = float(latest.get('latest', 0))
                    print(f"获取到实时价格 {code}: {price}")
                else:
                    # 如果THS_RQ失败，尝试THS_HQ作为备选
                    hq_result = THS_HQ(code, 'preclose,high,low,last,thsname,close', 'block=gpbm')
                    if hq_result is not None and hq_result.errorcode == 0 and hq_result.data is not None and len(hq_result.data) > 0:
                        hq_df = hq_result.data
                        if hasattr(hq_df, 'iloc'):
                            hq_latest = hq_df.iloc[-1]
                        else:
                            hq_latest = hq_result.data.iloc[-1]
                        
                        # 优先使用最新价last（实时价格），如果没有则使用收盘价close
                        if 'last' in hq_latest.index and pd.notna(hq_latest.get('last')) and hq_latest.get('last') != 0:
                            price = float(hq_latest.get('last', 0))
                            print(f"THS_RQ失败，使用THS_HQ获取到实时价格 {code}: {price}")
                        elif 'close' in hq_latest.index and pd.notna(hq_latest.get('close')) and hq_latest.get('close') != 0:
                            price = float(hq_latest.get('close', 0))
                            print(f"THS_RQ和THS_HQ最新价都失败，使用收盘价 {code}: {price}")
                        else:
                            price = 0
                    else:
                        price = 0
                
                # 判断市场
                market = 'A股'
                if code.endswith('.HK'):
                    market = '港股'
                
                if price and price > 0:
                    # 优先使用Excel名称，如果Excel没有才使用同花顺名称
                    excel_name = get_stock_name_from_excel(code)
                    final_name = excel_name if excel_name else code
                    
                    # 更新本地缓存
                    CLOSE_PRICES[code] = {'price': price, 'name': final_name, 'market': market}
                    return jsonify({
                        'code': code,
                        'name': final_name,
                        'price': price,
                        'market': market,
                        'source': 'iFinD_realtime'
                    })
        except Exception as e:
            print(f"同花顺获取 {code} 价格失败: {e}")
    
    # 如果同花顺失败，尝试从Excel获取名称（价格为0）
    excel_name = get_stock_name_from_excel(code)
    if excel_name:
        return jsonify({
            'code': code,
            'name': excel_name,
            'price': 0,
            'market': 'A股',
            'source': 'excel_fallback'
        })
    
    # 如果本地缓存有数据，返回本地缓存
    if code in CLOSE_PRICES:
        return jsonify({
            'code': code,
            'name': CLOSE_PRICES[code].get('name', code),
            'price': CLOSE_PRICES[code].get('price', 0),
            'market': CLOSE_PRICES[code].get('market', 'A股'),
            'source': 'local_cache'
        })
    
    # 如果都失败，返回默认值
    return jsonify({
        'code': code,
        'name': original_code,
        'price': 0,
        'market': 'A股',
        'source': 'none'
    })

@app.route('/api/prices/batch', methods=['POST'])
def get_batch_prices():
    """批量获取股票价格"""
    import pandas as pd
    from datetime import datetime, timedelta
    
    data = request.get_json()
    codes = data.get('codes', [])
    
    if not codes:
        return jsonify({'error': 'No codes provided'})
    
    results = {}
    
    for code in codes:
        try:
            # 处理代码格式
            original_code = code
            if '.' not in code:
                if code.startswith('6') or code.startswith('5'):
                    code = code + '.SH'
                elif code.startswith('00') or code.startswith('30'):
                    code = code + '.SZ'
                elif code.startswith('8') or code.startswith('4'):
                    code = code + '.BJ'
                elif code.startswith('HK'):
                    code = code + '.HK'
            
            # 优先从同花顺获取实时价格
            price = 0
            market = 'A股'
            source = 'none'
            name = original_code
            
            if HAS_IFIND:
                try:
                    result = THS_RQ(code, 'latest')
                    if result is not None and result.errorcode == 0 and result.data is not None and len(result.data) > 0:
                        df = result.data
                        if hasattr(df, 'iloc'):
                            latest = df.iloc[-1]
                        else:
                            latest = result.data.iloc[-1]
                        
                        if 'latest' in latest.index and pd.notna(latest.get('latest')) and latest.get('latest') != 0:
                            price = float(latest.get('latest', 0))
                            source = 'iFinD_realtime'
                            print(f"批量获取到实时价格 {code}: {price}")
                        
                        if code.endswith('.HK'):
                            market = '港股'
                        
                        if price > 0:
                            excel_name = get_stock_name_from_excel(code)
                            name = excel_name if excel_name else original_code
                            
                            # 更新本地缓存
                            CLOSE_PRICES[code] = {'price': price, 'name': name, 'market': market}
                    
                except Exception as e:
                    print(f"批量获取 {code} 价格失败: {e}")
            
            # 如果同花顺失败，尝试本地缓存
            if price == 0 and code in CLOSE_PRICES:
                cached_data = CLOSE_PRICES[code]
                price = cached_data.get('price', 0)
                name = cached_data.get('name', original_code)
                market = cached_data.get('market', 'A股')
                source = 'local_cache'
            
            results[original_code] = {
                'code': original_code,
                'name': name,
                'price': price,
                'market': market,
                'source': source
            }
            
        except Exception as e:
            print(f"处理 {code} 时出错: {e}")
            results[code] = {
                'code': code,
                'name': code,
                'price': 0,
                'market': 'A股',
                'source': 'error'
            }
    
    return jsonify({'results': results})

@app.route('/api/export/positions')
def export_positions():
    """导出持仓为Excel文件"""
    import pandas as pd
    from io import BytesIO
    
    load_portfolio()
    
    if not portfolio.get('positions'):
        return jsonify({'error': 'No positions to export'})
    
    # 准备导出数据 - 简化为4列
    export_data = []
    for pos in portfolio['positions']:
        # 计算买入占比
        buy_ratio = (pos['buyAmount'] / portfolio['initialCash'] * 100) if portfolio['initialCash'] > 0 else 0
        
        export_data.append({
            '股票代码': pos['code'],
            '股票名称': pos.get('name', ''),
            '买入价格': round(pos['buyPrice'], 2),
            '买入占比(%)': round(buy_ratio, 2)
        })
    
    # 创建DataFrame
    df = pd.DataFrame(export_data)
    
    # 创建Excel文件
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='持仓明细', index=False)
        
        # 获取工作表对象，设置列宽
        worksheet = writer.sheets['持仓明细']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 20)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f'持仓导出_{datetime.now().strftime("%Y%m%d")}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/api/import/positions', methods=['POST'])
def import_positions():
    """从Excel文件导入持仓"""
    import pandas as pd
    from werkzeug.utils import secure_filename
    
    load_portfolio()
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '没有选择文件'})
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'success': False, 'error': '文件格式错误，请上传Excel文件'})
    
    try:
        # 读取Excel文件
        df = pd.read_excel(file)
        
        # 检查必需列 - 简化为3列
        required_columns = ['股票代码', '买入价格', '买入占比(%)']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return jsonify({
                'success': False, 
                'error': f'缺少必需列：{", ".join(missing_columns)}'
            })
        
        imported_count = 0
        today = datetime.now().strftime('%Y-%m-%d')
        
        for index, row in df.iterrows():
            try:
                code = str(row['股票代码']).strip()
                price = float(row['买入价格'])
                ratio = float(row['买入占比(%)'])
                
                # 验证数据
                if not code or price <= 0 or ratio <= 0:
                    print(f"跳过第{index+1}行：数据不完整")
                    continue
                
                # 验证股票代码必须带交易所后缀
                if '.' not in code:
                    print(f"跳过第{index+1}行：股票代码{code}缺少交易所后缀")
                    continue
                
                # 提取交易所
                exchange = code.split('.')[-1].upper()
                if exchange not in ['SZ', 'SH', 'BJ', 'HK']:
                    print(f"跳过第{index+1}行：不支持的交易所后缀.{exchange}")
                    continue
                
                # 判断市场
                market = '港股' if exchange == 'HK' else 'A股'
                
                # 计算买入金额
                planned_amount = portfolio['initialCash'] * (ratio / 100)
                
                # 计算股数
                if market == '港股':
                    planned_amount_cny = planned_amount
                    planned_amount_hkd = planned_amount_cny / HKD_CNY_RATE
                    shares = int(planned_amount_hkd / price)
                    actual_buy_amount_cny = shares * price * HKD_CNY_RATE
                else:
                    shares = int(planned_amount / price)
                    actual_buy_amount_cny = shares * price
                
                # 检查资金是否足够
                if actual_buy_amount_cny > portfolio['cash']:
                    print(f"跳过第{index+1}行：资金不足")
                    continue
                
                # 获取股票名称
                stock_name = get_stock_name_from_excel(code) or code
                
                # 检查是否已存在
                existing_pos = None
                for i, pos in enumerate(portfolio['positions']):
                    if pos['code'] == code:
                        existing_pos = i
                        break
                
                if existing_pos is not None:
                    # 更新现有持仓
                    existing = portfolio['positions'][existing_pos]
                    total_shares = existing['shares'] + shares
                    total_amount = existing['buyAmount'] + actual_buy_amount_cny
                    weighted_price = total_amount / total_shares
                    
                    portfolio['positions'][existing_pos] = {
                        **existing,
                        'shares': total_shares,
                        'buyPrice': weighted_price,
                        'buyAmount': total_amount,
                        'buyDate': today
                    }
                    print(f"更新持仓：{stock_name} {existing['shares']}+{shares}={total_shares}股")
                else:
                    # 新增持仓
                    new_position = {
                        'code': code,
                        'name': stock_name,
                        'market': market,
                        'exchange': exchange,
                        'buyDate': today,
                        'buyPrice': price,
                        'shares': shares,
                        'buyAmount': actual_buy_amount_cny,
                        'canSellDate': today
                    }
                    portfolio['positions'].append(new_position)
                    print(f"新增持仓：{stock_name} {shares}股")
                
                # 更新现金
                portfolio['cash'] -= actual_buy_amount_cny
                
                # 添加交易记录
                portfolio['trades'].append({
                    'type': '买入',
                    'code': code,
                    'name': stock_name,
                    'market': market,
                    'date': today,
                    'price': price,
                    'shares': shares,
                    'amount': actual_buy_amount_cny,
                    'ratio': ratio
                })
                
                imported_count += 1
                
            except Exception as e:
                print(f"导入第{index+1}行数据失败: {e}")
                continue
        
        # 保存更新后的组合数据
        save_portfolio()
        
        return jsonify({
            'success': True,
            'imported_count': imported_count,
            'portfolio': portfolio
        })
        
    except Exception as e:
        print(f"导入Excel文件失败: {e}")
        return jsonify({
            'success': False,
            'error': f'文件处理失败：{str(e)}'
        })

@app.route('/api/excel-name/<code>')
def get_excel_name(code):
    """专门从Excel获取股票名称"""
    excel_name = get_stock_name_from_excel(code)
    if excel_name:
        return jsonify({
            'code': code,
            'name': excel_name,
            'source': 'excel'
        })
    else:
        return jsonify({
            'code': code,
            'name': code,
            'source': 'none'
        })

if __name__ == '__main__':
    import socket
    
    # 启动前检查并清理旧进程
    def check_and_kill_old_process(port=5006):
        """检查端口是否被占用，如果是则杀掉旧进程"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('127.0.0.1', port))
            sock.close()
            return False  # 端口未被占用
        except OSError:
            # 端口被占用，尝试找到并杀掉旧进程
            sock.close()
            import subprocess
            try:
                # 查找占用端口的进程
                result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if f':{port}' in line:
                        # 提取PID
                        import re
                        pid_match = re.search(r'pid=(\d+)', line)
                        if pid_match:
                            old_pid = pid_match.group(1)
                            print(f"⚠️ 发现旧进程 PID={old_pid} 占用端口 {port}，正在清理...")
                            subprocess.run(['kill', old_pid])
                            import time
                            time.sleep(1)
                            print(f"✓ 已终止旧进程")
                            return True
            except Exception as e:
                print(f"⚠️ 清理旧进程失败: {e}")
            return True
    
    # 检查并清理旧进程
    check_and_kill_old_process(5006)
    
    # 启动时加载数据
    load_portfolio()
    
    # 初始化同花顺接口
    if HAS_IFIND:
        try:
            print("正在初始化同花顺接口...")
            login_result = THS_iFinDLogin(IFIND_USER, IFIND_PASS)
            if login_result == 0:
                print("✓ 同花顺接口登录成功")
            else:
                print(f"✗ 同花顺接口登录失败: {login_result}")
                HAS_IFIND = False
        except Exception as e:
            print(f"✗ 同花顺接口初始化失败: {e}")
            HAS_IFIND = False
    
    print("="*50)
    print("股票组合模拟交易 Web服务")
    print("="*50)
    if HAS_IFIND:
        print("[OK] 同花顺接口已加载")
    else:
        print("[WARN] 同花顺接口未加载")
    print("请在浏览器打开: http://localhost:5006")
    print("="*50)
    try:
        app.run(debug=False, host='0.0.0.0', port=5006)
    except KeyboardInterrupt:
        print("\n服务已停止")
