# 验证加权平均成本计算
hkd_cny_rate = 0.92

# 两笔原始交易
# 3月6日买入
buy1_price = 1.16  # HKD
buy1_shares = 2342578
buy1_amount_hkd = buy1_shares * buy1_price
buy1_amount_cny = buy1_amount_hkd * hkd_cny_rate

# 3月9日买入  
buy2_price = 1.39  # HKD
buy2_shares = 1954957
buy2_amount_hkd = buy2_shares * buy2_price
buy2_amount_cny = buy2_amount_hkd * hkd_cny_rate

# 计算加权平均成本
total_shares = buy1_shares + buy2_shares
total_amount_hkd = buy1_amount_hkd + buy2_amount_hkd
weighted_avg_cost_hkd = total_amount_hkd / total_shares

print("=== 原始交易数据 ===")
print(f"3月6日: {buy1_shares:,}股 × {buy1_price} HKD = {buy1_amount_hkd:,.2f} HKD = {buy1_amount_cny:,.2f} CNY")
print(f"3月9日: {buy2_shares:,}股 × {buy2_price} HKD = {buy2_amount_hkd:,.2f} HKD = {buy2_amount_cny:,.2f} CNY")
print()
print(f"总股数: {total_shares:,}股")
print(f"总金额: {total_amount_hkd:,.2f} HKD")
print(f"加权平均成本: {weighted_avg_cost_hkd:.6f} HKD")

# 验证持仓记录中的数据
position_shares = 4297535
position_buy_price = 1.2646  # 当前记录的买入价格
position_buy_amount = position_shares * position_buy_price

print(f"\n=== 持仓记录验证 ===")
print(f"持仓股数: {position_shares:,}股")
print(f"记录买入价: {position_buy_price:.6f} HKD")
print(f"记录买入金额: {position_buy_amount:,.2f} HKD")
print(f"计算买入金额: {total_amount_hkd:,.2f} HKD")
print(f"差异: {abs(position_buy_amount - total_amount_hkd):,.2f} HKD")

# 当前市值和收益
current_price = 1.19  # HKD
current_market_value_hkd = position_shares * current_price
current_market_value_cny = current_market_value_hkd * hkd_cny_rate

position_cost_hkd = position_shares * position_buy_price
position_cost_cny = position_cost_hkd * hkd_cny_rate

position_change_hkd = current_market_value_hkd - position_cost_hkd
position_change_cny = current_market_value_cny - position_cost_cny

print(f"\n=== 当前持仓收益 ===")
print(f"当前价格: {current_price} HKD")
print(f"当前市值: {current_market_value_hkd:,.2f} HKD = {current_market_value_cny:,.2f} CNY")
print(f"持仓成本: {position_cost_hkd:,.2f} HKD = {position_cost_cny:,.2f} CNY")
print(f"持仓收益: {position_change_hkd:,.2f} HKD = {position_change_cny:,.2f} CNY")
print(f"收益率: {position_change_cny / position_cost_cny * 100:.2f}%")

# 资产变动验证
initial_cash = 50000000
current_cash = 45000001.7468
total_assets = current_cash + current_market_value_cny
asset_change = total_assets - initial_cash

print(f"\n=== 资产变动验证 ===")
print(f"初始资金: {initial_cash:,} CNY")
print(f"当前现金: {current_cash:,.2f} CNY")
print(f"股票市值: {current_market_value_cny:,.2f} CNY")
print(f"总资产: {total_assets:,.2f} CNY")
print(f"资产变动: {asset_change:,.2f} CNY")

# 实际投入vs回报
actual_invested_cny = buy1_amount_cny + buy2_amount_cny
investment_return_cny = current_market_value_cny - actual_invested_cny

print(f"\n=== 实际投资回报 ===")
print(f"实际投入: {actual_invested_cny:,.2f} CNY")
print(f"当前价值: {current_market_value_cny:,.2f} CNY")
print(f"投资回报: {investment_return_cny:,.2f} CNY")
print(f"与资产变动差异: {abs(asset_change - investment_return_cny):,.2f} CNY")
