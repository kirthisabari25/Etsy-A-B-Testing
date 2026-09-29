import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import os

# Set style
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['figure.dpi'] = 300

os.makedirs('charts', exist_ok=True)

ass = pd.read_csv(r'checkout-redesign-ab-test-datasets/checkout-redesign-ab-test/assignments.csv')
ord_df = pd.read_csv(r'checkout-redesign-ab-test-datasets/checkout-redesign-ab-test/orders.csv')

ass['assigned_at'] = pd.to_datetime(ass['assigned_at'])
ord_df['ordered_at'] = pd.to_datetime(ord_df['ordered_at'])

# Sort & Filter
ass_sorted = ass.sort_values(['user_id', 'assigned_at'])
v_counts = ass.groupby('user_id')['variant'].nunique()
mixed_users = set(v_counts[v_counts > 1].index)

clean_users_df = ass_sorted[~ass_sorted['user_id'].isin(mixed_users)].groupby('user_id').first().reset_index()
clean_orders = ord_df.merge(clean_users_df[['user_id', 'variant', 'assigned_at']], on='user_id', how='inner')
valid_orders = clean_orders[clean_orders['ordered_at'] >= clean_orders['assigned_at']].copy()

user_orders = valid_orders.groupby('user_id').agg(
    n_orders=('order_id', 'count'),
    total_revenue=('order_value', 'sum')
).reset_index()

df = clean_users_df.merge(user_orders, on='user_id', how='left')
df['n_orders'] = df['n_orders'].fillna(0).astype(int)
df['total_revenue'] = df['total_revenue'].fillna(0.0)
df['converted'] = (df['n_orders'] > 0).astype(int)

# --- CHART 1: Conversion Rate by Device ---
fig, ax = plt.subplots(figsize=(9, 5.5))
devices = ['desktop', 'mobile', 'tablet']
x = np.arange(len(devices))
width = 0.35

c_rates, t_rates = [], []
c_cis, t_cis = [], []

for dev in devices:
    sub = df[df['device'] == dev]
    c_sub = sub[sub['variant'] == 'control']
    t_sub = sub[sub['variant'] == 'treatment']
    
    cr_c = c_sub['converted'].mean()
    cr_t = t_sub['converted'].mean()
    
    ci_c = 1.96 * np.sqrt(cr_c * (1 - cr_c) / len(c_sub))
    ci_t = 1.96 * np.sqrt(cr_t * (1 - cr_t) / len(t_sub))
    
    c_rates.append(cr_c * 100)
    t_rates.append(cr_t * 100)
    c_cis.append(ci_c * 100)
    t_cis.append(ci_t * 100)

rects1 = ax.bar(x - width/2, c_rates, width, yerr=c_cis, label='Control (Old Checkout)', color='#4A5568', capsize=5, edgecolor='black', alpha=0.9)
rects2 = ax.bar(x + width/2, t_rates, width, yerr=t_cis, label='Treatment (New Checkout)', color='#DD6B20', capsize=5, edgecolor='black', alpha=0.9)

ax.set_ylabel('Conversion Rate (%)', fontsize=12, fontweight='bold')
ax.set_title('Checkout Conversion Rate by Device (Control vs. Treatment)', fontsize=14, fontweight='bold', pad=15)
ax.set_xticks(x)
ax.set_xticklabels(['Desktop\n(n=14,998)', 'Mobile\n(n=13,211)', 'Tablet\n(n=2,507)'], fontsize=11)
ax.legend(frameon=True, facecolor='white', edgecolor='none', fontsize=11)
ax.set_ylim(0, 14)

# Value annotations
for rect in rects1:
    h = rect.get_height()
    ax.annotate(f'{h:.2f}%', xy=(rect.get_x() + rect.get_width()/2, h + 0.6), xytext=(0, 3),
                textcoords="offset points", ha='center', va='bottom', fontsize=10, fontweight='bold')

for rect in rects2:
    h = rect.get_height()
    ax.annotate(f'{h:.2f}%', xy=(rect.get_x() + rect.get_width()/2, h + 0.6), xytext=(0, 3),
                textcoords="offset points", ha='center', va='bottom', fontsize=10, fontweight='bold', color='#C05621')

# Add statistical annotations
ax.annotate('*** (+34.3% Rel, p<0.001)', xy=(0, 11.5), ha='center', fontsize=10, fontweight='bold', color='#2B6CB0')
ax.annotate('*** (-23.0% Rel, p<0.001)', xy=(1, 8.5), ha='center', fontsize=10, fontweight='bold', color='#C53030')
ax.annotate('NS (-22.9% Rel, p=0.106)', xy=(2, 8.0), ha='center', fontsize=10, fontweight='bold', color='#718096')

plt.tight_layout()
plt.savefig('charts/conversion_rate_by_device.png', dpi=300)
plt.close()

# --- CHART 2: Conversion Rate by Segment Matrix (Device x Visitor Type) ---
segments = [
    ('Desktop - New', 'desktop', 'new'),
    ('Desktop - Returning', 'desktop', 'returning'),
    ('Mobile - New', 'mobile', 'new'),
    ('Mobile - Returning', 'mobile', 'returning'),
    ('Tablet - New', 'tablet', 'new'),
    ('Tablet - Returning', 'tablet', 'returning')
]

seg_names = [s[0] for s in segments]
diffs = []
p_vals = []
ci_lows_list = []
ci_highs_list = []

for name, dev, vtype in segments:
    sub = df[(df['device'] == dev) & (df['visitor_type'] == vtype)]
    c_sub = sub[sub['variant'] == 'control']
    t_sub = sub[sub['variant'] == 'treatment']
    
    cr_c = c_sub['converted'].mean()
    cr_t = t_sub['converted'].mean()
    diff = (cr_t - cr_c) * 100
    
    se = np.sqrt(cr_c*(1-cr_c)/len(c_sub) + cr_t*(1-cr_t)/len(t_sub))
    z = (cr_t - cr_c) / se
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    
    diffs.append(diff)
    p_vals.append(p)
    ci_lows_list.append(diff - 1.96 * se * 100)
    ci_highs_list.append(diff + 1.96 * se * 100)

fig, ax = plt.subplots(figsize=(9, 5.5))
y_pos = np.arange(len(seg_names))
colors = ['#2B6CB0' if d > 0 and p < 0.05 else ('#C53030' if d < 0 and p < 0.05 else '#A0AEC0') for d, p in zip(diffs, p_vals)]

errors = [np.array(diffs) - np.array(ci_lows_list), np.array(ci_highs_list) - np.array(diffs)]

ax.barh(y_pos, diffs, xerr=errors, align='center', color=colors, alpha=0.85, edgecolor='black', capsize=4)
ax.axvline(0, color='black', linestyle='--', linewidth=1)

ax.set_yticks(y_pos)
ax.set_yticklabels(seg_names, fontsize=11, fontweight='bold')
ax.invert_yaxis()
ax.set_xlabel('Absolute Conversion Rate Lift (Percentage Points)', fontsize=12, fontweight='bold')
ax.set_title('Absolute Lift by Device & Visitor Type Segment (95% CI)', fontsize=14, fontweight='bold', pad=15)

for i, (d, p) in enumerate(zip(diffs, p_vals)):
    sig_str = " (p<0.001)" if p < 0.001 else f" (p={p:.3f})"
    txt = f"{d:+.2f} pp{sig_str}"
    x_pos = d + (0.4 if d >= 0 else -0.4)
    ha = 'left' if d >= 0 else 'right'
    ax.annotate(txt, xy=(x_pos, i), va='center', ha=ha, fontsize=9.5, fontweight='bold', color=colors[i])

ax.set_xlim(-5.0, 6.5)
plt.tight_layout()
plt.savefig('charts/segment_conversion_matrix.png', dpi=300)
plt.close()

# --- CHART 3: Financial Revenue Impact Scenarios ---
scenarios = ['Full Launch\n(All Devices)', 'Phased Launch\n(Desktop Only)', 'Mobile Redesign\nLoss']
expected_impact = [12612.01, 28455.00, -13314.11]
ci_lows_scen = [-1888.67, 17508.56, -22038.14]
ci_highs_scen = [27112.70, 39401.45, -4590.08]

fig, ax = plt.subplots(figsize=(8.5, 5.5))
x_scen = np.arange(len(scenarios))
colors_scen = ['#DD6B20', '#2B6CB0', '#C53030']

errors_scen = [np.array(expected_impact) - np.array(ci_lows_scen), np.array(ci_highs_scen) - np.array(expected_impact)]

bars = ax.bar(x_scen, expected_impact, yerr=errors_scen, color=colors_scen, alpha=0.85, edgecolor='black', capsize=6, width=0.45)
ax.axhline(0, color='black', linestyle='-', linewidth=1.2)

ax.set_ylabel('Estimated Monthly Revenue Delta ($)', fontsize=12, fontweight='bold')
ax.set_title('Estimated Monthly Revenue Impact by Rollout Strategy\n(Test Cohort Scale: ~30.7k Monthly Users)', fontsize=13, fontweight='bold', pad=15)
ax.set_xticks(x_scen)
ax.set_xticklabels(scenarios, fontsize=11, fontweight='bold')

for bar, exp, low, high in zip(bars, expected_impact, ci_lows_scen, ci_highs_scen):
    h = bar.get_height()
    y_pos = high + 2000 if h >= 0 else low - 4500
    va = 'bottom' if h >= 0 else 'top'
    ax.annotate(f'${exp:+,.0f}\n[${low:+,.0f}, ${high:+,.0f}]', 
                xy=(bar.get_x() + bar.get_width()/2, y_pos),
                ha='center', va=va, fontsize=10, fontweight='bold')

ax.set_ylim(-32000, 48000)
plt.tight_layout()
plt.savefig('charts/revenue_impact_scenarios.png', dpi=300)
plt.close()

print("All charts generated successfully in 'charts/' directory!")
