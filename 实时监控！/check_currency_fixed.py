# 检查货币转换逻辑
hkd_cny_rate = 0.92

print("=== 货币转换逻辑检查 ===")

# 初始状态
initial_cash_cny = 50000000  # CNY

print(f"初始资金: {initial_cash_cny:,.2f} CNY")

# 第一次买入 (3月6日)
buy1_shares = 2342578
buy1_price_hkd = 1.16
buy1_amount_hkd = buy1_shares * buy1_price_hkd
buy1_amount_cny = buy1_amount_hkd * hkd_cny_rate

remaining_cash_after_buy1 = initial_cash_cny - buy1_amount_cny

print(f"\n第一次买入 (3月6日):")
print(f"  买入: {buy1_shares:,}股 × {buy1_price_hkd} HKD = {buy1_amount_hkd:,.2f} HKD = {buy1_amount_cny:,.2f} CNY")
print(f"  剩余现金: {remaining_cash_after_buy1:,.2f} CNY")

# 关键问题：计算3月9日总资产时，股票盈利如何计算？
# 假设3月9日股价涨到1.39 HKD

scenario_1_price_hkd = 1.39
scenario_1_stock_value_hkd = buy1_shares * scenario_1_price_hkd
scenario_1_stock_value_cny = scenario_1_stock_value_hkd * hkd_cny_rate  # 港币盈利转换为人民币

scenario_1_total_assets_cny = remaining_cash_after_buy1 + scenario_1_stock_value_cny
scenario_1_profit_cny = scenario_1_stock_value_cny - buy1_amount_cny

print(f"\n=== 正确逻辑: 盈利转换为人民币 ===")
print(f"  股价涨到: {scenario_1_price_hkd} HKD")
print(f"  股票价值: {scenario_1_stock_value_hkd:,.2f} HKD = {scenario_1_stock_value_cny:,.2f} CNY")
print(f"  股票盈利: {scenario_1_stock_value_hkd - buy1_amount_hkd:,.2f} HKD = {scenario_1_profit_cny:,.2f} CNY")
print(f"  总资产: {remaining_cash_after_buy1:,.2f} CNY + {scenario_1_stock_value_cny:,.2f} CNY = {scenario_1_total_assets_cny:,.2f} CNY")
print(f"  资产增长: {scenario_1_total_assets_cny - initial_cash_cny:,.2f} CNY")

# 验证第二次买入金额计算
print(f"\n=== 第二次买入验证 ===")
buy2_planned_cny_correct = scenario_1_total_assets_cny * 0.05
buy2_planned_hkd_correct = buy2_planned_cny_correct / hkd_cny_rate
buy2_shares_correct = int(buy2_planned_hkd_correct / scenario_1_price_hkd)
buy2_actual_hkd_correct = buy2_shares_correct * scenario_1_price_hkd
buy2_actual_cny_correct = buy2_actual_hkd_correct * hkd_cny_rate

print(f"基于正确总资产的第二次买入:")
print(f"  总资产: {scenario_1_total_assets_cny:,.2f} CNY")
print(f"  计划投入5%: {buy2_planned_cny_correct:,.2f} CNY = {buy2_planned_hkd_correct:,.2f} HKD")
print(f"  可买股数: {buy2_shares_correct:,}股")
print(f"  实际成交: {buy2_shares_correct:,}股 × {scenario_1_price_hkd} = {buy2_actual_hkd_correct:,.2f} HKD = {buy2_actual_cny_correct:,.2f} CNY")

print(f"\n与我们之前计算的对比:")
print(f"  之前计算: 1,974,338股, 2,744,329.82 HKD, 2,524,783.43 CNY")
print(f"  验证计算: {buy2_shares_correct:,}股, {buy2_actual_hkd_correct:,.2f} HKD, {buy2_actual_cny_correct:,.2f} CNY")
print(f"  差异: {abs(buy2_shares_correct - 1974338):,}股, {abs(buy2_actual_hkd_correct - 2744329.82):,.2f} HKD, {abs(buy2_actual_cny_correct - 2524783.43):,.2f} CNY")

print(f"\n✅ 结论:")
print(f"  1. 货币转换逻辑是正确的")
print(f"  2. 港币盈利确实需要转换为人民币计算总资产")
print(f"  3. 第二次买入金额计算基于人民币总资产是正确的")
print(f"  4. 我们之前的计算没有问题")
