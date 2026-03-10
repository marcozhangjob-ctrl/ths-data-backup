import json

# 读取数据
with open('portfolio_data.json', 'r', encoding='utf-8') as f:
    portfolio = json.load(f)

print('=== 当前持仓数据 ===')
for pos in portfolio['positions']:
    print(f'股票: {pos["name"]} ({pos["code"]})')
    print(f'买入价格: {pos["buyPrice"]} HKD')
    print(f'持仓股数: {pos["shares"]:,}股')
    print(f'买入成本: {pos["buyAmount"]:,.2f} HKD')
    print()

print('=== 组合概况 ===')
print(f'初始资金: {portfolio["initialCash"]:,} CNY')
print(f'当前现金: {portfolio["cash"]:,.2f} CNY')
print(f'股票买入成本: {sum(pos["buyAmount"] for pos in portfolio["positions"]):,.2f} HKD')

# 模拟当前价格计算（假设当前价格为1.40 HKD）
current_price_hkd = 1.40
hkd_cny_rate = 0.92

for pos in portfolio['positions']:
    current_market_value_hkd = pos['shares'] * current_price_hkd
    current_market_value_cny = current_market_value_hkd * hkd_cny_rate
    buy_cost_cny = pos['buyAmount'] * hkd_cny_rate
    
    print(f'\n=== {pos["name"]} 盈亏分析 ===')
    print(f'当前价格: {current_price_hkd} HKD')
    print(f'当前市值: {current_market_value_hkd:,.2f} HKD ({current_market_value_cny:,.2f} CNY)')
    print(f'买入成本: {pos["buyAmount"]:,.2f} HKD ({buy_cost_cny:,.2f} CNY)')
    print(f'价格变动收益: {current_market_value_cny - buy_cost_cny:,.2f} CNY')
    print(f'收益率: {(current_market_value_cny - buy_cost_cny) / buy_cost_cny * 100:.2f}%')

total_assets = portfolio['cash'] + sum(pos['shares'] * current_price_hkd * hkd_cny_rate for pos in portfolio['positions'])
asset_change = total_assets - portfolio['initialCash']
asset_growth = asset_change / portfolio['initialCash'] * 100

print(f'\n=== 总资产分析 ===')
print(f'总资产: {total_assets:,.2f} CNY')
print(f'资产变动: {asset_change:,.2f} CNY')
print(f'资产增长率: {asset_growth:.2f}%')
