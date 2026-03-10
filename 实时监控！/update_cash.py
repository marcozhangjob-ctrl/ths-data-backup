# 计算正确的现金余额
hkd_cny_rate = 0.92

# 初始资金
initial_cash = 50000000

# 第一次买入
buy1_cny = 2717390.48 * hkd_cny_rate

# 第二次买入 (修正后)
buy2_cny = 2744329.82 * hkd_cny_rate

# 计算剩余现金
remaining_cash = initial_cash - buy1_cny - buy2_cny

print("=== 现金余额计算 ===")
print(f"初始资金: {initial_cash:,.2f} CNY")
print(f"第一次买入: {buy1_cny:,.2f} CNY")
print(f"第二次买入: {buy2_cny:,.2f} CNY")
print(f"剩余现金: {remaining_cash:,.2f} CNY")
print()
print(f"当前记录现金: 45,000,001.75 CNY")
print(f"应调整为: {remaining_cash:,.2f} CNY")
print(f"差异: {remaining_cash - 45000001.75:.2f} CNY")
