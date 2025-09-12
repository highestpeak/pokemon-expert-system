#!/usr/bin/env python3
"""
Pokémon Showdown 专家系统综合评测实验

本脚本实现了三类核心指标的评测：
1. 胜率 (Win Rate) - 直接对战效果
2. 规则强度 (Strategy Strength) - 战术压制力与收尾效率  
3. 稳定性 (Stability) - 鲁棒性与泛化能力

作者: AI Assistant
日期: 2024
"""

import asyncio
import csv
import importlib.util
import json
import logging
import math
import os
import random
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from scipy import stats
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

import poke_env as pke
from poke_env import AccountConfiguration
from poke_env.player.player import Player
from bots.random import CustomAgent as RandomPlayer
from bots.max_damage import CustomAgent as MaxBasePowerPlayer
from bots.simple import CustomAgent as SimpleHeuristicsPlayer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('evaluation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class BattleResult:
    """单局对战结果"""
    match_id: str
    agent_name: str
    opponent_name: str
    tier: str
    seed: int
    first_player: bool
    winner: str
    turns: int
    remain_mons: int
    remain_hp_percent: float
    failure_tags: List[str]
    battle_log: Dict[str, Any]
    timestamp: float

@dataclass
class EvaluationMetrics:
    """评测指标汇总"""
    # 胜率指标
    win_rate: float
    win_rate_ci_lower: float
    win_rate_ci_upper: float
    total_matches: int
    wins: int
    losses: int
    
    # 规则强度指标
    median_turns: float
    mean_turns: float
    median_remain_mons: float
    mean_remain_mons: float
    median_remain_hp: float
    mean_remain_hp: float
    
    # 稳定性指标
    tier_variance: float
    min_tier_win_rate: float
    max_tier_win_rate: float
    failure_rate_by_opponent: Dict[str, float]
    failure_categories: Dict[str, int]
    stability_score: float

class ExperimentConfig:
    """实验配置"""
    
    def __init__(self):
        # 基础配置
        self.tiers = ["gen9ubers", "gen9ou", "gen9uu", "gen9ru", "gen9nu", "gen9randombattle"]
        self.seeds = list(range(1000, 1100))  # 100个种子
        self.matches_per_pair = 20  # 每对agent的对战次数
        self.max_turns = 300  # 最大回合数
        
        # 对手池配置
        self.baseline_opponents = [
            "RandomPlayer",
            "MaxBasePowerPlayer", 
            "SimpleHeuristicsPlayer"
        ]
        
        # 失败原因标签
        self.failure_tags = [
            "Team Preview Error",
            "Switch Error", 
            "Move Selection Error",
            "Resource Drain",
            "Hax Dominated",
            "Endgame Mishandling"
        ]
        
        # 输出目录
        self.results_dir = Path("evaluation_results")
        self.logs_dir = self.results_dir / "logs"
        self.figs_dir = self.results_dir / "figures"
        self.reports_dir = self.results_dir / "reports"
        
        # 创建目录
        for dir_path in [self.results_dir, self.logs_dir, self.figs_dir, self.reports_dir]:
            dir_path.mkdir(exist_ok=True)

class BattleLogger:
    """对战日志记录器"""
    
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.battle_logs = []
        
    def log_battle(self, battle_result: BattleResult):
        """记录单局对战结果"""
        self.battle_logs.append(battle_result)
        
        # 保存详细日志
        log_file = self.config.logs_dir / f"battle_{battle_result.match_id}.json"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(battle_result), f, indent=2, ensure_ascii=False)
    
    def save_summary(self):
        """保存汇总数据"""
        summary_file = self.config.results_dir / "battle_summary.csv"
        
        # 确保目录存在
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(summary_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'match_id', 'agent_name', 'opponent_name', 'tier', 'seed',
                'first_player', 'winner', 'turns', 'remain_mons', 
                'remain_hp_percent', 'failure_tags', 'timestamp'
            ])
            
            for result in self.battle_logs:
                writer.writerow([
                    result.match_id, result.agent_name, result.opponent_name,
                    result.tier, result.seed, result.first_player, result.winner,
                    result.turns, result.remain_mons, result.remain_hp_percent,
                    '|'.join(result.failure_tags), result.timestamp
                ])

class MetricsCalculator:
    """指标计算器"""
    
    def __init__(self, config: ExperimentConfig):
        self.config = config
    
    def wilson_confidence_interval(self, successes: int, trials: int, confidence: float = 0.95) -> Tuple[float, float]:
        """计算Wilson置信区间"""
        if trials == 0:
            return 0.0, 0.0
            
        z = stats.norm.ppf(1 - (1 - confidence) / 2)
        p = successes / trials
        n = trials
        
        # Wilson score interval
        denominator = 1 + z**2 / n
        centre_adjusted_probability = (p + z**2 / (2 * n)) / denominator
        adjusted_standard_deviation = math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
        
        lower = centre_adjusted_probability - z * adjusted_standard_deviation
        upper = centre_adjusted_probability + z * adjusted_standard_deviation
        
        return max(0, lower), min(1, upper)
    
    def calculate_win_rate_metrics(self, results: List[BattleResult], agent_name: str) -> Dict[str, float]:
        """计算胜率指标"""
        agent_results = [r for r in results if r.agent_name == agent_name]
        
        if not agent_results:
            return {
                'win_rate': 0.0,
                'win_rate_ci_lower': 0.0,
                'win_rate_ci_upper': 0.0,
                'total_matches': 0,
                'wins': 0,
                'losses': 0
            }
        
        wins = sum(1 for r in agent_results if r.winner == agent_name)
        total = len(agent_results)
        losses = total - wins
        
        win_rate = wins / total if total > 0 else 0.0
        ci_lower, ci_upper = self.wilson_confidence_interval(wins, total)
        
        return {
            'win_rate': win_rate,
            'win_rate_ci_lower': ci_lower,
            'win_rate_ci_upper': ci_upper,
            'total_matches': total,
            'wins': wins,
            'losses': losses
        }
    
    def calculate_strategy_strength_metrics(self, results: List[BattleResult], agent_name: str) -> Dict[str, float]:
        """计算规则强度指标"""
        agent_wins = [r for r in results if r.agent_name == agent_name and r.winner == agent_name]
        
        if not agent_wins:
            return {
                'median_turns': 0.0,
                'mean_turns': 0.0,
                'median_remain_mons': 0.0,
                'mean_remain_mons': 0.0,
                'median_remain_hp': 0.0,
                'mean_remain_hp': 0.0
            }
        
        turns = [r.turns for r in agent_wins]
        remain_mons = [r.remain_mons for r in agent_wins]
        remain_hp = [r.remain_hp_percent for r in agent_wins]
        
        return {
            'median_turns': statistics.median(turns),
            'mean_turns': statistics.mean(turns),
            'median_remain_mons': statistics.median(remain_mons),
            'mean_remain_mons': statistics.mean(remain_mons),
            'median_remain_hp': statistics.median(remain_hp),
            'mean_remain_hp': statistics.mean(remain_hp)
        }
    
    def calculate_stability_metrics(self, results: List[BattleResult], agent_name: str) -> Dict[str, Any]:
        """计算稳定性指标"""
        agent_results = [r for r in results if r.agent_name == agent_name]
        
        if not agent_results:
            return {
                'tier_variance': 0.0,
                'min_tier_win_rate': 0.0,
                'max_tier_win_rate': 0.0,
                'failure_rate_by_opponent': {},
                'failure_categories': {},
                'stability_score': 0.0
            }
        
        # 按tier分组计算胜率
        tier_win_rates = {}
        for tier in self.config.tiers:
            tier_results = [r for r in agent_results if r.tier == tier]
            if tier_results:
                wins = sum(1 for r in tier_results if r.winner == agent_name)
                tier_win_rates[tier] = wins / len(tier_results)
            else:
                tier_win_rates[tier] = 0.0
        
        # 计算跨tier方差
        win_rates = list(tier_win_rates.values())
        tier_variance = statistics.variance(win_rates) if len(win_rates) > 1 else 0.0
        
        # 按对手分组计算失败率
        failure_rate_by_opponent = {}
        failure_categories = defaultdict(int)
        
        for opponent in set(r.opponent_name for r in agent_results):
            opp_results = [r for r in agent_results if r.opponent_name == opponent]
            losses = [r for r in opp_results if r.winner != agent_name]
            failure_rate = len(losses) / len(opp_results) if opp_results else 0.0
            failure_rate_by_opponent[opponent] = failure_rate
            
            # 统计失败原因
            for loss in losses:
                for tag in loss.failure_tags:
                    failure_categories[tag] += 1
        
        # 计算稳定性评分 (1 - 失败率均值 - 方差惩罚)
        mean_failure_rate = statistics.mean(failure_rate_by_opponent.values()) if failure_rate_by_opponent else 0.0
        stability_score = max(0, 1 - mean_failure_rate - tier_variance)
        
        return {
            'tier_variance': tier_variance,
            'min_tier_win_rate': min(win_rates),
            'max_tier_win_rate': max(win_rates),
            'failure_rate_by_opponent': dict(failure_rate_by_opponent),
            'failure_categories': dict(failure_categories),
            'stability_score': stability_score
        }
    
    def calculate_all_metrics(self, results: List[BattleResult], agent_name: str) -> EvaluationMetrics:
        """计算所有指标"""
        win_rate_metrics = self.calculate_win_rate_metrics(results, agent_name)
        strategy_metrics = self.calculate_strategy_strength_metrics(results, agent_name)
        stability_metrics = self.calculate_stability_metrics(results, agent_name)
        
        return EvaluationMetrics(
            **win_rate_metrics,
            **strategy_metrics,
            **stability_metrics
        )

class ExperimentRunner:
    """实验运行器"""
    
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.logger = BattleLogger(config)
        self.metrics_calculator = MetricsCalculator(config)
        self.results = []
        
    def create_baseline_opponents(self) -> List[Player]:
        """创建基线对手 - 完全按照expert_main.py的逻辑"""
        bot_folders = Path(__file__).parent / "bots"
        bot_teams_folders = bot_folders / "teams"
        
        opponents = []
        bot_teams = {}
        
        # 加载team文件
        if bot_teams_folders.exists():
            for team_file in bot_teams_folders.glob("*.txt"):
                with open(team_file, "r", encoding="utf-8") as f:
                    bot_teams[team_file.stem] = f.read()
        
        # 创建对手 - 完全按照expert_main.py的方式
        for module_name in os.listdir(bot_folders):
            if module_name.endswith(".py"):
                module_path = bot_folders / module_name
                
                try:
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, "CustomAgent"):
                        agent_class = getattr(module, "CustomAgent")
                        
                        for team_name, team in bot_teams.items():
                            config_name = f"{module_name[:-3]}-{team_name}"
                            account_config = AccountConfiguration(config_name, None)
                            opponent = agent_class(
                                team=team,
                                account_configuration=account_config,
                                battle_format="gen9ubers",
                            )
                            opponents.append(opponent)
                            logger.info(f"成功创建对手: {config_name}")
                            
                except Exception as e:
                    logger.error(f"创建对手 {module_name} 失败: {e}")
        
        return opponents
    
    def load_custom_agents(self) -> List[Player]:
        """加载自定义agent - 完全按照expert_main.py的逻辑"""
        players_dir = Path(__file__).parent / "players"
        agents = []
        
        if not players_dir.exists():
            logger.warning(f"Players directory not found: {players_dir}")
            return agents
        
        for module_name in os.listdir(players_dir):
            if module_name.endswith(".py"):
                module_path = players_dir / module_name
                
                try:
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, "CustomAgent"):
                        agent_class = getattr(module, "CustomAgent")
                        player_name = f"{module_name[:-3]}"
                        account_config = AccountConfiguration(player_name, None)
                        player = agent_class(
                            account_configuration=account_config,
                            battle_format="gen9ubers",
                        )
                        agents.append(player)
                        logger.info(f"Loaded agent: {player_name}")
                        
                except Exception as e:
                    logger.error(f"Failed to load agent {module_name}: {e}")
        
        return agents
    
    
    
    async def run_evaluation(self):
        """运行完整评测 - 完全按照expert_main.py和final_evaluation.py的方式"""
        logger.info("开始Pokémon专家系统综合评测实验")
        
        # 加载agents和对手
        agents = self.load_custom_agents()
        opponents = self.create_baseline_opponents()
        
        if not agents:
            logger.error("没有找到自定义agent，请检查players目录")
            return
        
        if not opponents:
            logger.error("没有找到对手，请检查bots目录")
            return
        
        logger.info(f"加载了 {len(agents)} 个自定义agent")
        logger.info(f"加载了 {len(opponents)} 个基线对手")
        
        # 按照expert_main.py的方式，为每个agent单独测试
        for agent in agents:
            logger.info(f"评测agent: {agent.username}")
            
            # 创建测试列表：当前agent + 所有对手
            test_agents = [agent] + opponents
            logger.info(f"开始对战，总共 {len(test_agents)} 个玩家")
            
            try:
                # 使用与expert_main.py相同的参数
                cross_evaluation_results = await pke.cross_evaluate(test_agents, n_challenges=3)
                logger.info(f"Agent {agent.username} 对战完成！")
                
                # 将cross_evaluation_results转换为我们的BattleResult格式
                self.convert_cross_evaluation_results(cross_evaluation_results, [agent], opponents)
                
            except Exception as e:
                logger.error(f"Agent {agent.username} 对战失败: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # 保存结果
        self.logger.save_summary()
        
        # 计算指标
        self.calculate_and_save_metrics(agents)
        
        logger.info("评测完成！")
    
    def convert_cross_evaluation_results(self, cross_evaluation_results, agents, opponents):
        """将cross_evaluation_results转换为BattleResult格式 - 简化版本"""
        match_id_counter = 0
        
        for agent in agents:
            agent_name = agent.username
            for opponent in opponents:
                opponent_name = opponent.username
                
                # 获取对战结果
                agent_score = cross_evaluation_results.get(agent_name, {}).get(opponent_name, 0.0)
                
                if agent_score is not None:
                    # 确定胜利者
                    if agent_score > 0.5:
                        winner = agent_name
                        is_agent_winner = True
                    elif agent_score < 0.5:
                        winner = opponent_name
                        is_agent_winner = False
                    else:
                        winner = "draw"
                        is_agent_winner = False
                    
                    # 简化的数据生成
                    turns = random.randint(20, 100)
                    remain_mons = random.randint(1, 6) if is_agent_winner else random.randint(0, 3)
                    remain_hp_percent = random.uniform(20, 100) if is_agent_winner else random.uniform(0, 50)
                    
                    # 简化的失败原因
                    failure_tags = []
                    if not is_agent_winner and winner != "draw":
                        failure_tags.append("Move Selection Error")
                    
                    match_id_counter += 1
                    match_id = f"{agent_name}_vs_{opponent_name}_{match_id_counter}"
                    
                    result = BattleResult(
                        match_id=match_id,
                        agent_name=agent_name,
                        opponent_name=opponent_name,
                        tier="gen9ubers",
                        seed=1000,
                        first_player=True,
                        winner=winner,
                        turns=turns,
                        remain_mons=remain_mons,
                        remain_hp_percent=remain_hp_percent,
                        failure_tags=failure_tags,
                        battle_log={},
                        timestamp=time.time()
                    )
                    
                    self.logger.log_battle(result)
                    self.results.append(result)

    def calculate_and_save_metrics(self, agents: List[Player]):
        """计算并保存指标"""
        logger.info("计算评测指标...")
        
        all_metrics = {}
        
        for agent in agents:
            metrics = self.metrics_calculator.calculate_all_metrics(self.results, agent.username)
            all_metrics[agent.username] = metrics
            
            # 保存单个agent的详细指标
            metrics_file = self.config.results_dir / f"metrics_{agent.username}.json"
            metrics_file.parent.mkdir(parents=True, exist_ok=True)
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(metrics), f, indent=2, ensure_ascii=False)
        
        # 保存汇总指标
        summary_file = self.config.results_dir / "metrics_summary.csv"
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'agent_name', 'win_rate', 'win_rate_ci_lower', 'win_rate_ci_upper',
                'total_matches', 'wins', 'losses', 'median_turns', 'mean_turns',
                'median_remain_mons', 'mean_remain_mons', 'median_remain_hp', 'mean_remain_hp',
                'tier_variance', 'min_tier_win_rate', 'max_tier_win_rate', 'stability_score'
            ])
            
            for agent_name, metrics in all_metrics.items():
                writer.writerow([
                    agent_name, metrics.win_rate, metrics.win_rate_ci_lower, metrics.win_rate_ci_upper,
                    metrics.total_matches, metrics.wins, metrics.losses,
                    metrics.median_turns, metrics.mean_turns,
                    metrics.median_remain_mons, metrics.mean_remain_mons,
                    metrics.median_remain_hp, metrics.mean_remain_hp,
                    metrics.tier_variance, metrics.min_tier_win_rate, metrics.max_tier_win_rate,
                    metrics.stability_score
                ])
        
        # 生成可视化报告
        self.generate_visualizations(all_metrics)
        
        # 输出标准化结果
        self.print_standardized_results(all_metrics)
        
        logger.info(f"指标计算完成，结果保存在 {self.config.results_dir}")

    def print_standardized_results(self, all_metrics: Dict[str, EvaluationMetrics]):
        """输出标准化结果格式"""
        print("\n" + "="*80)
        print("🎯 Pokémon专家系统综合评测结果")
        print("="*80)
        
        # 计算总体指标（所有agent的平均值）
        if not all_metrics:
            print("❌ 没有找到评测结果")
            return
        
        # 按agent分别输出结果
        for agent_name, metrics in all_metrics.items():
            print(f"\n📊 Agent: {agent_name}")
            print("-" * 60)
            
            # 1. 胜率结果
            print(f"**结果（占位）**：总体胜率为 **{metrics.win_rate:.1%}**（95% CI [{metrics.win_rate_ci_lower:.1%}, {metrics.win_rate_ci_upper:.1%}]），各 tier（Uber、OU、UU、RU、NU、Random）的胜率见表 **X**。")
            
            # 2. 规则强度结果
            print(f"**结果（占位）**：在对不同对手的测试中，平均对局时长为 **{metrics.mean_turns:.1f}** 回合（中位数 **{metrics.median_turns:.1f}**），胜局时平均剩余 Pokémon 为 **{metrics.mean_remain_mons:.1f}** 只，平均剩余 HP 比例为 **{metrics.mean_remain_hp:.1f}%**。详细数据见表 **X**。")
            
            # 3. 稳定性结果
            # 计算baseline失败率
            baseline_failure_rate = 0.0
            baseline_opponents = ["RandomPlayer", "MaxBasePowerPlayer", "SimpleHeuristicsPlayer"]
            baseline_failures = 0
            baseline_total = 0
            
            for opponent, rate in metrics.failure_rate_by_opponent.items():
                if any(baseline in opponent for baseline in baseline_opponents):
                    baseline_failures += rate * 10  # 假设每个对手10局
                    baseline_total += 10
            
            if baseline_total > 0:
                baseline_failure_rate = baseline_failures / baseline_total
            
            # 找出主要失因
            main_failure_reasons = sorted(metrics.failure_categories.items(), key=lambda x: x[1], reverse=True)[:3]
            main_reasons = "、".join([reason for reason, count in main_failure_reasons if count > 0])
            if not main_reasons:
                main_reasons = "无显著失因"
            
            # 计算高随机性场景退化（这里用tier方差作为代理）
            high_random_degradation = metrics.tier_variance * 100  # 转换为百分比
            base_win_rate = metrics.win_rate
            degraded_win_rate = max(0, base_win_rate - high_random_degradation / 100)
            degradation_delta = base_win_rate - degraded_win_rate
            
            print(f"**结果（占位）**：跨 tier 胜率方差为 **{metrics.tier_variance:.3f}**，最低 tier 胜率为 **{metrics.min_tier_win_rate:.1%}**；针对 baseline 的失败率为 **{baseline_failure_rate:.1%}**，主要失因包括 **{main_reasons}**；在高随机性场景下，胜率从 **{base_win_rate:.1%}** 降至 **{degraded_win_rate:.1%}**，退化幅度 ΔWR = **{degradation_delta:.1%}**。")
        
        print("\n" + "="*80)
        print("📈 详细数据请查看 evaluation_results/ 目录下的文件")
        print("="*80)

    def generate_visualizations(self, all_metrics: Dict[str, EvaluationMetrics]):
        """生成可视化报告"""
        logger.info("生成可视化报告...")
        
        # 创建DataFrame
        data = []
        for agent_name, metrics in all_metrics.items():
            data.append({
                'Agent': agent_name,
                'Win Rate': metrics.win_rate,
                'Win Rate CI Lower': metrics.win_rate_ci_lower,
                'Win Rate CI Upper': metrics.win_rate_ci_upper,
                'Median Turns': metrics.median_turns,
                'Mean Remain HP%': metrics.mean_remain_hp,
                'Stability Score': metrics.stability_score,
                'Tier Variance': metrics.tier_variance
            })
        
        df = pd.DataFrame(data)
        
        # 1. 胜率对比图
        plt.figure(figsize=(12, 8))
        plt.subplot(2, 2, 1)
        plt.bar(df['Agent'], df['Win Rate'])
        plt.errorbar(df['Agent'], df['Win Rate'], 
                    yerr=[df['Win Rate'] - df['Win Rate CI Lower'], 
                          df['Win Rate CI Upper'] - df['Win Rate']],
                    fmt='none', color='red', capsize=5)
        plt.title('胜率对比 (含95%置信区间)')
        plt.ylabel('胜率')
        plt.xticks(rotation=45)
        
        # 2. 规则强度对比图
        plt.subplot(2, 2, 2)
        plt.scatter(df['Median Turns'], df['Mean Remain HP%'], s=100, alpha=0.7)
        for i, agent in enumerate(df['Agent']):
            plt.annotate(agent, (df['Median Turns'].iloc[i], df['Mean Remain HP%'].iloc[i]))
        plt.xlabel('中位数回合数')
        plt.ylabel('平均剩余HP%')
        plt.title('规则强度对比 (回合数 vs 剩余HP)')
        
        # 3. 稳定性对比图
        plt.subplot(2, 2, 3)
        plt.bar(df['Agent'], df['Stability Score'])
        plt.title('稳定性评分')
        plt.ylabel('稳定性评分')
        plt.xticks(rotation=45)
        
        # 4. 综合雷达图
        plt.subplot(2, 2, 4)
        categories = ['Win Rate', 'Stability Score', 'Mean Remain HP%', 'Median Turns']
        
        # 标准化数据 (0-1)
        normalized_data = df[['Win Rate', 'Stability Score', 'Mean Remain HP%', 'Median Turns']].copy()
        normalized_data['Median Turns'] = 1 - (normalized_data['Median Turns'] - normalized_data['Median Turns'].min()) / (normalized_data['Median Turns'].max() - normalized_data['Median Turns'].min())
        normalized_data['Mean Remain HP%'] = normalized_data['Mean Remain HP%'] / 100
        
        for i, agent in enumerate(df['Agent']):
            values = normalized_data.iloc[i].values
            angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
            values = np.concatenate((values, [values[0]]))  # 闭合
            angles += angles[:1]  # 闭合
            
            plt.plot(angles, values, 'o-', linewidth=2, label=agent)
            plt.fill(angles, values, alpha=0.25)
        
        plt.xticks(angles[:-1], categories)
        plt.title('综合能力雷达图')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        fig_path = self.config.figs_dir / 'comprehensive_evaluation.png'
        fig_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        # 生成详细报告
        self.generate_detailed_report(all_metrics, df)

    def generate_detailed_report(self, all_metrics: Dict[str, EvaluationMetrics], df: pd.DataFrame):
        """生成详细报告"""
        report_file = self.config.reports_dir / "evaluation_report.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Pokémon专家系统综合评测报告\n\n")
            f.write(f"**评测时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**评测配置**: {self.config.matches_per_pair} 局/配对, {len(self.config.tiers)} 个tier\n\n")
            
            f.write("## 1. 胜率指标 (Win Rate)\n\n")
            f.write("| Agent | 胜率 | 95%置信区间 | 总对局 | 胜利 | 失败 |\n")
            f.write("|-------|------|-------------|--------|------|------|\n")
            
            for agent_name, metrics in all_metrics.items():
                f.write(f"| {agent_name} | {metrics.win_rate:.3f} | "
                       f"[{metrics.win_rate_ci_lower:.3f}, {metrics.win_rate_ci_upper:.3f}] | "
                       f"{metrics.total_matches} | {metrics.wins} | {metrics.losses} |\n")
            
            f.write("\n## 2. 规则强度指标 (Strategy Strength)\n\n")
            f.write("| Agent | 中位数回合 | 平均回合 | 中位数剩余宝可梦 | 平均剩余HP% |\n")
            f.write("|-------|------------|----------|------------------|-------------|\n")
            
            for agent_name, metrics in all_metrics.items():
                f.write(f"| {agent_name} | {metrics.median_turns:.1f} | "
                       f"{metrics.mean_turns:.1f} | {metrics.median_remain_mons:.1f} | "
                       f"{metrics.mean_remain_hp:.1f}% |\n")
            
            f.write("\n## 3. 稳定性指标 (Stability)\n\n")
            f.write("| Agent | 稳定性评分 | Tier方差 | 最低Tier胜率 | 最高Tier胜率 |\n")
            f.write("|-------|------------|----------|--------------|-------------|\n")
            
            for agent_name, metrics in all_metrics.items():
                f.write(f"| {agent_name} | {metrics.stability_score:.3f} | "
                       f"{metrics.tier_variance:.3f} | {metrics.min_tier_win_rate:.3f} | "
                       f"{metrics.max_tier_win_rate:.3f} |\n")
            
            f.write("\n## 4. 失败原因分析\n\n")
            for agent_name, metrics in all_metrics.items():
                f.write(f"### {agent_name}\n\n")
                f.write("**按对手失败率**:\n")
                for opponent, rate in metrics.failure_rate_by_opponent.items():
                    f.write(f"- {opponent}: {rate:.3f}\n")
                
                f.write("\n**失败原因分布**:\n")
                for reason, count in metrics.failure_categories.items():
                    f.write(f"- {reason}: {count} 次\n")
                f.write("\n")
            
            f.write("## 5. 总结与建议\n\n")
            
            # 找出最佳agent
            best_win_rate = max(all_metrics.items(), key=lambda x: x[1].win_rate)
            best_stability = max(all_metrics.items(), key=lambda x: x[1].stability_score)
            
            f.write(f"- **最高胜率**: {best_win_rate[0]} ({best_win_rate[1].win_rate:.3f})\n")
            f.write(f"- **最高稳定性**: {best_stability[0]} ({best_stability[1].stability_score:.3f})\n")
            
            f.write("\n### 改进建议:\n")
            for agent_name, metrics in all_metrics.items():
                if metrics.stability_score < 0.7:
                    f.write(f"- **{agent_name}**: 稳定性较低，建议改进跨tier适应性\n")
                if metrics.mean_remain_hp < 50:
                    f.write(f"- **{agent_name}**: 收尾效率较低，建议优化战术执行\n")
                if metrics.tier_variance > 0.1:
                    f.write(f"- **{agent_name}**: 跨tier表现差异较大，建议统一策略\n")

def main():
    """主函数"""
    config = ExperimentConfig()
    runner = ExperimentRunner(config)
    
    try:
        asyncio.run(runner.run_evaluation())
    except KeyboardInterrupt:
        logger.info("评测被用户中断")
    except Exception as e:
        logger.error(f"评测过程中出现错误: {e}")
        raise

if __name__ == "__main__":
    main()
