#!/usr/bin/env python3
"""
Pokémon专家系统评测使用示例

展示如何使用评测系统进行不同类型的实验
"""

import asyncio
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append(str(Path(__file__).parent))

def example_quick_test():
    """示例：快速测试"""
    print("🚀 运行快速测试示例...")
    print("这将运行一个简化的评测，用于验证系统是否正常工作")
    
    # 这里可以调用实际的评测代码
    # 由于依赖问题，这里只展示调用方式
    print("调用方式: python run_evaluation.py --quick")
    print("预期输出格式:")
    print("""
**结果（占位）**：总体胜率为 **XX%**（95% CI [XX, XX]），各 tier（Uber、OU、UU、RU、NU、Random）的胜率见表 **X**。
**结果（占位）**：在对不同对手的测试中，平均对局时长为 **XX** 回合（中位数 **XX**），胜局时平均剩余 Pokémon 为 **XX** 只，平均剩余 HP 比例为 **XX%**。详细数据见表 **X**。
**结果（占位）**：跨 tier 胜率方差为 **XX**，最低 tier 胜率为 **XX%**；针对 baseline 的失败率为 **XX%**，主要失因包括 **XX**；在高随机性场景下，胜率从 **XX%** 降至 **XX%**，退化幅度 ΔWR = **XX%**。
""")

def example_custom_config():
    """示例：自定义配置"""
    print("\n🔧 自定义配置示例...")
    
    from experiment_config import CONFIG_MANAGER
    
    # 创建自定义配置
    custom_config = CONFIG_MANAGER.create_custom_config(
        experiment_name="我的自定义评测",
        matches_per_pair=30,
        enabled_tiers=["gen9ou", "gen9uu"],
        enabled_opponents=["RandomPlayer", "SimpleHeuristicsPlayer"]
    )
    
    # 保存配置
    config_file = "my_custom_config.json"
    CONFIG_MANAGER.save_config(custom_config, config_file)
    
    print(f"✅ 自定义配置已保存到: {config_file}")
    print(f"运行命令: python run_evaluation.py --custom {config_file}")

def example_result_analysis():
    """示例：结果分析"""
    print("\n📊 结果分析示例...")
    
    print("评测完成后，您可以：")
    print("1. 查看控制台输出的标准化结果")
    print("2. 检查 evaluation_results/metrics_summary.csv 获取详细数据")
    print("3. 查看 evaluation_results/figures/ 目录下的可视化图表")
    print("4. 阅读 evaluation_results/reports/evaluation_report.md 获取完整报告")
    
    print("\n示例数据分析代码:")
    print("""
import pandas as pd
import matplotlib.pyplot as plt

# 加载结果
df = pd.read_csv('evaluation_results/metrics_summary.csv')

# 胜率对比
plt.figure(figsize=(10, 6))
plt.bar(df['agent_name'], df['win_rate'])
plt.title('Agent胜率对比')
plt.ylabel('胜率')
plt.xticks(rotation=45)
plt.show()

# 规则强度分析
plt.figure(figsize=(10, 6))
plt.scatter(df['median_turns'], df['mean_remain_hp'])
plt.xlabel('中位数回合数')
plt.ylabel('平均剩余HP%')
plt.title('规则强度分析')
plt.show()
""")

def main():
    """主函数"""
    print("🎮 Pokémon专家系统评测系统使用示例")
    print("="*60)
    
    example_quick_test()
    example_custom_config()
    example_result_analysis()
    
    print("\n" + "="*60)
    print("📚 更多信息请查看 README_evaluation.md")
    print("🚀 开始评测: python run_evaluation.py --help")

if __name__ == "__main__":
    main()
