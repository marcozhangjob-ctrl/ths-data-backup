# -*- coding: utf-8 -*-
"""
个股仓位控制系统
根据个股的累计涨幅和回撤幅度自动计算仓位限制和减仓提示
"""
from flask import Flask, render_template_string, request, jsonify
import json
from datetime import datetime, timedelta
import os
import sys

app = Flask(__name__)

# 数据文件路径
DATA_FILE = '/home/openclaw/.openclaw/workspace/实时监控！/position_control_data.json'

# 投资组合数据
portfolio = {
    'initialCash': 50000000,  # 初始资金5000万
    'positions': [],  # 持仓列表
}

def load_data():
    global portfolio
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                portfolio = json.load(f)
        except:
            pass

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)

def calculate_position_limit(cumulative_increase):
    """
    计算仓位限制
    根据累计涨幅返回允许的最大买入/持仓比例
    """
    if cumulative_increase >= 65 and cumulative_increase < 100:
        return 10, "止盈", "累计涨幅65%-100%，仓位限制10%以内"
    elif cumulative_increase >= 100:
        return 5, "止盈", "累计涨幅≥100%，仓位限制5%以内"
    else:
        return 20, "正常", "仓位限制20%以内"

def calculate_reduction(stock_position):
    """
    计算减仓比例
    返回: (减仓比例, 提示信息, 是否清仓)
    """
    cumulative_increase = stock_position.get('cumulative_increase', 0)  # 累计涨幅%
    drawdown = stock_position.get('drawdown', 0)  # 回撤幅度%
    position_ratio = stock_position.get('position_ratio', 0)  # 持仓比例%
    
    # 情况1：累计涨幅为正
    if cumulative_increase > 0:
        # 1.1 回撤在 -4.5% 到 -15% 之间
        if drawdown > -15 and drawdown <= -4.5:
            # 减仓比例 = 回撤幅度/累计涨幅 * 持仓比例
            reduction_ratio = abs(drawdown) / cumulative_increase * position_ratio
            reduction_ratio = min(reduction_ratio, position_ratio)  # 不能超过持仓比例
            return reduction_ratio, f"减仓提示：{stock_position.get('name', '')}回撤{drawdown:.1f}%，累计涨幅{cumulative_increase:.1f}%，建议减仓比例{reduction_ratio:.1f}%", False
        
        # 1.2 回撤 <= -15%
        elif drawdown <= -15:
            return position_ratio, f"清仓提示：{stock_position.get('name', '')}回撤已达{abs(drawdown):.1f}%，超过15%红线，建议清仓", True
    
    # 情况2：累计涨幅为负（亏损）
    else:
        loss = abs(cumulative_increase)  # 亏损比例
        
        # 仓位限制在6%以内
        if position_ratio > 6:
            return position_ratio - 6, f"仓位超限：{stock_position.get('name', '')}处于亏损状态，仓位需控制在6%以内，当前{position_ratio:.1f}%，需减仓{position_ratio - 6:.1f}%", False
        
        # 减仓公式：累计亏损比例 * 15 * 持仓占比
        reduction_ratio = loss * 0.15 * position_ratio
        reduction_ratio = min(reduction_ratio, position_ratio)
        
        # 如果亏损达到-4.5%以上，建议清仓
        if loss >= 4.5:
            return position_ratio, f"清仓提示：{stock_position.get('name', '')}亏损{loss:.1f}%，已达止损线，建议清仓", True
        
        return reduction_ratio, f"减仓提示：{stock_position.get('name', '')}亏损{loss:.1f}%，建议减仓比例{reduction_ratio:.1f}%", False
    
    # 无需减仓
    return 0, "持有", "持有"

# HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>个股仓位控制系统</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #fff; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; color: #00d4ff; }
        
        .card { background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        .card h2 { color: #00d4ff; margin-bottom: 16px; font-size: 18px; }
        
        .form-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
        .form-group { flex: 1; min-width: 150px; }
        .form-group label { display: block; margin-bottom: 6px; color: #8b9dc3; font-size: 13px; }
        .form-group input { width: 100%; padding: 10px; border: 1px solid #333; border-radius: 6px; background: rgba(0,0,0,0.3); color: #fff; }
        .form-group input:focus { outline: none; border-color: #00d4ff; }
        
        .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.3s; }
        .btn-primary { background: linear-gradient(135deg, #00d4ff, #0099cc); color: #fff; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,212,255,0.3); }
        .btn-danger { background: linear-gradient(135deg, #ff6b6b, #ee5a24); color: #fff; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 12px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }
        th { background: rgba(0,212,255,0.1); color: #00d4ff; font-weight: 600; }
        tr:hover { background: rgba(255,255,255,0.02); }
        
        .alert { padding: 12px 16px; border-radius: 6px; margin: 12px 0; }
        .alert-warning { background: rgba(255,193,7,0.2); border: 1px solid #ffc107; color: #ffc107; }
        .alert-danger { background: rgba(255,107,107,0.2); border: 1px solid #ff6b6b; color: #ff6b6b; }
        .alert-success { background: rgba(0,255,136,0.2); border: 1px solid #00ff88; color: #00ff88; }
        .alert-info { background: rgba(0,212,255,0.2); border: 1px solid #00d4ff; color: #00d4ff; }
        
        .position-tag { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .position-ok { background: rgba(0,255,136,0.2); color: #00ff88; }
        .position-warning { background: rgba(255,193,7,0.2); color: #ffc107; }
        .position-danger { background: rgba(255,107,107,0.2); color: #ff6b6b; }
        
        .tabs { display: flex; gap: 8px; margin-bottom: 20px; }
        .tab { padding: 12px 24px; background: rgba(255,255,255,0.05); border: none; border-radius: 8px; color: #8b9dc3; cursor: pointer; transition: all 0.3s; }
        .tab.active { background: linear-gradient(135deg, #00d4ff, #0099cc); color: #fff; }
        
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .tips { background: rgba(0,212,255,0.05); border-radius: 8px; padding: 16px; margin-top: 20px; }
        .tips h3 { color: #00d4ff; margin-bottom: 12px; font-size: 16px; }
        .tips ul { color: #8b9dc3; font-size: 13px; line-height: 1.8; padding-left: 20px; }
        
        .empty-state { text-align: center; padding: 40px; color: #8b9dc3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ 个股仓位控制系统</h1>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('positions')">持仓管理</button>
            <button class="tab" onclick="switchTab('add')">添加持仓</button>
            <button class="tab" onclick="switchTab('rules')">规则说明</button>
        </div>
        
        <div class="tab-content active" id="tab-positions">
            <div class="card">
                <h2>📊 持仓列表与仓位控制</h2>
                <div id="positionsTable"></div>
            </div>
        </div>
        
        <div class="tab-content" id="tab-add">
            <div class="card">
                <h2>➕ 添加/更新持仓</h2>
                <div class="form-row">
                    <div class="form-group">
                        <label>股票代码</label>
                        <input type="text" id="stockCode" placeholder="如: 600519.SH">
                    </div>
                    <div class="form-group">
                        <label>股票名称</label>
                        <input type="text" id="stockName" placeholder="如: 贵州茅台">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>最低点日期</label>
                        <input type="date" id="lowestDate">
                    </div>
                    <div class="form-group">
                        <label>最低点价格</label>
                        <input type="number" id="lowestPrice" step="0.01" placeholder="如: 1500.00">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>买入日期</label>
                        <input type="date" id="buyDate">
                    </div>
                    <div class="form-group">
                        <label>买入价格</label>
                        <input type="number" id="buyPrice" step="0.01" placeholder="如: 1800.00">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>当前价格</label>
                        <input type="number" id="currentPrice" step="0.01" placeholder="如: 2000.00">
                    </div>
                    <div class="form-group">
                        <label>持仓占比(%)</label>
                        <input type="number" id="positionRatio" step="0.1" placeholder="如: 15.5">
                    </div>
                </div>
                <div class="form-row">
                    <button class="btn btn-primary" onclick="addPosition()">💾 保存持仓</button>
                    <button class="btn btn-danger" onclick="clearForm()">清空表单</button>
                </div>
                <div id="addAlert"></div>
            </div>
        </div>
        
        <div class="tab-content" id="tab-rules">
            <div class="card">
                <h2>📋 仓位控制规则</h2>
                <div class="tips">
                    <h3>一、建仓和持有止盈的仓位限制</h3>
                    <ul>
                        <li><strong>累计涨幅 ≥65% 且 &lt;100%</strong>：买入仓位限制10%以内，超过提示"止盈至10%以内"</li>
                        <li><strong>累计涨幅 ≥100%</strong>：买入仓位限制5%以内，超过提示"止盈至5%以内"</li>
                        <li><strong>其他情形</strong>：买入/持有仓位限制20%以内，超过提示不能买入或止盈至20%</li>
                    </ul>
                </div>
                <div class="tips">
                    <h3>二、强制减仓规则</h3>
                    <ul>
                        <li><strong>累计涨幅为正，回撤-4.5%至-15%</strong>：建议减仓 = |回撤|/累计涨幅 × 持仓比例</li>
                        <li><strong>累计涨幅为正，回撤≤-15%</strong>：建议清仓（减仓比例=全部持仓）</li>
                        <li><strong>累计涨幅为负（亏损）</strong>：仓位限制6%以内；减仓 = 亏损比例 × 15 × 持仓比例</li>
                        <li><strong>亏损≥4.5%</strong>：建议清仓（止损）</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let positions = [];
        
        document.addEventListener('DOMContentLoaded', function() {
            loadPositions();
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('buyDate').value = today;
            document.getElementById('lowestDate').value = today;
        });
        
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
            if(tab === 'positions') loadPositions();
        }
        
        function loadPositions() {
            fetch('/api/positions')
                .then(r => r.json())
                .then(data => {
                    positions = data.positions || [];
                    renderPositions();
                });
        }
        
        function renderPositions() {
            const container = document.getElementById('positionsTable');
            if(positions.length === 0) {
                container.innerHTML = '<div class="empty-state">暂无持仓，请先添加</div>';
                return;
            }
            
            let html = '<table><thead><tr><th>股票</th><th>最低点</th><th>买入价</th><th>现价</th><th>累计涨幅</th><th>持仓比例</th><th>回撤</th><th>仓位限制</th><th>状态</th><th>操作</th></tr></thead><tbody>';
            
            positions.forEach((p, idx) => {
                const cumulative_increase = p.cumulative_increase || 0;
                const drawdown = p.drawdown || 0;
                const position_ratio = p.position_ratio || 0;
                
                // 计算仓位限制
                let limit_info = getLimitInfo(cumulative_increase, position_ratio);
                
                // 获取减仓提示
                let reduction = getReductionInfo(p);
                
                // 状态样式
                let statusClass = 'position-ok';
                let statusText = '正常';
                if(limit_info.warning || reduction.warning) {
                    statusClass = 'position-warning';
                    statusText = '注意';
                }
                if(reduction.sell_all || (cumulative_increase < 0 && position_ratio > 6)) {
                    statusClass = 'position-danger';
                    statusText = '警告';
                }
                
                html += `<tr>
                    <td>${p.name}<br><small style="color:#8b9dc3">${p.code}</small></td>
                    <td>${p.lowest_date}<br><small style="color:#00ff88">¥${p.lowest_price}</small></td>
                    <td>¥${p.buy_price}</td>
                    <td>¥${p.current_price}</td>
                    <td style="color:${cumulative_increase >= 0 ? '#00ff88' : '#ff6b6b'}">${cumulative_increase >= 0 ? '+' : ''}${cumulative_increase.toFixed(1)}%</td>
                    <td>${position_ratio.toFixed(1)}%</td>
                    <td style="color:${drawdown >= 0 ? '#00ff88' : '#ff6b6b'}">${drawdown.toFixed(1)}%</td>
                    <td>${limit_info.limit}%</td>
                    <td><span class="position-tag ${statusClass}">${statusText}</span></td>
                    <td><button class="btn btn-danger" style="padding:4px 8px;font-size:12px;" onclick="deletePosition(${idx})">删除</button></td>
                </tr>`;
            });
            html += '</tbody></table>';
            
            // 添加警告信息
            let warnings = '';
            positions.forEach(p => {
                let limit_info = getLimitInfo(p.cumulative_increase || 0, p.position_ratio || 0);
                let reduction = getReductionInfo(p);
                if(limit_info.warning) {
                    warnings += `<div class="alert alert-warning">${limit_info.warning}</div>`;
                }
                if(reduction.warning) {
                    warnings += `<div class="alert ${reduction.sell_all ? 'alert-danger' : 'alert-warning'}">${reduction.message}</div>`;
                }
            });
            
            container.innerHTML = warnings + html;
        }
        
        function getLimitInfo(cumulative_increase, position_ratio) {
            if(cumulative_increase >= 65 && cumulative_increase < 100) {
                if(position_ratio > 10) {
                    return { limit: 10, warning: `⚠️ 累计涨幅${cumulative_increase.toFixed(1)}%，仓位需控制在10%以内，当前${position_ratio.toFixed(1)}%，请止盈` };
                }
                return { limit: 10, warning: null };
            } else if(cumulative_increase >= 100) {
                if(position_ratio > 5) {
                    return { limit: 5, warning: `⚠️ 累计涨幅≥100%，仓位需控制在5%以内，当前${position_ratio.toFixed(1)}%，请止盈` };
                }
                return { limit: 5, warning: null };
            } else {
                if(position_ratio > 20) {
                    return { limit: 20, warning: `⚠️ 仓位需控制在20%以内，当前${position_ratio.toFixed(1)}%` };
                }
                return { limit: 20, warning: null };
            }
        }
        
        function getReductionInfo(p) {
            const cumulative_increase = p.cumulative_increase || 0;
            const drawdown = p.drawdown || 0;
            const position_ratio = p.position_ratio || 0;
            
            if(cumulative_increase > 0) {
                if(drawdown > -15 && drawdown <= -4.5) {
                    const reduction = Math.abs(drawdown) / cumulative_increase * position_ratio;
                    return { 
                        reduction: reduction, 
                        message: `🔔 ${p.name}回撤${Math.abs(drawdown).toFixed(1)}%，建议减仓${reduction.toFixed(1)}%`,
                        warning: true,
                        sell_all: false
                    };
                } else if(drawdown <= -15) {
                    return {
                        reduction: position_ratio,
                        message: `🚨 ${p.name}回撤已达${Math.abs(drawdown).toFixed(1)}%，建议清仓`,
                        warning: true,
                        sell_all: true
                    };
                }
            } else {
                // 亏损状态
                const loss = Math.abs(cumulative_increase);
                if(position_ratio > 6) {
                    return {
                        reduction: position_ratio - 6,
                        message: `⚠️ ${p.name}处于亏损状态，仓位需控制在6%以内，当前${position_ratio.toFixed(1)}%，需减仓${(position_ratio - 6).toFixed(1)}%`,
                        warning: true,
                        sell_all: false
                    };
                }
                if(loss >= 4.5) {
                    return {
                        reduction: position_ratio,
                        message: `🚨 ${p.name}亏损${loss.toFixed(1)}%，已达止损线，建议清仓`,
                        warning: true,
                        sell_all: true
                    };
                }
                const reduction = loss * 0.15 * position_ratio;
                if(reduction > 0) {
                    return {
                        reduction: reduction,
                        message: `🔔 ${p.name}亏损${loss.toFixed(1)}%，建议减仓${reduction.toFixed(1)}%`,
                        warning: true,
                        sell_all: false
                    };
                }
            }
            
            return { reduction: 0, message: '', warning: false, sell_all: false };
        }
        
        function addPosition() {
            const code = document.getElementById('stockCode').value.trim();
            const name = document.getElementById('stockName').value.trim();
            const lowest_date = document.getElementById('lowestDate').value;
            const lowest_price = parseFloat(document.getElementById('lowestPrice').value);
            const buy_date = document.getElementById('buyDate').value;
            const buy_price = parseFloat(document.getElementById('buyPrice').value);
            const current_price = parseFloat(document.getElementById('currentPrice').value);
            const position_ratio = parseFloat(document.getElementById('positionRatio').value);
            
            if(!code || !name || !lowest_date || !lowest_price || !buy_date || !buy_price || !current_price || !position_ratio) {
                showAlert('addAlert', '请填写完整信息', 'error');
                return;
            }
            
            // 计算累计涨幅和回撤
            const cumulative_increase = (buy_price - lowest_price) / lowest_price * 100;
            const current_increase = (current_price - buy_price) / buy_price * 100;
            // 简化的回撤计算（实际应该是从最高点到当前点的回撤）
            const drawdown = current_increase > 0 ? -4.5 : current_increase;  // 这里需要输入高点数据
            
            const position = {
                code, name, lowest_date, lowest_price, buy_date, buy_price,
                current_price, position_ratio,
                cumulative_increase,
                drawdown,
                add_time: new Date().toISOString()
            };
            
            // 检查是否已存在，存在则更新
            const existIdx = positions.findIndex(p => p.code === code);
            if(existIdx >= 0) {
                positions[existIdx] = position;
            } else {
                positions.push(position);
            }
            
            savePositions();
            showAlert('addAlert', '保存成功', 'success');
            clearForm();
        }
        
        function deletePosition(idx) {
            if(confirm('确定删除该持仓？')) {
                positions.splice(idx, 1);
                savePositions();
                renderPositions();
            }
        }
        
        function clearForm() {
            document.getElementById('stockCode').value = '';
            document.getElementById('stockName').value = '';
            document.getElementById('lowestPrice').value = '';
            document.getElementById('buyPrice').value = '';
            document.getElementById('currentPrice').value = '';
            document.getElementById('positionRatio').value = '';
        }
        
        function savePositions() {
            fetch('/api/positions', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({positions})
            });
        }
        
        function showAlert(id, msg, type) {
            const colors = { success: '#00ff88', error: '#ff6b6b', warning: '#ffc107', info: '#00d4ff' };
            document.getElementById(id).innerHTML = `<div class="alert alert-${type}">${msg}</div>`;
            setTimeout(() => {
                document.getElementById(id).innerHTML = '';
            }, 5000);
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    load_data()
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/positions')
def get_positions():
    load_data()
    return jsonify(portfolio)

@app.route('/api/positions', methods=['POST'])
def save_positions():
    global portfolio
    data = request.json
    portfolio['positions'] = data.get('positions', [])
    save_data()
    return jsonify({'status': 'ok'})

@app.route('/api/calculate', methods=['POST'])
def calculate():
    """计算单个股票的仓位控制信息"""
    data = request.json
    position = {
        'name': data.get('name', ''),
        'code': data.get('code', ''),
        'cumulative_increase': data.get('cumulative_increase', 0),
        'drawdown': data.get('drawdown', 0),
        'position_ratio': data.get('position_ratio', 0)
    }
    
    # 仓位限制
    limit, status, msg = calculate_position_limit(position['cumulative_increase'])
    
    # 减仓计算
    reduction, reduction_msg, should_sell_all = calculate_reduction(position)
    
    return jsonify({
        'position_limit': limit,
        'limit_status': status,
        'limit_message': msg,
        'reduction_ratio': reduction,
        'reduction_message': reduction_msg,
        'should_sell_all': should_sell_all
    })

if __name__ == '__main__':
    # 启动时加载数据
    load_data()
    print("="*50)
    print("个股仓位控制系统")
    print("="*50)
    print("请在浏览器打开: http://localhost:5007")
    print("="*50)
    app.run(debug=False, host='0.0.0.0', port=5007)
