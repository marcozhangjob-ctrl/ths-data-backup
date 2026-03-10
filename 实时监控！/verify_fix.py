# 验证修正后的计算
hkd_cny_rate = 0.92

# 修正后的数据
current_price = 1.19  # HKD
shares = 4297535
corrected_avg_cost = 1.2646  # HKD

# 当前市值计算
current_market_value_hkd = shares * current_price
current_market_value_cny = current_market_value_hkd * hkd_cny_rate

# 修正后买入成本计算
buy_cost_hkd = shares * corrected_avg_cost
buy_cost_cny = buy_cost_hkd * hkd_cny_rate

print("=== 修正后的持仓收益分析 ===")
print(f"当前价格: {current_price} HKD")
print(f"修正后加权平均成本: {corrected_avg_cost} HKD")
print(f"持仓股数: {shares:,}股")
print()
print(f"当前市值: {current_market_value_hkd:,.2f} HKD = {current_market_value_cny:,.2f} CNY")
print(f"买入成本: {buy_cost_hkd:,.2f} HKD = {buy_cost_cny:,.2f} CNY")
print(f"持仓收益: {current_market_value_cny - buy_cost_cny:,.2f} CNY")
print(f"收益率: {(current_market_value_cny - buy_cost_cny) / buy_cost_cny * 100:.2f}%")

# 资产变动分析
initial_cash = 50000000
current_cash = 45000001.7468
total_assets = current_cash + current_market_value_cny
asset_change = total_assets - initial_cash

print(f"\n=== 资产变动分析 ===")
print(f"初始资金: {initial_cash:,} CNY")
print(f"当前现金: {current_cash:,.2f} CNY")
print(f"当前股票市值: {current_market_value_cny:,.2f} CNY")
print(f"总资产: {total_assets:,.2f} CNY")
print(f"资产变动: {asset_change:,.2f} CNY")

# 验证一致性
actual_invested = 5434780.71 * hkd_cny_rate  # 实际投入
investment_return = current_market_value_cny - actual_invested

print(f"\n=== 一致性验证 ===")
print(f"实际投入: {actual_invested:,.2f} CNY")
print(f"当前价值: {current_market_value_cny:,.2f} CNY")
print(f"投资回报: {investment_return:,.2f} CNY")
print(f"与资产变动差异: {abs(asset_change - investment_return):,.2f} CNY")
