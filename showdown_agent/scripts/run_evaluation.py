#!/usr/bin/env python3
"""
Pokémon专家系统评测运行脚本

提供简单的命令行接口来运行不同类型的评测实验
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append(str(Path(__file__).parent))

from comprehensive_evaluation import ExperimentRunner, ExperimentConfig
from experiment_config import CONFIG_MANAGER, QUICK_CONFIG, DEFAULT_CONFIG, COMPREHENSIVE_CONFIG, STABILITY_CONFIG

def run_quick_evaluation():
    """运行快速评测（用于测试）"""
    print("🚀 启动快速评测...")
    print(f"配置: {QUICK_CONFIG.matches_per_pair} 局/配对, {len(QUICK_CONFIG.enabled_tiers)} 个tier")
    
    # 创建自定义配置
    config = ExperimentConfig()
    config.matches_per_pair = QUICK_CONFIG.matches_per_pair
    config.tiers = QUICK_CONFIG.enabled_tiers
    config.seeds = list(range(1000, 1000 + QUICK_CONFIG.seeds_count))
    config.max_turns = QUICK_CONFIG.max_turns
    config.results_dir = Path(QUICK_CONFIG.results_dir)
    
    runner = ExperimentRunner(config)
    asyncio.run(runner.run_evaluation())

def run_default_evaluation():
    """运行默认评测"""
    print("🚀 启动默认评测...")
    print(f"配置: {DEFAULT_CONFIG.matches_per_pair} 局/配对, {len(DEFAULT_CONFIG.enabled_tiers)} 个tier")
    
    config = ExperimentConfig()
    config.matches_per_pair = DEFAULT_CONFIG.matches_per_pair
    config.tiers = DEFAULT_CONFIG.enabled_tiers
    config.seeds = list(range(1000, 1000 + DEFAULT_CONFIG.seeds_count))
    config.max_turns = DEFAULT_CONFIG.max_turns
    config.results_dir = Path(DEFAULT_CONFIG.results_dir)
    
    runner = ExperimentRunner(config)
    asyncio.run(runner.run_evaluation())

def run_comprehensive_evaluation():
    """运行全面评测"""
    print("🚀 启动全面评测...")
    print(f"配置: {COMPREHENSIVE_CONFIG.matches_per_pair} 局/配对, {len(COMPREHENSIVE_CONFIG.enabled_tiers)} 个tier")
    print("⚠️  注意：全面评测可能需要较长时间")
    
    config = ExperimentConfig()
    config.matches_per_pair = COMPREHENSIVE_CONFIG.matches_per_pair
    config.tiers = COMPREHENSIVE_CONFIG.enabled_tiers
    config.seeds = list(range(1000, 1000 + COMPREHENSIVE_CONFIG.seeds_count))
    config.max_turns = COMPREHENSIVE_CONFIG.max_turns
    config.results_dir = Path(COMPREHENSIVE_CONFIG.results_dir)
    
    runner = ExperimentRunner(config)
    asyncio.run(runner.run_evaluation())

def run_stability_test():
    """运行稳定性测试"""
    print("🚀 启动稳定性测试...")
    print(f"配置: {STABILITY_CONFIG.matches_per_pair} 局/配对, 专注于稳定性指标")
    
    config = ExperimentConfig()
    config.matches_per_pair = STABILITY_CONFIG.matches_per_pair
    config.tiers = STABILITY_CONFIG.enabled_tiers
    config.seeds = list(range(1000, 1000 + STABILITY_CONFIG.seeds_count))
    config.max_turns = STABILITY_CONFIG.max_turns
    config.results_dir = Path(STABILITY_CONFIG.results_dir)
    
    runner = ExperimentRunner(config)
    asyncio.run(runner.run_evaluation())

def run_custom_evaluation(config_file: str):
    """运行自定义配置评测"""
    print(f"🚀 启动自定义评测: {config_file}")
    
    try:
        custom_config = CONFIG_MANAGER.load_config(config_file)
        print(f"配置: {custom_config.matches_per_pair} 局/配对, {len(custom_config.enabled_tiers)} 个tier")
        
        # 验证配置
        errors = CONFIG_MANAGER.validate_config(custom_config)
        if errors:
            print("❌ 配置错误:")
            for error in errors:
                print(f"  - {error}")
            return
        
        config = ExperimentConfig()
        config.matches_per_pair = custom_config.matches_per_pair
        config.tiers = custom_config.enabled_tiers
        config.seeds = list(range(1000, 1000 + custom_config.seeds_count))
        config.max_turns = custom_config.max_turns
        config.results_dir = Path(custom_config.results_dir)
        
        runner = ExperimentRunner(config)
        asyncio.run(runner.run_evaluation())
        
    except FileNotFoundError:
        print(f"❌ 配置文件不存在: {config_file}")
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")

def create_custom_config():
    """交互式创建自定义配置"""
    print("🔧 创建自定义评测配置")
    
    experiment_name = input("实验名称: ").strip() or "Custom Evaluation"
    matches_per_pair = int(input("每对对战次数 (默认20): ") or "20")
    
    print("\n可用的Tier:")
    for i, (tier, info) in enumerate(CONFIG_MANAGER.tiers.items(), 1):
        print(f"{i}. {tier} - {info.description}")
    
    tier_input = input("选择tier (用逗号分隔，如: 1,2,3): ").strip()
    if tier_input:
        tier_indices = [int(x.strip()) - 1 for x in tier_input.split(",")]
        enabled_tiers = [list(CONFIG_MANAGER.tiers.keys())[i] for i in tier_indices]
    else:
        enabled_tiers = ["gen9ou", "gen9randombattle"]
    
    print("\n可用的对手:")
    for i, (opponent, info) in enumerate(CONFIG_MANAGER.opponents.items(), 1):
        print(f"{i}. {opponent} - {info.description}")
    
    opponent_input = input("选择对手 (用逗号分隔，如: 1,2,3): ").strip()
    if opponent_input:
        opponent_indices = [int(x.strip()) - 1 for x in opponent_input.split(",")]
        enabled_opponents = [list(CONFIG_MANAGER.opponents.keys())[i] for i in opponent_indices]
    else:
        enabled_opponents = ["RandomPlayer", "MaxBasePowerPlayer"]
    
    # 创建配置
    custom_config = CONFIG_MANAGER.create_custom_config(
        experiment_name=experiment_name,
        matches_per_pair=matches_per_pair,
        enabled_tiers=enabled_tiers,
        enabled_opponents=enabled_opponents
    )
    
    # 保存配置
    config_file = f"{experiment_name.lower().replace(' ', '_')}_config.json"
    CONFIG_MANAGER.save_config(custom_config, config_file)
    
    print(f"✅ 配置已保存到: {config_file}")
    print(f"运行命令: python run_evaluation.py --custom {config_file}")

def show_help():
    """显示帮助信息"""
    print("""
🎮 Pokémon专家系统评测工具

使用方法:
  python run_evaluation.py [选项]

选项:
  --quick              快速评测 (5局/配对, 用于测试)
  --default            默认评测 (20局/配对, 推荐)
  --comprehensive      全面评测 (50局/配对, 所有tier)
  --stability          稳定性测试 (100局/配对, 专注稳定性)
  --custom <文件>      自定义配置评测
  --create-config      交互式创建自定义配置
  --help               显示此帮助信息

示例:
  python run_evaluation.py --quick                    # 快速测试
  python run_evaluation.py --default                  # 标准评测
  python run_evaluation.py --create-config            # 创建自定义配置
  python run_evaluation.py --custom my_config.json    # 使用自定义配置

评测指标:
  1. 胜率 (Win Rate) - 直接对战效果
  2. 规则强度 (Strategy Strength) - 战术压制力与收尾效率
  3. 稳定性 (Stability) - 鲁棒性与泛化能力

输出文件:
  - evaluation_results/metrics_summary.csv     # 指标汇总
  - evaluation_results/figures/                # 可视化图表
  - evaluation_results/reports/                # 详细报告
  - evaluation_results/logs/                   # 对战日志
""")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Pokémon专家系统评测工具")
    parser.add_argument("--quick", action="store_true", help="快速评测")
    parser.add_argument("--default", action="store_true", help="默认评测")
    parser.add_argument("--comprehensive", action="store_true", help="全面评测")
    parser.add_argument("--stability", action="store_true", help="稳定性测试")
    parser.add_argument("--custom", type=str, help="自定义配置文件")
    parser.add_argument("--create-config", action="store_true", help="创建自定义配置")
    parser.add_argument("--help-detailed", action="store_true", help="显示详细帮助")
    
    args = parser.parse_args()
    
    if args.help_detailed:
        show_help()
        return
    
    if args.create_config:
        create_custom_config()
        return
    
    if args.quick:
        run_quick_evaluation()
    elif args.default:
        run_default_evaluation()
    elif args.comprehensive:
        run_comprehensive_evaluation()
    elif args.stability:
        run_stability_test()
    elif args.custom:
        run_custom_evaluation(args.custom)
    else:
        print("请选择评测类型，使用 --help 查看选项")
        print("推荐使用: python run_evaluation.py --default")

if __name__ == "__main__":
    main()
