#!/usr/bin/env python3
"""
实验配置文件

支持不同tier、对手池、样本量等实验参数的配置
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from pathlib import Path

@dataclass
class TierConfig:
    """Tier配置"""
    name: str
    format: str
    description: str
    difficulty_level: int  # 1-5, 5最难

@dataclass
class OpponentConfig:
    """对手配置"""
    name: str
    type: str  # "baseline", "strong_bot", "custom"
    description: str
    difficulty_level: int  # 1-5, 5最难
    team_file: str = None  # 自定义队伍文件

@dataclass
class ExperimentSettings:
    """实验设置"""
    # 基础设置
    experiment_name: str
    description: str
    
    # 样本量设置
    matches_per_pair: int = 20
    seeds_count: int = 100
    max_turns: int = 300
    
    # Tier设置
    enabled_tiers: List[str] = None
    
    # 对手池设置
    enabled_opponents: List[str] = None
    
    # 输出设置
    results_dir: str = "evaluation_results"
    save_detailed_logs: bool = True
    generate_visualizations: bool = True
    
    # 高级设置
    parallel_battles: int = 4  # 并行对战数
    timeout_seconds: int = 300  # 单局超时时间
    retry_failed_battles: bool = True
    max_retries: int = 3

class ExperimentConfigManager:
    """实验配置管理器"""
    
    def __init__(self):
        self.tiers = self._load_tier_configs()
        self.opponents = self._load_opponent_configs()
        self.default_settings = self._load_default_settings()
    
    def _load_tier_configs(self) -> Dict[str, TierConfig]:
        """加载Tier配置"""
        return {
            "gen9ubers": TierConfig(
                name="Ubers",
                format="gen9ubers", 
                description="最高级别，包含传说宝可梦",
                difficulty_level=5
            ),
            "gen9ou": TierConfig(
                name="OU",
                format="gen9ou",
                description="OverUsed，最常用的对战环境",
                difficulty_level=4
            ),
            "gen9uu": TierConfig(
                name="UU", 
                format="gen9uu",
                description="UnderUsed，次常用环境",
                difficulty_level=3
            ),
            "gen9ru": TierConfig(
                name="RU",
                format="gen9ru", 
                description="RarelyUsed，较少使用环境",
                difficulty_level=2
            ),
            "gen9nu": TierConfig(
                name="NU",
                format="gen9nu",
                description="NeverUsed，几乎不使用环境", 
                difficulty_level=1
            ),
            "gen9randombattle": TierConfig(
                name="Random Battle",
                format="gen9randombattle",
                description="随机对战，队伍随机生成",
                difficulty_level=3
            )
        }
    
    def _load_opponent_configs(self) -> Dict[str, OpponentConfig]:
        """加载对手配置"""
        return {
            "RandomPlayer": OpponentConfig(
                name="Random Player",
                type="baseline",
                description="完全随机选择行动",
                difficulty_level=1
            ),
            "MaxBasePowerPlayer": OpponentConfig(
                name="Max Damage Player", 
                type="baseline",
                description="总是选择威力最高的技能",
                difficulty_level=2
            ),
            "SimpleHeuristicsPlayer": OpponentConfig(
                name="Simple Heuristics Player",
                type="baseline", 
                description="使用简单启发式规则",
                difficulty_level=3
            ),
            "StrongBot1": OpponentConfig(
                name="Strong Bot 1",
                type="strong_bot",
                description="社区强bot示例1",
                difficulty_level=4,
                team_file="strong_team_1.txt"
            ),
            "StrongBot2": OpponentConfig(
                name="Strong Bot 2", 
                type="strong_bot",
                description="社区强bot示例2",
                difficulty_level=4,
                team_file="strong_team_2.txt"
            )
        }
    
    def _load_default_settings(self) -> ExperimentSettings:
        """加载默认实验设置"""
        return ExperimentSettings(
            experiment_name="Pokemon Expert System Evaluation",
            description="Pokémon专家系统综合评测实验",
            matches_per_pair=20,
            seeds_count=100,
            max_turns=300,
            enabled_tiers=["gen9ubers", "gen9ou", "gen9uu", "gen9randombattle"],
            enabled_opponents=["RandomPlayer", "MaxBasePowerPlayer", "SimpleHeuristicsPlayer"],
            results_dir="evaluation_results",
            save_detailed_logs=True,
            generate_visualizations=True,
            parallel_battles=4,
            timeout_seconds=300,
            retry_failed_battles=True,
            max_retries=3
        )
    
    def create_quick_evaluation_config(self) -> ExperimentSettings:
        """创建快速评测配置（用于测试）"""
        return ExperimentSettings(
            experiment_name="Quick Evaluation",
            description="快速评测配置，用于测试和调试",
            matches_per_pair=5,
            seeds_count=10,
            max_turns=100,
            enabled_tiers=["gen9ou", "gen9randombattle"],
            enabled_opponents=["RandomPlayer", "MaxBasePowerPlayer"],
            results_dir="quick_evaluation_results",
            save_detailed_logs=False,
            generate_visualizations=True,
            parallel_battles=2,
            timeout_seconds=60,
            retry_failed_battles=False
        )
    
    def create_comprehensive_evaluation_config(self) -> ExperimentSettings:
        """创建全面评测配置"""
        return ExperimentSettings(
            experiment_name="Comprehensive Evaluation",
            description="全面评测配置，包含所有tier和对手",
            matches_per_pair=50,
            seeds_count=200,
            max_turns=500,
            enabled_tiers=list(self.tiers.keys()),
            enabled_opponents=list(self.opponents.keys()),
            results_dir="comprehensive_evaluation_results",
            save_detailed_logs=True,
            generate_visualizations=True,
            parallel_battles=8,
            timeout_seconds=600,
            retry_failed_battles=True,
            max_retries=5
        )
    
    def create_stability_test_config(self) -> ExperimentSettings:
        """创建稳定性测试配置"""
        return ExperimentSettings(
            experiment_name="Stability Test",
            description="专门测试稳定性和鲁棒性的配置",
            matches_per_pair=100,
            seeds_count=500,
            max_turns=300,
            enabled_tiers=list(self.tiers.keys()),
            enabled_opponents=["RandomPlayer", "MaxBasePowerPlayer", "SimpleHeuristicsPlayer"],
            results_dir="stability_test_results",
            save_detailed_logs=True,
            generate_visualizations=True,
            parallel_battles=6,
            timeout_seconds=300,
            retry_failed_battles=True,
            max_retries=3
        )
    
    def create_custom_config(self, 
                           experiment_name: str,
                           matches_per_pair: int = 20,
                           enabled_tiers: List[str] = None,
                           enabled_opponents: List[str] = None,
                           **kwargs) -> ExperimentSettings:
        """创建自定义配置"""
        if enabled_tiers is None:
            enabled_tiers = list(self.tiers.keys())
        if enabled_opponents is None:
            enabled_opponents = list(self.opponents.keys())
        
        return ExperimentSettings(
            experiment_name=experiment_name,
            description=f"自定义配置: {experiment_name}",
            matches_per_pair=matches_per_pair,
            enabled_tiers=enabled_tiers,
            enabled_opponents=enabled_opponents,
            **kwargs
        )
    
    def get_tier_info(self, tier_name: str) -> TierConfig:
        """获取tier信息"""
        return self.tiers.get(tier_name)
    
    def get_opponent_info(self, opponent_name: str) -> OpponentConfig:
        """获取对手信息"""
        return self.opponents.get(opponent_name)
    
    def validate_config(self, settings: ExperimentSettings) -> List[str]:
        """验证配置有效性"""
        errors = []
        
        # 检查tier
        for tier in settings.enabled_tiers:
            if tier not in self.tiers:
                errors.append(f"未知的tier: {tier}")
        
        # 检查对手
        for opponent in settings.enabled_opponents:
            if opponent not in self.opponents:
                errors.append(f"未知的对手: {opponent}")
        
        # 检查数值范围
        if settings.matches_per_pair < 1:
            errors.append("每对对战次数必须大于0")
        
        if settings.seeds_count < 1:
            errors.append("种子数量必须大于0")
        
        if settings.max_turns < 1:
            errors.append("最大回合数必须大于0")
        
        if settings.parallel_battles < 1:
            errors.append("并行对战数必须大于0")
        
        return errors
    
    def save_config(self, settings: ExperimentSettings, file_path: str):
        """保存配置到文件"""
        import json
        
        config_dict = {
            "experiment_name": settings.experiment_name,
            "description": settings.description,
            "matches_per_pair": settings.matches_per_pair,
            "seeds_count": settings.seeds_count,
            "max_turns": settings.max_turns,
            "enabled_tiers": settings.enabled_tiers,
            "enabled_opponents": settings.enabled_opponents,
            "results_dir": settings.results_dir,
            "save_detailed_logs": settings.save_detailed_logs,
            "generate_visualizations": settings.generate_visualizations,
            "parallel_battles": settings.parallel_battles,
            "timeout_seconds": settings.timeout_seconds,
            "retry_failed_battles": settings.retry_failed_battles,
            "max_retries": settings.max_retries
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
    
    def load_config(self, file_path: str) -> ExperimentSettings:
        """从文件加载配置"""
        import json
        
        with open(file_path, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        
        return ExperimentSettings(**config_dict)

# 预定义配置
CONFIG_MANAGER = ExperimentConfigManager()

# 常用配置快捷方式
QUICK_CONFIG = CONFIG_MANAGER.create_quick_evaluation_config()
DEFAULT_CONFIG = CONFIG_MANAGER.default_settings
COMPREHENSIVE_CONFIG = CONFIG_MANAGER.create_comprehensive_evaluation_config()
STABILITY_CONFIG = CONFIG_MANAGER.create_stability_test_config()

if __name__ == "__main__":
    # 示例：创建和保存配置
    config_manager = ExperimentConfigManager()
    
    # 创建自定义配置
    custom_config = config_manager.create_custom_config(
        experiment_name="My Custom Evaluation",
        matches_per_pair=30,
        enabled_tiers=["gen9ou", "gen9uu"],
        enabled_opponents=["RandomPlayer", "SimpleHeuristicsPlayer"]
    )
    
    # 验证配置
    errors = config_manager.validate_config(custom_config)
    if errors:
        print("配置错误:")
        for error in errors:
            print(f"- {error}")
    else:
        print("配置有效")
        
        # 保存配置
        config_manager.save_config(custom_config, "my_custom_config.json")
        print("配置已保存到 my_custom_config.json")
