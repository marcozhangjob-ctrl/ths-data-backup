#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试仓位控制计算
"""
import json
import os

# 读取实际的投资组合数据
DATA_FILE = '/home/openclaw/.openclaw/workspace/实时监控！/portfolio_data.json'

def debug_position_control():
    """调试仓位控制计算"""
    if not os.path.exists(DATA_FILE):
        print("找不到数据文件")
        return
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        portfolio = json.load(f)
    
    # 计算当前状态
    initial_cash = portfolio.get('initialCash', 0)
    current_cash = portfolio.get('cash', 0)
    
    total_stock_value = 0
    for pos in portfolio.get('positions', []):
        # 简化计算，使用买入价作为当前价
        total_stock_value += pos.get('buyAmount', 0)
    
    total_assets = total_stock_value + current_cash
    asset_change = total_assets - initial_cash
    asset_growth = (asset_change / initial_cash * 100) if initial_cash > 0 else 0
    
    # 净值回撤计算
    current_net_value = total_assets / initial_cash if initial_cash > 0 else 1.0
    peak_net_value = portfolio.get('peakNetValue', current_net_value)
    
    if current_net_value > peak_net_value:
        net_value_drawdown = 0.0
    else:
        net_value_drawdown = (current_net_value - peak_net_value) / peak_net_value * 100
    
    print("=== 当前组合状态 ===")
    print(f"初始资金: {initial_cash:,.0f}")
    print(f"总资产: {total_assets:,.0f}")
    print(f"资产变动: {asset_change:,.0f}")
    print(f"资产增长: {asset_growth:.2f}%")
    print(f"当前净值: {current_net_value:.4f}")
    print(f"峰值净值: {peak_net_value:.4f}")
    print(f"净值回撤: {net_value_drawdown:.2f}%")
    
    print("\n=== 仓位控制计算 ===")
    
    # 条件①检查
    condition1 = asset_growth <= 5 or net_value_drawdown <= -6
    print(f"条件① (资产增长<=5% 或 回撤<=-6%): {condition1}")
    if condition1:
        print("  → 触发条件①，仓位控制 = 40%")
        return
    
    # 条件②检查
    condition2 = (asset_growth * 3 + 40) > 100 and net_value_drawdown > -2
    print(f"条件② ((资产增长*3+40)>100% 且 回撤>-2%): {condition2}")
    print(f"  资产增长*3+40 = {asset_growth * 3 + 40:.1f}%")
    print(f"  净值回撤 > -2%: {net_value_drawdown > -2}")
    if condition2:
        print("  → 触发条件②，仓位控制 = 100%")
        return
    
    # 条件③计算
    position_from_growth = asset_growth * 3 + 40
    position_from_drawdown = (net_value_drawdown + 2) * 15 + 100
    
    print(f"\n条件③计算:")
    print(f"  增长方: 资产增长*3+40 = {asset_growth:.2f} * 3 + 40 = {position_from_growth:.1f}%")
    print(f"  回撤方: (净值回撤+2)*15+100 = ({net_value_drawdown:.2f}+2)*15+100 = {position_from_drawdown:.1f}%")
    
    max_position = min(position_from_growth, position_from_drawdown)
    max_position = max(0, min(100, max_position))
    
    print(f"  取最小值: min({position_from_growth:.1f}%, {position_from_drawdown:.1f}%) = {min(position_from_growth, position_from_drawdown):.1f}%")
    print(f"  限制范围后: {max_position:.1f}%")
    print(f"→ 最终仓位控制: {max_position:.1f}%")

if __name__ == "__main__":
    debug_position_control()
