# 分析当前的计算逻辑
hkd_cny_rate = 0.92

# 从API获取的实际数据
current_price = 1.19  # HKD
shares = 4297535
weighted_avg_cost = 1.1635  # HKD

# 当前市值计算
current_market_value_hkd = shares * current_price
current_market_value_cny = current_market_value_hkd * hkd_cny_rate

# 买入成本计算（按加权平均）
buy_cost_hkd = shares * weighted_avg_cost
buy_cost_cny = buy_cost_hkd * hkd_cny_rate

print("=== 持仓收益分析 ===")
print(f"当前价格: {current_price} HKD")
print(f"加权平均成本: {weighted_avg_cost} HKD")
print(f"持仓股数: {shares:,}股")
print()
print(f"当前市值: {current_market_value_hkd:,.2f} HKD = {current_market_value_cny:,.2f} CNY")
print(f"买入成本: {buy_cost_hkd:,.2f} HKD = {buy_cost_cny:,.2f} CNY")
print(f"持仓收益: {current_market_value_cny - buy_cost_cny:,.2f} CNY")

# 实际买入分析
print("\n=== 实际买入分析 ===")
# 第一次买入
buy1_shares = 2342578
buy1_price = 1.16
buy1_amount_hkd = buy1_shares * buy1_price
buy1_amount_cny = buy1_amount_hkd * hkd_cny_rate

# 第二次买入
buy2_shares = 1954957
buy2_price = 1.39
buy2_amount_hkd = buy2_shares * buy2_price
buy2_amount_cny = buy2_amount_hkd * hkd_cny_rate

print(f"第一次买入: {buy1_shares:,}股 × {buy1_price} HKD = {buy1_amount_hkd:,.2f} HKD = {buy1_amount_cny:,.2f} CNY")
print(f"第二次买入: {buy2_shares:,}股 × {buy2_price} HKD = {buy2_amount_hkd:,.2f} HKD = {buy2_amount_cny:,.2f} CNY")
print(f"总买入成本: {buy1_amount_hkd + buy2_amount_hkd:,.2f} HKD = {buy1_amount_cny + buy2_amount_cny:,.2f} CNY")

# 正确的加权平均成本验证
total_shares = buy1_shares + buy2_shares
total_amount_hkd = buy1_amount_hkd + buy2_amount_hkd
actual_avg_cost = total_amount_hkd / total_shares

print(f"\n=== 验证加权平均成本 ===")
print(f"实际加权平均成本: {actual_avg_cost:.4f} HKD")
print(f"记录的加权平均成本: {weighted_avg_cost} HKD")
print(f"差异: {abs(actual_avg_cost - weighted_avg_cost):.6f} HKD")

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

# 实际投入vs当前价值
actual_invested = buy1_amount_cny + buy2_amount_cny
current_value = current_market_value_cny
investment_return = current_value - actual_invested

print(f"\n=== 投资回报分析 ===")
print(f"实际投入: {actual_invested:,.2f} CNY")
print(f"当前价值: {current_value:,.2f} CNY")
print(f"投资回报: {investment_return:,.2f} CNY")
print(f"投资回报率: {investment_return / actual_invested * 100:.2f}%")
