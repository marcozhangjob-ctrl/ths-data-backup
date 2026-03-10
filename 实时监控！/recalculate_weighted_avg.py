# 重新计算考虑资产增长的加权平均成本
hkd_cny_rate = 0.92

# 初始数据
initial_cash = 50000000  # CNY

# 3月6日第一次买入 (5%仓位)
buy1_ratio = 0.05  # 5%
buy1_planned_cny = initial_cash * buy1_ratio  # 2,500,000 CNY
buy1_planned_hkd = buy1_planned_cny / hkd_cny_rate  # 约2,717,391 HKD
buy1_price = 1.16  # HKD
buy1_shares = int(buy1_planned_hkd / buy1_price)  # 2,342,578股
buy1_actual_hkd = buy1_shares * buy1_price  # 2,717,390.48 HKD
buy1_actual_cny = buy1_actual_hkd * hkd_cny_rate

print("=== 3月6日第一次买入 ===")
print(f"计划投入: {buy1_planned_cny:,.2f} CNY = {buy1_planned_hkd:,.2f} HKD")
print(f"买入价格: {buy1_price} HKD")
print(f"可买股数: {buy1_shares:,}股")
print(f"实际成交: {buy1_shares:,}股 × {buy1_price} = {buy1_actual_hkd:,.2f} HKD = {buy1_actual_cny:,.2f} CNY")
print(f"剩余现金: {initial_cash - buy1_actual_cny:,.2f} CNY")

# 假设3月6日到3月9日期间，股价从1.16涨到某个价格，导致资产增长
# 我们需要计算3月9日的总资产（假设3月9日开盘价为X）

# 3月9日第二次买入 (也是5%仓位，但基于增长后的总资产)
# 关键问题：3月9日的5%是基于当时的总资产，不是初始资金

# 让我们反推：如果第二次买入也是2,500,000 CNY的计划金额
# 那么说明3月9日的总资产仍然是50,000,000 CNY左右
# 这意味着第一次买入后资产没有增长，或者增长被其他因素抵消

# 但实际上，第二次买入的价格是1.39 HKD，比第一次高
# 让我们计算如果第一次买入后股价涨到1.39，总资产会是多少

假设_3月9日股价 = 1.39  # HKD
buy1_value_at_139_hkd = buy1_shares * 假设_3月9日股价
buy1_value_at_139_cny = buy1_value_at_139_hkd * hkd_cny_rate
total_assets_at_139 = (initial_cash - buy1_actual_cny) + buy1_value_at_139_cny

print(f"\n=== 假设3月9日股价涨到1.39 HKD ===")
print(f"第一次买入持仓价值: {buy1_shares:,}股 × {假设_3月9日股价} = {buy1_value_at_139_hkd:,.2f} HKD = {buy1_value_at_139_cny:,.2f} CNY")
print(f"总资产: {initial_cash - buy1_actual_cny:,.2f} CNY (现金) + {buy1_value_at_139_cny:,.2f} CNY (股票) = {total_assets_at_139:,.2f} CNY")
print(f"资产增长: {total_assets_at_139 - initial_cash:,.2f} CNY ({(total_assets_at_139 - initial_cash) / initial_cash * 100:.2f}%)")

# 如果3月9日仍然按5%仓位买入
buy2_ratio = 0.05
buy2_planned_cny = total_assets_at_139 * buy2_ratio
buy2_planned_hkd = buy2_planned_cny / hkd_cny_rate
buy2_price = 1.39  # HKD
buy2_shares = int(buy2_planned_hkd / buy2_price)
buy2_actual_hkd = buy2_shares * buy2_price
buy2_actual_cny = buy2_actual_hkd * hkd_cny_rate

print(f"\n=== 3月9日第二次买入 (基于增长后总资产) ===")
print(f"当时总资产: {total_assets_at_139:,.2f} CNY")
print(f"计划投入: {buy2_planned_cny:,.2f} CNY = {buy2_planned_hkd:,.2f} HKD")
print(f"买入价格: {buy2_price} HKD")
print(f"可买股数: {buy2_shares:,}股")
print(f"实际成交: {buy2_shares:,}股 × {buy2_price} = {buy2_actual_hkd:,.2f} HKD = {buy2_actual_cny:,.2f} CNY")

# 重新计算加权平均成本
total_shares_corrected = buy1_shares + buy2_shares
total_amount_hkd_corrected = buy1_actual_hkd + buy2_actual_hkd
weighted_avg_cost_corrected = total_amount_hkd_corrected / total_shares_corrected

print(f"\n=== 修正后的加权平均成本 ===")
print(f"总股数: {total_shares_corrected:,}股")
print(f"总金额: {total_amount_hkd_corrected:,.2f} HKD")
print(f"修正后加权平均成本: {weighted_avg_cost_corrected:.6f} HKD")

# 与之前错误的计算对比
print(f"\n=== 对比分析 ===")
print(f"之前错误计算: 1.264627 HKD (假设两次投入金额相等)")
print(f"修正后计算: {weighted_avg_cost_corrected:.6f} HKD (考虑资产增长)")
print(f"差异: {weighted_avg_cost_corrected - 1.264627:.6f} HKD")
