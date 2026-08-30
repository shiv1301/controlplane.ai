import matplotlib.pyplot as plt
import numpy as np

# Set dark theme styling
plt.style.use('dark_background')
fig = plt.figure(figsize=(16, 9), facecolor='#0f172a')
fig.suptitle('ControlPlane.ai vs Baseline LLM\nBenchmark Report (1,000 Interactions)', 
             fontsize=28, color='#38bdf8', fontweight='bold', y=0.95)

# 1. Cost Comparison
ax1 = plt.subplot(231, facecolor='#1e293b')
bars = ax1.bar(['Baseline', 'ControlPlane'], [0.0677, 0.0001], color=['#ef4444', '#10b981'])
ax1.set_title('Inference Cost ($)', color='white', fontsize=16, pad=15)
ax1.tick_params(colors='gray', labelsize=12)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.spines['bottom'].set_color('#475569')
ax1.spines['left'].set_color('#475569')
for bar in bars:
    yval = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2, yval, f'\', ha='center', va='bottom', color='white', fontweight='bold', fontsize=12)

# 2. Token Consumption
ax2 = plt.subplot(232, facecolor='#1e293b')
bars2 = ax2.bar(['Baseline', 'ControlPlane'], [4745, 346], color=['#f59e0b', '#3b82f6'])
ax2.set_title('Token Consumption', color='white', fontsize=16, pad=15)
ax2.tick_params(colors='gray', labelsize=12)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.spines['bottom'].set_color('#475569')
ax2.spines['left'].set_color('#475569')
for bar in bars2:
    yval = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2, yval, f'{yval}', ha='center', va='bottom', color='white', fontweight='bold', fontsize=12)

# 3. Big Metric 1
ax3 = plt.subplot(233, facecolor='#1e293b')
ax3.axis('off')
ax3.text(0.5, 0.7, '99.9%', ha='center', va='center', color='#10b981', fontsize=48, fontweight='bold')
ax3.text(0.5, 0.4, 'Cost Reduction', ha='center', va='center', color='white', fontsize=20)
ax3.text(0.5, 0.2, 'via Semantic Cache & Routing', ha='center', va='center', color='gray', fontsize=12)

# 4. Big Metric 2
ax4 = plt.subplot(234, facecolor='#1e293b')
ax4.axis('off')
ax4.text(0.5, 0.7, '100%', ha='center', va='center', color='#8b5cf6', fontsize=48, fontweight='bold')
ax4.text(0.5, 0.4, 'Safety Block Rate', ha='center', va='center', color='white', fontsize=20)
ax4.text(0.5, 0.2, 'Zero-shot injection detection', ha='center', va='center', color='gray', fontsize=12)

# 5. Big Metric 3
ax5 = plt.subplot(235, facecolor='#1e293b')
ax5.axis('off')
ax5.text(0.5, 0.7, '0.00s', ha='center', va='center', color='#0ea5e9', fontsize=48, fontweight='bold')
ax5.text(0.5, 0.4, 'Cache Latency', ha='center', va='center', color='white', fontsize=20)
ax5.text(0.5, 0.2, 'Instant response for repeated queries', ha='center', va='center', color='gray', fontsize=12)

# 6. Big Metric 4
ax6 = plt.subplot(236, facecolor='#1e293b')
ax6.axis('off')
ax6.text(0.5, 0.7, '\,144', ha='center', va='center', color='#10b981', fontsize=48, fontweight='bold')
ax6.text(0.5, 0.4, 'Annual Savings', ha='center', va='center', color='white', fontsize=20)
ax6.text(0.5, 0.2, 'Projected at 1M conversations/mo', ha='center', va='center', color='gray', fontsize=12)

plt.tight_layout(pad=4.0)
plt.subplots_adjust(top=0.85)
plt.savefig('business_dashboard.png', dpi=300, bbox_inches='tight', facecolor='#0f172a')

