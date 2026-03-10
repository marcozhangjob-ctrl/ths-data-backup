# 最终验证修正后的数据
hkd_cny_rate = 0.92

print("=== 修正后的最终验证 ===")

# 修正后的交易记录
buy1_shares = 2342578
buy1_price = 1.16
buy1_amount_hkd = 2342578 * 1.16

buy2_shares = 1974338
buy2_price = 1.39
buy2_amount_hkd = 1974338 * 1.39

# 持仓记录
position_shares = 4316916
position_buy_price = 1.265190
position_buy_amount = 5461720.30

print("交易记录:")
print(f"  3月6日: {buy1_shares:,}股 × {buy1_price} = {buy1_amount_hkd:,.2f} HKD")
print(f"  3月9日: {buy2_shares:,}股 × {buy2_price} = {buy2_amount_hkd:,.2f} HKD")
print(f"  合计: {buy1_shares + buy2_shares:,}股 × {(buy1_amount_hkd + buy2_amount_hkd)/(buy1_shares + buy2_shares):.6f} = {buy1_amount_hkd + buy2_amount_hkd:,.2f} HKD")

print("\n持仓记录:")
print(f"  记录: {position_shares:,}股 × {position_buy_price:.6f} = {position_buy_amount:,.2f} HKD")

print("\n验证:")
print(f"  股数匹配: {position_shares == buy1_shares + buy2_shares}")
print(f"  金额匹配: {abs(position_buy_amount - (buy1_amount_hkd + buy2_amount_hkd)) < 0.01}")
print(f"  成本匹配: {abs(position_buy_price - (buy1_amount_hkd + buy2_amount_hkd)/(buy1_shares + buy2_shares)) < 0.000001}")

# 现金验证
initial_cash = 50000000
buy1_cny = buy1_amount_hkd * hkd_cny_rate
buy2_cny = buy2_amount_hkd * hkd_cny_rate
expected_cash = initial_cash - buy1_cny - buy2_cny
actual_cash = 44975217.32

print(f"\n现金验证:")
print(f"  初始资金: {initial_cash:,.2f} CNY")
print(f"  第一次支出: {buy1_cny:,.2f} CNY")
print(f"  第二次支出: {buy2_cny:,.2f} CNY")
print(f"  应剩余现金: {expected_cash:,.2f} CNY")
print(f"  记录现金: {actual_cash:,.2f} CNY")
print(f"  现金匹配: {abs(expected_cash - actual_cash) < 0.01}")

# 当前收益计算
current_price = 1.19
current_market_value_hkd = position_shares * current_price
current_market_value_cny = current_market_value_hkd * hkd_cny_rate

position_cost_hkd = position_shares * position_buy_price
position_cost_cny = position_cost_hkd * hkd_cny_rate

position_change_cny = current_market_value_cny - position_cost_cny

# 资产变动
total_assets = actual_cash + current_market_value_cny
asset_change = total_assets - initial_cash

print(f"\n当前收益状况:")
print(f"  当前价格: {current_price} HKD")
print(f"  当前市值: {current_market_value_hkd:,.2f} HKD = {current_market_value_cny:,.2f} CNY")
print(f"  持仓成本: {position_cost_hkd:,.2f} HKD = {position_cost_cny:,.2f} CNY")
print(f"  持仓收益: {position_change_cny:,.2f} CNY ({position_change_cny/position_cost_cny*100:.2f}%)")
print(f"  总资产: {total_assets:,.2f} CNY")
print(f"  资产变动: {asset_change:,.2f} CNY ({asset_change/initial_cash*100:.2f}%)")
print(f"  收益一致性: {abs(position_change_cny - asset_change) < 1.0}")

print(f"\n✅ 关键改进:")
print(f"  ✓ 考虑了3月9日资产增长对第二次买入金额的影响")
print(f"  ✓ 第二次买入金额: {buy2_cny:,.2f} CNY > 第一次: {buy1_cny:,.2f} CNY")
print(f"  ✓ 加权平均成本更精确: {position_buy_price:.6f} HKD")
print(f"  ✓ 交易记录完整保留，持仓计算准确")
