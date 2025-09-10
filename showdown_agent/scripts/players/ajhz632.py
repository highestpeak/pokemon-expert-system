from poke_env.battle import AbstractBattle, Pokemon, Move
from poke_env.player import Player
from poke_env.battle.move_category import MoveCategory
from poke_env.battle.side_condition import SideCondition
from typing import Dict, List, Tuple, Optional, Any, cast
import random
import math
import logging
import os
import time
import json
from datetime import datetime

team = """
Arceus-Fairy @ Pixie Plate
Ability: Multitype
Tera Type: Fire
EVs: 248 HP / 72 Def / 188 Spe
Bold Nature
IVs: 0 Atk
- Calm Mind
- Judgment
- Taunt
- Recover

Zacian-Crowned @ Rusted Sword
Ability: Intrepid Sword
Tera Type: Flying
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Swords Dance
- Behemoth Blade
- Close Combat
- Wild Charge

Eternatus @ Power Herb
Ability: Pressure
Tera Type: Fire
EVs: 124 HP / 252 SpA / 132 Spe
Modest Nature
IVs: 0 Atk
- Agility
- Meteor Beam
- Dynamax Cannon
- Fire Blast

Necrozma-Dusk-Mane @ Assault Vest
Ability: Prism Armor
Tera Type: Steel
EVs: 248 HP / 200 Def / 60 SpD
Impish Nature
- Sunsteel Strike
- Earthquake
- Photon Geyser
- Rock Slide

Deoxys-Speed @ Focus Sash
Ability: Pressure
Tera Type: Ghost
EVs: 248 HP / 8 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Thunder Wave
- Spikes
- Taunt
- Psycho Boost

Kingambit @ Dread Plate
Ability: Supreme Overlord
Tera Type: Dark
EVs: 56 HP / 252 Atk / 200 Spe
Adamant Nature
- Swords Dance
- Kowtow Cleave
- Iron Head
- Sucker Punch
"""

# 宝可梦属性克制表 (第六世代起)
# 按照图片中的表格顺序排列，使用标准的Pokemon Showdown属性名称
type_chart_indices = [
    "NORMAL", "FIGHTING", "FLYING", "POISON", "GROUND", "ROCK", "BUG", "GHOST", 
    "STEEL", "FIRE", "WATER", "GRASS", "ELECTRIC", "PSYCHIC", "ICE", "DRAGON", 
    "DARK", "FAIRY"
]

# 属性相克矩阵 (攻击方属性 -> 防御方属性)
# 1 = 正常效果, 2 = 效果绝佳, 0.5 = 效果不好, 0 = 没有效果
# 来自 https://bulbapedia.bulbagarden.net/wiki/Type#Type_chart
type_effectiveness_matrix = [
    [1,   1,   1,   1,   1,   0.5, 1,   0,   0.5, 1,   1,   1,   1,   1,   1,   1,   1,   1],   # normal
    [2,   1,   0.5, 0.5, 1,   2,   0.5, 0,   2,   1,   1,   1,   1,   0.5, 2,   1,   2,   0.5], # fighting
    [1,   2,   1,   1,   1,   0.5, 2,   1,   0.5, 1,   1,   2,   0.5, 1,   1,   1,   1,   1],   # flying
    [1,   1,   1,   0.5, 0.5, 0.5, 1,   0.5, 0,   1,   1,   2,   1,   1,   1,   1,   1,   2],   # poison
    [1,   1,   0,   2,   1,   2,   0.5, 1,   2,   2,   1,   0.5, 2,   1,   1,   1,   1,   1],   # ground
    [1,   0.5, 2,   1,   0.5, 1,   2,   1,   0.5, 2,   1,   1,   1,   1,   2,   1,   1,   1],   # rock
    [1,   0.5, 0.5, 0.5, 1,   1,   1,   0.5, 0.5, 0.5, 1,   2,   1,   2,   1,   1,   2,   0.5], # bug
    [0,   1,   1,   1,   1,   1,   1,   2,   1,   1,   1,   1,   1,   2,   1,   1,   0.5, 1],   # ghost
    [1,   1,   1,   1,   1,   2,   1,   1,   0.5, 0.5, 0.5, 1,   0.5, 1,   2,   1,   1,   2],   # steel
    [1,   1,   1,   1,   1,   0.5, 2,   1,   2,   0.5, 0.5, 2,   1,   1,   2,   0.5, 1,   1],   # fire
    [1,   1,   1,   1,   2,   2,   1,   1,   1,   2,   0.5, 0.5, 1,   1,   1,   0.5, 1,   1],   # water
    [1,   1,   0.5, 0.5, 2,   2,   0.5, 1,   0.5, 0.5, 2,   0.5, 1,   1,   1,   0.5, 1,   1],   # grass
    [1,   1,   2,   1,   0,   1,   1,   1,   1,   1,   2,   0.5, 0.5, 1,   1,   1,   1,   1],   # electric
    [1,   2,   1,   2,   1,   1,   1,   1,   0.5, 1,   1,   1,   1,   0.5, 1,   1,   0,   1],   # psychic
    [1,   1,   2,   1,   2,   1,   1,   1,   0.5, 0.5, 0.5, 2,   1,   1,   0.5, 2,   1,   1],   # ice
    [1,   1,   1,   1,   1,   1,   1,   1,   0.5, 1,   1,   1,   1,   1,   1,   2,   1,   0],   # dragon
    [1,   0.5, 1,   1,   1,   1,   1,   2,   1,   1,   1,   1,   1,   2,   1,   1,   0.5, 0.5], # dark
    [1,   2,   1,   0.5, 1,   1,   1,   1,   0.5, 0.5, 1,   1,   1,   1,   1,   2,   2,   1]    # fairy
]

# ============================== 技能分类常量 ==============================

# 技能分类字典
MOVE_CLASSIFICATION = {
    'setup': {
        'swordsdance', 'dragondance', 'quiverdance', 'calmmind', 'nastyplot',
        'bulkup', 'irondefense', 'amnesia', 'agility', 'rockpolish',
        'workup', 'growth', 'honeclaws', 'coil', 'shiftgear'
    },
    'recovery': {
        'recover', 'roost', 'synthesis', 'moonlight', 'milkdrink',
        'softboiled', 'healorder', 'slackoff', 'shoreup', 'rest'
    },
    'status': {
        'thunderwave', 'willowisp', 'toxic', 'hypnosis', 'sleepspore',
        'spore', 'sing', 'yawn', 'encore', 'taunt', 'haze'
    },
    'field': {
        'stealthrock', 'spikes', 'toxicspikes', 'stickyweb', 'defog',
        'rapidspin', 'trickroom', 'lightscreen', 'reflect', 'auroraveil'
    },
    'protection': {
        'protect', 'detect', 'spikyshield', 'banefulbunker', 'obstruct',
        'substitute', 'kingsshield'
    },
    'priority': {
        'extremespeed', 'suckerpunch', 'bulletpunch', 'machpunch',
        'vacuumwave', 'aquajet', 'iceshard', 'shadow sneak'
    },
    # 新增：针对低级别格式的技能分类
    'nu_stall': {
        'toxic', 'willowisp', 'thunderwave', 'protect', 'substitute',
        'recover', 'roost', 'synthesis', 'rest', 'slackoff'
    },
    'ru_control': {
        'uturn', 'voltswitch', 'partingshot', 'teleport', 'taunt',
        'encore', 'haze', 'roar', 'whirlwind', 'defog', 'rapidspin'
    },
    'uu_offense': {
        'swordsdance', 'dragondance', 'calmmind', 'nastyplot',
        'extremespeed', 'suckerpunch', 'bulletpunch', 'machpunch'
    }
}

# ============================== 队伍组合检测常量 ==============================

# 撒钉组合招式
HAZARD_MOVES = {'stealthrock', 'spikes', 'toxicspikes', 'stickyweb'}

# 强化推队组合招式
SETUP_MOVES = {'swordsdance', 'dragondance', 'quiverdance', 'calmmind', 'nastyplot', 'bulkup'}

# 高威力招式特征词
HIGH_POWER_MOVE_KEYWORDS = {'blast', 'cannon', 'strike', 'claw'}

# 状态受队组合招式
STALL_MOVES = {'protect', 'toxic', 'willowisp', 'recover', 'roost', 'synthesis', 'rest'}

# 天气推队组合招式
WEATHER_MOVES = {'raindance', 'sunnyday', 'sandstorm', 'hail', 'snowscape'}

# 天气推队宝可梦
WEATHER_SWEEPERS = {'gyarados', 'charizard', 'tyranitar', 'abomasnow'}

# 双墙队组合招式
SCREEN_MOVES = {'lightscreen', 'reflect', 'auroraveil'}

# 灭亡歌陷阱组合招式
TRAP_MOVES = {'meanlook', 'perishsong', 'spiderweb', 'block'}

# 先制收割组合招式
PRIORITY_MOVES = {'extremespeed', 'suckerpunch', 'bulletpunch', 'machpunch', 'vacuumwave'}

# 回复受队组合招式
RECOVERY_MOVES = {'recover', 'roost', 'synthesis', 'moonlight', 'rest', 'slackoff'}

# ============================== 队伍组合应对 策略配置常量 ==============================
# 战略目标配置
STRATEGIC_TARGETS = {
    'sweep_setup': {
        'target': 'setup_disrupt',
        'priority_actions': ['taunt', 'encore', 'haze', 'thunderwave', 'willowisp'],
        'tactical_weights': {
            'W_K': 1.2,  # 略微提高KO权重，但不要太多以适应低威力环境
            'W_D': 1.0,  # 略微提高伤害权重，但不要太多以适应低威力环境
            'W_R': 1.1,  # 稍微提高风险权重
            'W_F': 0.8,  # 降低场地权重，但不要太多以适应低威力环境，NU/RU更注重控制
            'W_S': 0.7,  # 降低强化权重，但不要太多以适应低威力环境
            'W_C': 1.0   # 换人成本
        }
    },
    'status_stall': {
        'target': 'stall_break',
        'priority_actions': ['taunt', 'attack', 'setup', 'strong_attack'],
        'tactical_weights': {
            'W_K': 1.5,  # 保持高KO权重，受队需要快速突破
            'W_D': 1.2,  # 保持高伤害权重
            'W_R': 0.9,  # 降低风险权重
            'W_F': 0.5,  # 大幅降低场地权重
            'W_S': 0.4,  # 降低强化权重
            'W_C': 0.8   # 降低换人成本
        }
    },
    'entry_hazard': {
        'target': 'hazard_control',
        'priority_actions': ['defog', 'rapidspin', 'taunt', 'attack'],
        'tactical_weights': {
            'W_K': 1.1,  # 稍微提高KO权重
            'W_D': 1.0,  # 标准伤害权重
            'W_R': 1.0,  # 标准风险权重
            'W_F': 2.0,  # 大幅提高场地权重
            'W_S': 0.6,  # 降低强化权重
            'W_C': 1.1   # 稍微提高换人成本
        }
    },
    'trick_room': {
        'target': 'trick_room_counter',
        'priority_actions': ['protect', 'recover', 'switch', 'stall'],
        'tactical_weights': {
            'W_K': 0.8,  # 降低KO权重
            'W_D': 0.7,  # 降低伤害权重
            'W_R': 1.5,  # 大幅提高风险权重
            'W_F': 0.5,  # 降低场地权重
            'W_S': 0.3,  # 大幅降低强化权重
            'W_C': 0.6   # 降低换人成本
        }
    },
    'weather_sweep': {
        'target': 'weather_counter',
        'priority_actions': ['air_lock', 'weather_change', 'resist_switch', 'attack'],
        'tactical_weights': {
            'W_K': 1.2,  # 提高KO权重
            'W_D': 1.0,  # 伤害权重
            'W_R': 1.2,  # 提高风险权重
            'W_F': 1.3,  # 提高场地权重
            'W_S': 0.6,  # 降低强化权重
            'W_C': 1.0   # 换人成本
        }
    },
    # 新增：针对低级别格式的策略
    'nu_stall': {
        'target': 'stall_break',
        'priority_actions': ['taunt', 'strong_attack', 'setup', 'hazard_removal'],
        'tactical_weights': {
            'W_K': 1.5,  # 提高KO权重，受队需要快速突破
            'W_D': 1.2,  # 提高伤害权重
            'W_R': 0.8,  # 降低风险权重，受队攻击力低
            'W_F': 2.0,  # 大幅提高场地权重，NU更注重场地控制
            'W_S': 1.0,  # 提高强化权重
            'W_C': 0.7   # 降低换人成本，更灵活换人
        }
    },
    'ru_balance': {
        'target': 'momentum_gain',
        'priority_actions': ['attack', 'switch', 'setup'],
        'tactical_weights': {
            'W_K': 1.1,  # 稍微提高KO权重
            'W_D': 1.0,  # 标准伤害权重
            'W_R': 1.0,  # 标准风险权重
            'W_F': 1.2,  # 提高场地权重
            'W_S': 0.9,  # 稍微降低强化权重
            'W_C': 1.0   # 标准换人成本
        }
    },
    'uu_offense': {
        'target': 'momentum_gain',
        'priority_actions': ['attack', 'setup', 'priority'],
        'tactical_weights': {
            'W_K': 1.3,  # 提高KO权重
            'W_D': 1.1,  # 提高伤害权重
            'W_R': 0.9,  # 降低风险权重
            'W_F': 0.8,  # 降低场地权重
            'W_S': 1.1,  # 提高强化权重
            'W_C': 1.0   # 标准换人成本
        }
    },
    'default': {
        'target': 'momentum_gain',
        'priority_actions': ['attack', 'switch', 'setup'],
        'tactical_weights': {
            'W_K': 1.0,  # 标准权重
            'W_D': 1.0,  # 标准权重
            'W_R': 1.0,  # 标准权重
            'W_F': 1.0,  # 标准权重
            'W_S': 1.0,  # 标准权重
            'W_C': 1.0   # 标准权重
        }
    }
}

# 策略置信度阈值
STRATEGY_CONFIDENCE_THRESHOLDS = {
    'sweep_setup': 0.5,
    'status_stall': 0.4,
    'entry_hazard': 0.4,
    'trick_room': 0.5,
    'weather_sweep': 0.4
}

# ============================== 技能优先级 ==============================

# 技能优先级：生存 > 控制 > 强化 > 攻击 > 先制
PRIORITY_ORDER = ['recovery', 'protection', 'status', 'field', 'setup', 'physical_attack', 'special_attack', 'priority', 'nu_stall', 'ru_control', 'uu_offense']

# 技能优先级乘数配置
PRIORITY_MULTIPLIER = {
    'recovery': 1.2,      # 回复技能优先级最高
    'protection': 1.1,    # 保护技能次之
    'status': 1.05,       # 状态技能
    'field': 1.0,         # 场地技能
    'setup': 0.9,         # 强化技能
    'physical_attack': 0.8,  # 物理攻击
    'special_attack': 0.8,   # 特殊攻击
    'priority': 0.7,      # 先制技能
    'nu_stall': 1.15,     # NU受队技能优先级较高
    'ru_control': 1.1,    # RU控制技能优先级较高
    'uu_offense': 0.95,   # UU进攻技能优先级稍高
    'other': 0.5          # 其他技能
}

# ============================== matrix helper ==============================

def get_type_effectiveness(attacking_type, defending_type):
    """
    获取属性相克倍数
    
    Args:
        attacking_type (str): 攻击方属性
        defending_type (str): 防御方属性
    
    Returns:
        float: 相克倍数 (0, 0.5, 1, 2)
    """
    try:
        attack_idx = type_chart_indices.index(attacking_type)
        defend_idx = type_chart_indices.index(defending_type)
        return type_effectiveness_matrix[attack_idx][defend_idx]
    except ValueError:
        # 如果属性名称不在列表中，返回1（正常效果）
        return 1.0

def get_effectiveness_multiplier(attacking_types, defending_types):
    """
    计算多属性宝可梦的相克倍数
    
    Args:
        attacking_types (list): 攻击方属性列表
        defending_types (list): 防御方属性列表
    
    Returns:
        float: 总相克倍数
    """
    total_multiplier = 1.0
    
    for attack_type in attacking_types:
        for defend_type in defending_types:
            multiplier = get_type_effectiveness(attack_type, defend_type)
            total_multiplier *= multiplier
    
    return total_multiplier

# ============================== other helper ==============================

def get_active_pokemon(battle: AbstractBattle) -> Tuple[Optional[Pokemon], Optional[Pokemon]]:
    """安全获取我方和对手的当前宝可梦"""
    # 安全获取我方宝可梦
    my_pokemon = getattr(battle, 'active_pokemon', None)
    if my_pokemon is not None and hasattr(my_pokemon, 'fainted'):
        my_pokemon = cast(Pokemon, my_pokemon)
    
    # 安全获取对手宝可梦
    opp_pokemon = getattr(battle, 'opponent_active_pokemon', None)
    if opp_pokemon is not None and hasattr(opp_pokemon, 'fainted'):
        opp_pokemon = cast(Pokemon, opp_pokemon)
    
    return my_pokemon, opp_pokemon

class CustomAgent(Player):
    
    def __init__(self, *args, **kwargs):
        super().__init__(team=team, *args, **kwargs)
        # 初始化学习数据
        self.opponent_history = []  # 对手历史行为
        self.battle_state = {}  # 当前对战状态
        self.combo_confidences = {}  # 组合检测置信度
        self.phase_weights = {}  # 阶段权重
        self.status_adjustments = {}  # 异常状态调整
        self.opponent_threat_level = 'medium'  # 对手威胁等级
        
        # 初始化日志系统
        self.battle_id = None
        self.battle_start_time = None
        self.battle_logger = None
        self.performance_stats = {
            'total_battles': 0,
            'wins': 0,
            'losses': 0,
            'total_turns': 0,
            'total_decision_time': 0.0,
            'strategy_usage': {},
            'opponent_types': {},
            'damage_calculations': 0,
            'ko_predictions': 0,
            'correct_ko_predictions': 0
        }
        self.setup_logging()

    def setup_logging(self):
        """设置日志系统"""
        # 创建results目录
        self.results_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'results')
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 设置主日志记录器
        self.main_logger = logging.getLogger(f'ajhz632_main_{id(self)}')
        self.main_logger.setLevel(logging.INFO)
        
        # 清除现有的处理器
        for handler in self.main_logger.handlers[:]:
            self.main_logger.removeHandler(handler)
        
        # 创建文件处理器
        log_file = os.path.join(self.results_dir, 'ajhz632_main.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 创建格式器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        self.main_logger.addHandler(file_handler)
        self.main_logger.info("AJHZ632 Agent initialized")

    def start_battle_logging(self, battle: AbstractBattle):
        """开始对战日志记录 - 始终创建详细日志，但只在失败时保存"""
        self.battle_id = f"battle_{int(time.time())}_{battle.battle_tag}"
        self.battle_start_time = time.time()
        
        # 创建对战专用日志记录器
        self.battle_logger = logging.getLogger(f'ajhz632_battle_{self.battle_id}')
        self.battle_logger.setLevel(logging.DEBUG)
        
        # 清除现有的处理器
        for handler in self.battle_logger.handlers[:]:
            self.battle_logger.removeHandler(handler)
        
        # 创建内存处理器（StringIO）来临时存储日志
        import io
        self.log_buffer = io.StringIO()
        memory_handler = logging.StreamHandler(self.log_buffer)
        memory_handler.setLevel(logging.DEBUG)
        
        # 创建详细格式器
        battle_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        memory_handler.setFormatter(battle_formatter)
        
        self.battle_logger.addHandler(memory_handler)
        
        # 启用详细日志记录
        self.detailed_logging_enabled = True
        
        # 记录对战开始信息
        self.battle_logger.info(f"=== 对战开始 ===")
        self.battle_logger.info(f"对战ID: {self.battle_id}")
        self.battle_logger.info(f"对战标签: {battle.battle_tag}")
        self.battle_logger.info(f"对手: {getattr(battle, 'opponent_username', 'Unknown')}")
        
        # 记录我方队伍
        my_pokemon, _ = get_active_pokemon(battle)
        if my_pokemon:
            self.battle_logger.info(f"我方首发: {my_pokemon.species} (HP: {my_pokemon.current_hp_fraction:.2f})")
        
        # 记录对手队伍
        _, opp_pokemon = get_active_pokemon(battle)
        if opp_pokemon:
            self.battle_logger.info(f"对手首发: {opp_pokemon.species} (HP: {opp_pokemon.current_hp_fraction:.2f})")
            self.battle_logger.info(f"对手招式: {[str(move) for move in opp_pokemon.moves.values()]}")
        
        # 记录基本信息到主日志
        self.main_logger.info(f"开始对战: {self.battle_id} vs {getattr(battle, 'opponent_username', 'Unknown')}")

    def log_decision(self, battle: AbstractBattle, action, decision_time: float, strategy_info: Dict = None):
        """记录决策过程 - 只在详细日志启用时记录"""
        # 记录性能统计（无论是否启用详细日志）
        self.performance_stats['total_decision_time'] += decision_time
        
        # 只在详细日志启用时记录详细信息
        if not self.detailed_logging_enabled or not self.battle_logger:
            return
            
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        
        self.battle_logger.info(f"--- 第 {battle.turn} 回合 ---")
        self.battle_logger.info(f"决策时间: {decision_time:.3f}秒")
        
        if my_pokemon:
            self.battle_logger.info(f"我方状态: {my_pokemon.species} HP:{my_pokemon.current_hp_fraction:.2f} 状态:{my_pokemon.status}")
        if opp_pokemon:
            self.battle_logger.info(f"对手状态: {opp_pokemon.species} HP:{opp_pokemon.current_hp_fraction:.2f} 状态:{opp_pokemon.status}")
        
        self.battle_logger.info(f"选择动作: {action}")
        
        if strategy_info:
            self.battle_logger.info(f"策略信息: {strategy_info}")

    def log_damage_calculation(self, move: Move, target: Pokemon, damage_info: Dict):
        """记录伤害计算 - 只在详细日志启用时记录"""
        # 记录性能统计（无论是否启用详细日志）
        self.performance_stats['damage_calculations'] += 1
        
        # 只在详细日志启用时记录详细信息
        if not self.detailed_logging_enabled or not self.battle_logger:
            return
        
        self.battle_logger.debug(f"伤害计算: {move} -> {target.species}")
        self.battle_logger.debug(f"  基础威力: {move.base_power}")
        self.battle_logger.debug(f"  期望伤害: {damage_info['mean_damage']:.1f}")
        self.battle_logger.debug(f"  KO概率: {damage_info['ko_prob']:.2f}")

    def log_ko_prediction(self, predicted_ko: bool, actual_ko: bool):
        """记录KO预测"""
        self.performance_stats['ko_predictions'] += 1
        if predicted_ko == actual_ko:
            self.performance_stats['correct_ko_predictions'] += 1

    def end_battle_logging(self, battle: AbstractBattle, won: bool):
        """结束对战日志记录"""
        battle_duration = time.time() - self.battle_start_time
        
        # 更新性能统计
        self.performance_stats['total_battles'] += 1
        if won:
            self.performance_stats['wins'] += 1
        else:
            self.performance_stats['losses'] += 1
        self.performance_stats['total_turns'] += battle.turn
        
        # 记录对手类型
        _, opp_pokemon = get_active_pokemon(battle)
        if opp_pokemon:
            opp_type = str(opp_pokemon.species)
            self.performance_stats['opponent_types'][opp_type] = self.performance_stats['opponent_types'].get(opp_type, 0) + 1
        
        # 如果战斗失败，保存详细日志到文件
        if not won:
            self.save_detailed_battle_log(battle, battle_duration)
        
        # 记录结果到主日志
        self.main_logger.info(f"对战结束: {self.battle_id} - {'胜利' if won else '失败'} ({battle.turn}回合, {battle_duration:.2f}秒)")
        
        # 更新总体性能统计
        self.update_performance_summary()

    def save_detailed_battle_log(self, battle: AbstractBattle, battle_duration: float):
        """保存失败的战斗详细日志到文件"""
        if not hasattr(self, 'log_buffer') or not self.battle_logger:
            return
        
        # 记录对战结束信息到内存日志
        self.battle_logger.info(f"=== 对战结束 ===")
        self.battle_logger.info(f"结果: 失败")
        self.battle_logger.info(f"对战时长: {battle_duration:.2f}秒")
        self.battle_logger.info(f"总回合数: {battle.turn}")
        
        # 将内存中的日志内容写入文件
        battle_log_file = os.path.join(self.results_dir, f'{self.battle_id}.log')
        with open(battle_log_file, 'w', encoding='utf-8') as f:
            f.write(self.log_buffer.getvalue())
        
        # 清理内存缓冲区
        self.log_buffer.close()
        self.log_buffer = None

    def update_performance_summary(self):
        """更新性能汇总文件"""
        summary_file = os.path.join(self.results_dir, 'performance_summary.json')
        
        # 计算胜率
        win_rate = self.performance_stats['wins'] / self.performance_stats['total_battles'] if self.performance_stats['total_battles'] > 0 else 0
        
        # 计算平均决策时间
        avg_decision_time = self.performance_stats['total_decision_time'] / self.performance_stats['total_turns'] if self.performance_stats['total_turns'] > 0 else 0
        
        # 计算KO预测准确率
        ko_accuracy = self.performance_stats['correct_ko_predictions'] / self.performance_stats['ko_predictions'] if self.performance_stats['ko_predictions'] > 0 else 0
        
        performance_summary = {
            'total_battles': self.performance_stats['total_battles'],
            'wins': self.performance_stats['wins'],
            'losses': self.performance_stats['losses'],
            'win_rate': win_rate,
            'total_turns': self.performance_stats['total_turns'],
            'avg_decision_time': avg_decision_time,
            'damage_calculations': self.performance_stats['damage_calculations'],
            'ko_predictions': self.performance_stats['ko_predictions'],
            'ko_accuracy': ko_accuracy,
            'strategy_usage': self.performance_stats['strategy_usage'],
            'opponent_types': self.performance_stats['opponent_types'],
            'last_updated': datetime.now().isoformat()
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(performance_summary, f, indent=2, ensure_ascii=False)

    def _battle_finished_callback(self, battle: AbstractBattle):
        """战斗结束时的回调函数，用于清理状态"""
        # 记录对战结果
        won = battle.won
        self.end_battle_logging(battle, won)
        
        # 清理对战状态
        self.battle_state = {}
        self.combo_confidences = {}
        self.phase_weights = {}
        self.status_adjustments = {}
        self.battle_logger = None
        self.battle_id = None
        self.detailed_logging_enabled = False
        
        # 清理内存缓冲区（如果存在）
        if hasattr(self, 'log_buffer') and self.log_buffer:
            self.log_buffer.close()
            self.log_buffer = None
        
        # 调用父类的清理方法
        super()._battle_finished_callback(battle)

    def choose_move(self, battle: AbstractBattle):
        # 开始计时
        decision_start_time = time.time()
        
        # 如果是第一回合，开始对战日志记录
        if battle.turn == 1 and not self.battle_logger:
            self.start_battle_logging(battle)
        
        # **状态更新**：首先更新对战状态
        self.update_battle_state(battle)
        
        # **强制换人判断**：检查是否必须换人
        if battle.force_switch:
            # 如果必须换人，选择最佳换人
            if battle.available_switches:
                action = self.choose_best_switch(battle.available_switches)
                decision_time = time.time() - decision_start_time
                self.log_decision(battle, action, decision_time, {'reason': 'force_switch'})
                return action
            else:
                # 如果没有可用的换人选项，使用随机选择
                action = self.choose_random_move(battle.available_moves)
                decision_time = time.time() - decision_start_time
                self.log_decision(battle, action, decision_time, {'reason': 'force_switch_no_switches'})
                return action
        
        # **濒死判断**：是 AI 的第一个分支点（Switch vs. Move）
        my_pokemon, _ = get_active_pokemon(battle)
        if not my_pokemon or my_pokemon.fainted:
            # 如果 active_pokemon 不存在或为 None，尝试切换
            if battle.available_switches:
                action = self.choose_best_switch(battle.available_switches)
                decision_time = time.time() - decision_start_time
                self.log_decision(battle, action, decision_time, {'reason': 'pokemon_fainted'})
                return action
            else:
                # 如果没有可用的换人选项，使用随机招式
                action = self.choose_random_move(battle.available_moves)
                decision_time = time.time() - decision_start_time
                self.log_decision(battle, action, decision_time, {'reason': 'pokemon_fainted_no_switches'})
                return action

        # **异常状态修正**：必须要有，否则 AI 会傻乎乎地让睡着的宝可梦硬抗
        self.adjust_for_status(my_pokemon)
        
        # 优先尝试高伤害攻击
        high_damage_action = self.choose_high_damage_move(battle)
        if high_damage_action:
            decision_time = time.time() - decision_start_time
            self.log_decision(battle, high_damage_action, decision_time, {'reason': 'high_damage_priority'})
            return high_damage_action
        
        # 执行完整的策略pipeline（保持原有复杂逻辑）
        best_action = self.execute_strategy_pipeline(battle)

        if best_action:
            # 记录行为用于学习
            self.record_action(best_action, battle)
            decision_time = time.time() - decision_start_time
            self.log_decision(battle, best_action, decision_time, {'reason': 'strategy_pipeline'})
            return best_action

        if battle.available_switches:
            action = self.choose_best_switch(battle.available_switches)
            decision_time = time.time() - decision_start_time
            self.log_decision(battle, action, decision_time, {'reason': 'fallback_switch'})
            return action
        
        # 如果策略pipeline返回None，使用随机选择作为后备
        action = self.choose_random_move(battle.available_moves)
        decision_time = time.time() - decision_start_time
        self.log_decision(battle, action, decision_time, {'reason': 'fallback_random'})
        return action
    
    def adjust_for_status(self, pokemon):
        """异常状态修正"""
        # 根据异常状态调整策略
        if pokemon.status == 'slp':
            # 睡眠状态：优先使用攻击招式，避免使用需要精确时机的招式
            self.status_adjustments = {
                'prefer_attacking': True,
                'avoid_setup': True,
                'consider_switch': False
            }
        elif pokemon.status == 'par':
            # 麻痹状态：考虑换人，避免使用速度依赖的招式
            self.status_adjustments = {
                'prefer_attacking': False,
                'avoid_setup': True,
                'consider_switch': True
            }
        elif pokemon.status == 'brn':
            # 烧伤状态：优先换人，避免物理攻击
            self.status_adjustments = {
                'prefer_attacking': False,
                'avoid_physical': True,
                'consider_switch': True
            }
        elif pokemon.status == 'psn' or pokemon.status == 'tox':
            # 中毒状态：考虑换人，避免拖延
            self.status_adjustments = {
                'prefer_attacking': True,
                'avoid_stalling': True,
                'consider_switch': True
            }
        elif pokemon.status == 'frz':
            # 冰冻状态：优先换人
            self.status_adjustments = {
                'prefer_attacking': False,
                'consider_switch': True
            }
        else:
            # 无异常状态
            self.status_adjustments = {
                'prefer_attacking': False,
                'avoid_setup': False,
                'consider_switch': False
            }


    def execute_strategy_pipeline(self, battle: AbstractBattle):
        """主决策函数 - 实现完整的对战策略pipeline"""
        # 1. 感知模块 - 更新对战状态
        self.update_battle_state(battle)
        
        # 2. 组合识别
        detected_combos = self.combo_detector(battle)
        
        # 3. 阶段判定
        phase, phase_weights = self.phase_detector(battle)
        
        # 4. 对手预测
        opp_move_dist, opp_switch_probs = self.opponent_model(battle)
        
        # 5. 战术选择
        strategic_target, priority_actions, tactical_weights = self.strategic_layer(battle, detected_combos, phase_weights)
        
        # 6. 战术评估
        action_utilities = self.tactical_layer(battle, opp_move_dist, strategic_target, tactical_weights)
        
        # 7. 换人判定 - "是否换人"的问题（逻辑判定）
        switch_evaluation = self.switch_evaluator(battle, opp_switch_probs)
        
        # 8. 动作执行
        best_action = self.executor(battle, action_utilities, switch_evaluation, priority_actions)
        
        return best_action

    # ============================== 1. 感知模块 ==============================
    def update_battle_state(self, battle: AbstractBattle):
        """更新对战状态和对手历史行为"""
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        
        # 更新对手威胁等级
        self.opponent_threat_level = self.assess_opponent_threat(battle)
        
        self.battle_state = {
            'my_hp': my_pokemon.current_hp / my_pokemon.max_hp if my_pokemon else 0.0,
            'opp_hp': opp_pokemon.current_hp / opp_pokemon.max_hp if opp_pokemon else 0.0,
            'my_status': my_pokemon.status if my_pokemon else None,
            'opp_status': opp_pokemon.status if opp_pokemon else None,
            'my_remaining': len([p for p in battle.team.values() if not p.fainted]),
            'opp_remaining': len([p for p in battle.opponent_team.values() if not p.fainted]),
            'turn_count': battle.turn,
            'weather': battle.weather,
            # 场地效果
            'terrain': next((field.name.lower().replace('_', ' ') for field in battle.fields.keys() if field.is_terrain), None),
            # 我方和对方场地陷阱
            'hazards_my_side': self.get_hazards(battle, my_side=True),
            'hazards_opp_side': self.get_hazards(battle, my_side=False),
            'opponent_threat': self.opponent_threat_level
        }

    def get_hazards(self, battle: AbstractBattle, my_side: bool) -> List[str]:
        """获取场地状态"""
        hazards = []
        if my_side:
            if battle.side_conditions.get('stealthrock', 0) > 0:
                hazards.append('stealthrock')
            if battle.side_conditions.get('spikes', 0) > 0:
                hazards.append('spikes')
            if battle.side_conditions.get('toxicspikes', 0) > 0:
                hazards.append('toxicspikes')
        else:
            if battle.opponent_side_conditions.get('stealthrock', 0) > 0:
                hazards.append('stealthrock')
            if battle.opponent_side_conditions.get('spikes', 0) > 0:
                hazards.append('spikes')
            if battle.opponent_side_conditions.get('toxicspikes', 0) > 0:
                hazards.append('toxicspikes')
        return hazards

    def assess_opponent_threat(self, battle: AbstractBattle) -> str:
        """评估对手威胁等级"""
        _, opp_pokemon = get_active_pokemon(battle)
        if not opp_pokemon:
            return 'medium'
        
        # 检查是否为传说宝可梦
        legendary_pokemon = ['arceus', 'zacian', 'koraidon', 'rayquaza', 'necrozma', 'eternatus', 'deoxys', 'kingambit']
        if any(legend in str(opp_pokemon.species).lower() for legend in legendary_pokemon):
            return 'high'
        
        # 检查种族值总和
        if hasattr(opp_pokemon, 'base_stats'):
            total_stats = sum(opp_pokemon.base_stats.values())
            if total_stats > 600:
                return 'high'
            elif total_stats > 500:
                return 'medium'
            else:
                return 'low'
        
        return 'medium'

    # ============================== 2. 组合识别模块 ==============================
    def combo_detector(self, battle: AbstractBattle) -> Dict[str, float]:
        """检测对手可能的组合策略 - 战术反应引擎"""
        combos = {
            'entry_hazard': 0.0,      # 开场撒钉
            'sweep_setup': 0.0,       # 强化推队
            'status_stall': 0.0,      # 状态受队
            'hazard_control': 0.0,    # 场地控制
            'weather_sweep': 0.0,     # 天气推队
            'trick_room': 0.0,        # 空间队
            'dual_screen': 0.0,       # 双墙队
            'perish_trap': 0.0,       # 灭亡歌陷阱
            'baton_pass': 0.0,        # 接力队
            'priority_finish': 0.0,   # 先制收割
            'stall_recovery': 0.0,    # 回复受队
            'nu_stall': 0.0,          # NU受队
            'ru_balance': 0.0,        # RU平衡队
            'uu_offense': 0.0         # UU进攻队
        }
        
        _, opp_pokemon = get_active_pokemon(battle)
        if not opp_pokemon:
            return combos  # 如果对手宝可梦不存在，返回空组合

        opp_moves = [str(move).lower() for move in opp_pokemon.moves.values()]
        opp_species = str(opp_pokemon.species).lower()
        
        # 检测开场撒钉组合
        if any(move in opp_moves for move in HAZARD_MOVES):
            combos['entry_hazard'] += 0.4
            if battle.turn <= 3:  # 开场阶段更可能是撒钉
                combos['entry_hazard'] += 0.3
        
        # 检测强化推队组合
        if any(move in opp_moves for move in SETUP_MOVES):
            combos['sweep_setup'] += 0.5
            # 如果同时有高威力招式，更可能是推队
            high_power_moves = [move for move in opp_moves if any(power in move for power in HIGH_POWER_MOVE_KEYWORDS)]
            if high_power_moves:
                combos['sweep_setup'] += 0.2
        
        # 检测状态受队组合
        if any(move in opp_moves for move in STALL_MOVES):
            combos['status_stall'] += 0.3
            # 如果有剩饭道具特征
            if hasattr(opp_pokemon, 'item') and 'leftovers' in str(opp_pokemon.item).lower():
                combos['status_stall'] += 0.2
        
        # 检测天气推队组合
        if any(move in opp_moves for move in WEATHER_MOVES) or battle.weather:
            combos['weather_sweep'] += 0.4
            # 特定天气宝可梦
            if any(sweeper in opp_species for sweeper in WEATHER_SWEEPERS):
                combos['weather_sweep'] += 0.3
        
        # 检测空间队组合
        if 'trickroom' in opp_moves:
            combos['trick_room'] += 0.6
            # 慢速宝可梦更可能是空间队
            if opp_pokemon.base_stats.get('speed', 0) < 80:
                combos['trick_room'] += 0.2
        
        # 检测双墙队组合
        if any(move in opp_moves for move in SCREEN_MOVES):
            combos['dual_screen'] += 0.4
        
        # 检测灭亡歌陷阱组合
        if any(move in opp_moves for move in TRAP_MOVES):
            combos['perish_trap'] += 0.5
        
        # 检测接力队组合
        if 'batonpass' in opp_moves:
            combos['baton_pass'] += 0.6
            # 如果有强化招式，更可能是接力
            if any(move in opp_moves for move in SETUP_MOVES):
                combos['baton_pass'] += 0.2
        
        # 检测先制收割组合
        if any(move in opp_moves for move in PRIORITY_MOVES):
            combos['priority_finish'] += 0.4
        
        # 检测回复受队组合
        if any(move in opp_moves for move in RECOVERY_MOVES):
            combos['stall_recovery'] += 0.3
            # 高耐久宝可梦更可能是受队
            if opp_pokemon.base_stats.get('hp', 0) > 100 and opp_pokemon.base_stats.get('defense', 0) > 100:
                combos['stall_recovery'] += 0.2
        
        # 检测NU受队模式
        if self.detect_nu_stall_pattern(opp_pokemon, opp_moves):
            combos['nu_stall'] = 0.6
        
        # 检测RU平衡队模式
        if self.detect_ru_balance_pattern(opp_pokemon, opp_moves):
            combos['ru_balance'] = 0.5
        
        # 检测UU进攻队模式
        if self.detect_uu_offense_pattern(opp_pokemon, opp_moves):
            combos['uu_offense'] = 0.5
        
        return combos

    def detect_nu_stall_pattern(self, pokemon, moves):
        """检测NU受队模式"""
        # NU受队特征：高耐久、回复技能、状态技能
        stall_indicators = 0
        
        # 检查耐久度
        if hasattr(pokemon, 'base_stats'):
            hp = pokemon.base_stats.get('hp', 0)
            defense = pokemon.base_stats.get('defense', 0)
            sp_defense = pokemon.base_stats.get('special-defense', 0)
            if hp > 80 and (defense > 80 or sp_defense > 80):
                stall_indicators += 1
        
        # 检查回复技能
        recovery_moves = ['recover', 'roost', 'synthesis', 'moonlight', 'rest', 'slackoff']
        if any(move in moves for move in recovery_moves):
            stall_indicators += 1
        
        # 检查状态技能
        status_moves = ['toxic', 'willowisp', 'thunderwave', 'hypnosis', 'sleepspore']
        if any(move in moves for move in status_moves):
            stall_indicators += 1
        
        # 检查保护技能
        protection_moves = ['protect', 'detect', 'substitute']
        if any(move in moves for move in protection_moves):
            stall_indicators += 1
        
        return stall_indicators >= 2

    def detect_ru_balance_pattern(self, pokemon, moves):
        """检测RU平衡队模式"""
        # RU平衡队特征：中等威力、控制技能、换人技能
        balance_indicators = 0
        
        # 检查换人技能
        switch_moves = ['uturn', 'voltswitch', 'partingshot', 'teleport']
        if any(move in moves for move in switch_moves):
            balance_indicators += 1
        
        # 检查控制技能
        control_moves = ['taunt', 'encore', 'haze', 'roar', 'whirlwind']
        if any(move in moves for move in control_moves):
            balance_indicators += 1
        
        # 检查场地技能
        field_moves = ['stealthrock', 'spikes', 'toxicspikes', 'defog', 'rapidspin']
        if any(move in moves for move in field_moves):
            balance_indicators += 1
        
        return balance_indicators >= 2

    def detect_uu_offense_pattern(self, pokemon, moves):
        """检测UU进攻队模式"""
        # UU进攻队特征：高威力、强化技能、先制技能
        offense_indicators = 0
        
        # 检查强化技能
        setup_moves = ['swordsdance', 'dragondance', 'quiverdance', 'calmmind', 'nastyplot']
        if any(move in moves for move in setup_moves):
            offense_indicators += 1
        
        # 检查高威力技能
        high_power_moves = [move for move in moves if any(keyword in move for keyword in ['blast', 'cannon', 'strike', 'claw', 'punch'])]
        if high_power_moves:
            offense_indicators += 1
        
        # 检查先制技能
        priority_moves = ['extremespeed', 'suckerpunch', 'bulletpunch', 'machpunch', 'vacuumwave']
        if any(move in moves for move in priority_moves):
            offense_indicators += 1
        
        return offense_indicators >= 2

    # ============================== 3. 阶段判定模块 ==============================
    def phase_detector(self, battle: AbstractBattle) -> Tuple[str, Dict[str, float]]:
        """判定游戏阶段并返回权重"""
        my_remaining = self.battle_state['my_remaining']
        opp_remaining = self.battle_state['opp_remaining']
        turn_count = self.battle_state['turn_count']
        
        # 阶段判定逻辑
        if turn_count <= 5 or (my_remaining >= 5 and opp_remaining >= 5):
            phase = 'early'
            weights = {'offense': 0.3, 'defense': 0.2, 'setup': 0.3, 'disruption': 0.1, 'hazard_control': 0.1}
        elif my_remaining <= 2 or opp_remaining <= 2:
            phase = 'late'
            weights = {'offense': 0.5, 'defense': 0.3, 'setup': 0.1, 'disruption': 0.05, 'hazard_control': 0.05}
        else:
            phase = 'mid'
            weights = {'offense': 0.4, 'defense': 0.25, 'setup': 0.2, 'disruption': 0.1, 'hazard_control': 0.05}
        
        return phase, weights

    # ============================== 4. 对手预测模块 ==============================
    def opponent_model(self, battle: AbstractBattle) -> Tuple[List[Dict], List[Dict]]:
        """预测对手的招式和换人概率"""
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        
        if not my_pokemon or not opp_pokemon:
            return [], []
        
        # 基于属性相克和常见策略的简单预测
        opp_moves = []
        for move in opp_pokemon.moves.values():
            # PP是每个招式可以使用的次数限制，看一下是否还能使用
            if move.current_pp > 0:
                # 基于属性相克计算使用概率
                opponent_model_effectiveness = self.calculate_move_effectiveness(move, my_pokemon)
                
                # 提高基础概率，更符合实际对战
                if opponent_model_effectiveness >= 4.0:  # 4倍克制
                    prob = 0.8
                elif opponent_model_effectiveness >= 2.0:  # 2倍克制
                    prob = 0.6
                elif opponent_model_effectiveness >= 1.0:  # 正常效果
                    prob = 0.4
                else:  # 效果不好
                    prob = 0.2
                
                # 根据招式威力调整
                if move.base_power >= 120:
                    prob += 0.1  # 高威力招式更可能使用
                elif move.base_power >= 80:
                    prob += 0.05
                
                # 根据招式类型调整
                move_name = str(move).lower()
                if move_name in ['recover', 'roost', 'synthesis']:
                    # 回复技能在低HP时更可能使用
                    if opp_pokemon.current_hp / opp_pokemon.max_hp < 0.5:
                        prob += 0.2
                
                opp_moves.append({'move': move, 'probability': min(prob, 0.8)})
        
        # 换人预测
        opp_switches = []
        for pokemon in battle.opponent_team.values():
            # 只有活着且不在场的宝可梦才能被换上来
            if not pokemon.fainted and pokemon != opp_pokemon:
                # 基于属性相克计算换人概率
                switch_prob = self.calculate_switch_probability(pokemon, my_pokemon)
                opp_switches.append({'species': pokemon.species, 'probability': switch_prob})
        
        return opp_moves, opp_switches

    def calculate_switch_probability(self, pokemon: Pokemon, my_active: Pokemon) -> float:
        """计算对手换人概率"""
        if not pokemon.types or not my_active.types:
            return 0.1
        
        # 计算对手宝可梦对我方当前宝可梦的抗性
        resistance = 1.0
        for my_type in my_active.types:
            for opp_type in pokemon.types:
                eff = get_type_effectiveness(my_type.name.upper(), opp_type.name.upper())
                resistance *= eff
        
        # 抗性越好，换人概率越高
        if resistance <= 0.25:  # 4倍抗性
            return 0.8
        elif resistance <= 0.5:  # 2倍抗性
            return 0.6
        elif resistance < 1.0:  # 1.5倍抗性
            return 0.4
        elif resistance == 1.0:  # 正常效果
            return 0.2
        else:  # 被克制
            return 0.1

    # ============================== 5. 战术选择模块 ==============================
    def strategic_layer(self, battle: AbstractBattle, detected_combos: Dict, phase_weights: Dict) -> Tuple[str, List[str], Dict]:
        """战略层决策 - 根据组合识别选择应对策略"""
        # 找出置信度最高的组合
        max_combo = max(detected_combos.items(), key=lambda x: x[1])
        combo_type, confidence = max_combo
        
        # 根据组合类型和置信度选择策略配置
        if combo_type in STRATEGIC_TARGETS and confidence > STRATEGY_CONFIDENCE_THRESHOLDS.get(combo_type, 0.5):
            strategy_config = STRATEGIC_TARGETS[combo_type]
        else:
            strategy_config = STRATEGIC_TARGETS['default']
        
        return strategy_config['target'], strategy_config['priority_actions'], strategy_config['tactical_weights']

    # ============================== 6. 战术评估模块 ==============================
    def tactical_layer(self, battle: AbstractBattle, opp_move_dist: List, strategic_target: str, tactical_weights: Dict) -> List[Dict]:
        """战术层评估所有可用动作 - 基于技能分类的数值决策引擎"""
        action_utilities = []
        
        my_pokemon, _ = get_active_pokemon(battle)
        if not my_pokemon:
            return action_utilities
        
        # 评估所有可用招式
        for move in my_pokemon.moves.values():
            if move.current_pp > 0:
                utility = self.evaluate_action_utility(move, battle, opp_move_dist, strategic_target, tactical_weights)
                action_utilities.append({
                    'action': move,
                    'utility': utility,
                    'type': 'move',
                    'move_type': self.classify_move(move)
                })
        
        # 评估换人选项 - 换谁的问题 - 数值评估
        for switch in battle.available_switches:
            utility = self.evaluate_switch_utility(switch, battle, strategic_target)
            action_utilities.append({
                'action': switch,
                'utility': utility,
                'type': 'switch'
            })
        
        return action_utilities

    def evaluate_action_utility(self, move: Move, battle: AbstractBattle, opp_move_dist: List, 
                              strategic_target: str, tactical_weights: Dict) -> float:
        """改进的动作效用评估 - 加入生存机制和风险规避"""
        move_type = self.classify_move(move)
        utility = 0.0

        my_pokemon, opp_pokemon = get_active_pokemon(battle)

        # 安全获取宝可梦
        if not my_pokemon or not opp_pokemon:
            return utility
        
        my_hp_frac = my_pokemon.current_hp / my_pokemon.max_hp
        opp_hp_frac = opp_pokemon.current_hp / opp_pokemon.max_hp
        
        # 生存风险评估
        survival_risk = self.assess_survival_risk(battle, my_pokemon, opp_pokemon)
        
        # 基础伤害计算
        if move.base_power > 0:
            dmg_info = self.calculate_detailed_damage(move, opp_pokemon, battle)
            P_my_KO = dmg_info['ko_prob']
            E_dmg = dmg_info['mean_damage']
            
            # 记录伤害计算
            self.log_damage_calculation(move, opp_pokemon, dmg_info)
            
            # 攻击技能效用（根据生存风险调整）
            ko_value = tactical_weights['W_K'] * P_my_KO * 100.0
            dmg_value = tactical_weights['W_D'] * E_dmg * 0.1
            
            # 高生存风险时降低攻击价值
            if survival_risk > 0.7:
                ko_value *= 0.5
                dmg_value *= 0.7
            
            utility += ko_value + dmg_value
        
        # 计算对手反击风险
        P_opp_incoming_KO = 0.0
        for opp_move in opp_move_dist:
            if opp_move['probability'] > 0.1:
                opp_dmg_info = self.calculate_detailed_damage(
                    opp_move['move'], my_pokemon, battle
                )
                P_opp_incoming_KO += opp_move['probability'] * opp_dmg_info['ko_prob']
        
        # 风险惩罚（根据生存风险调整）
        risk_penalty = tactical_weights['W_R'] * P_opp_incoming_KO * 50.0
        if survival_risk > 0.5:
            risk_penalty *= 1.5  # 高生存风险时增加风险惩罚
        utility -= risk_penalty
        
        # 根据技能类型添加特殊效用
        if move_type == 'setup':
            # 强化技能：考虑未来回合收益和生存风险
            setup_value = self.estimate_setup_value(move, battle, tactical_weights)
            if survival_risk > 0.6:  # 高生存风险时降低强化价值
                setup_value *= 0.3
            utility += tactical_weights['W_S'] * setup_value
            
        elif move_type == 'recovery':
            # 回复技能：生存时间延长价值（高生存风险时更重要）
            recovery_value = self.estimate_recovery_value(move, battle)
            if survival_risk > 0.5:
                recovery_value *= 1.5  # 高生存风险时增加回复价值
            utility += recovery_value * 30.0
            
        elif move_type == 'status':
            # 状态技能：控制对手的价值
            status_value = self.estimate_status_value(move, battle, opp_move_dist)
            utility += status_value * 40.0
            
        elif move_type == 'field':
            # 场地技能：全局长期价值
            field_value = self.estimate_field_value(move, battle, strategic_target)
            utility += tactical_weights['W_F'] * field_value
            
        elif move_type == 'protection':
            # 保护技能：防御和探招价值（高生存风险时更重要）
            protection_value = self.estimate_protection_value(move, battle, opp_move_dist)
            if survival_risk > 0.6:
                protection_value *= 2.0  # 高生存风险时大幅增加保护价值
            utility += protection_value * 20.0
            
        elif move_type == 'priority':
            # 先制技能：确保先手价值
            priority_value = self.estimate_priority_value(move, battle)
            utility += priority_value * 25.0
        
        # 异常状态调整
        if hasattr(self, 'status_adjustments'):
            utility = self.apply_status_adjustments(utility, move, move_type)
        
        # 生存机制调整
        utility = self.apply_survival_adjustments(utility, move, move_type, survival_risk, my_hp_frac)
        
        return utility

    def assess_survival_risk(self, battle: AbstractBattle, my_pokemon: Pokemon, opp_pokemon: Pokemon) -> float:
        """评估生存风险（0-1，越高越危险）"""
        risk = 0.0
        
        # 1. HP风险
        my_hp_frac = my_pokemon.current_hp / my_pokemon.max_hp
        if my_hp_frac < 0.2:
            risk += 0.6
        elif my_hp_frac < 0.4:
            risk += 0.4
        elif my_hp_frac < 0.6:
            risk += 0.2
        
        # 2. 属性克制风险
        if self.is_severely_weak_to_opponent(battle):
            risk += 0.4
        
        # 3. 对手威胁风险
        if self.opponent_has_high_threat_moves(battle):
            risk += 0.3
        
        # 4. 速度劣势风险
        my_speed = my_pokemon.base_stats.get('speed', 0)
        opp_speed = opp_pokemon.base_stats.get('speed', 0)
        if opp_speed > my_speed * 1.2:  # 对手明显更快
            risk += 0.2
        
        # 5. 异常状态风险
        if my_pokemon.status in ['slp', 'frz', 'par']:
            risk += 0.3
        
        return min(risk, 1.0)

    def apply_survival_adjustments(self, utility: float, move: Move, move_type: str, survival_risk: float, my_hp_frac: float) -> float:
        """应用生存机制调整"""
        # 高生存风险时的调整
        if survival_risk > 0.7:
            if move_type in ['physical_attack', 'special_attack']:
                utility *= 0.3  # 大幅降低攻击技能价值
            elif move_type == 'setup':
                utility *= 0.1  # 几乎不使用强化技能
            elif move_type in ['recovery', 'protection']:
                utility *= 2.0  # 大幅增加生存技能价值
        
        # 低HP时的调整
        if my_hp_frac < 0.3:
            if move_type in ['recovery', 'protection']:
                utility += 50.0  # 大幅增加生存技能价值
            elif move_type in ['physical_attack', 'special_attack']:
                utility -= 30.0  # 降低攻击技能价值
        
        return utility

    def calculate_detailed_damage(self, move: Move, target: Pokemon, battle: AbstractBattle) -> Dict:
        """改进的伤害计算 - 修复类型相克和KO预测"""
        if move.base_power == 0:
            return {'ko_prob': 0.0, 'mean_damage': 0.0, 'min_damage': 0.0, 'max_damage': 0.0}
        
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        if not my_pokemon or not opp_pokemon:
            return {'ko_prob': 0.0, 'mean_damage': 0.0, 'min_damage': 0.0, 'max_damage': 0.0}
        
        # 基础威力
        base_power = move.base_power
        
        # 类型相克 - 使用更准确的计算
        try:
            type_effectiveness = float(target.damage_multiplier(move))
        except:
            type_effectiveness = self.calculate_move_effectiveness(move, target)
        
        # 如果类型相克为0，直接返回0伤害
        if type_effectiveness == 0:
            return {'ko_prob': 0.0, 'mean_damage': 0.0, 'min_damage': 0.0, 'max_damage': 0.0}
        
        # STAB加成
        stab_multiplier = 1.0
        if move.type and my_pokemon.types:
            for my_type in my_pokemon.types:
                if move.type.name.upper() == my_type.name.upper():
                    stab_multiplier = 1.5
                    break
        
        # 改进的伤害计算 - 使用更合理的公式
        # 基础伤害 = 基础威力 * 类型相克 * STAB * 等级修正
        level_factor = 0.44  # 等级50的修正因子
        base_damage = base_power * level_factor * type_effectiveness * stab_multiplier
        
        # 随机因子（85%-100%）
        min_damage = base_damage * 0.85
        max_damage = base_damage * 1.0
        mean_damage = (min_damage + max_damage) / 2
        
        # 改进的KO概率计算
        target_current_hp = target.current_hp
        
        if mean_damage >= target_current_hp:
            ko_prob = 0.95  # 期望伤害足够KO
        elif max_damage >= target_current_hp:
            ko_prob = 0.75  # 最大伤害可能KO
        elif min_damage >= target_current_hp:
            ko_prob = 0.25  # 最小伤害可能KO
        else:
            # 基于伤害比例估算KO概率
            damage_ratio = mean_damage / target_current_hp if target_current_hp > 0 else 0
            if damage_ratio >= 0.8:
                ko_prob = 0.6
            elif damage_ratio >= 0.6:
                ko_prob = 0.4
            elif damage_ratio >= 0.4:
                ko_prob = 0.2
            else:
                ko_prob = 0.1
        
        return {
            'ko_prob': min(ko_prob, 1.0),
            'mean_damage': max(mean_damage, 0.0),
            'min_damage': max(min_damage, 0.0),
            'max_damage': max(max_damage, 0.0)
        }

    def estimate_setup_value(self, move: Move, battle: AbstractBattle, tactical_weights: Dict) -> float:
        """估算强化技能的未来价值"""
        move_name = str(move).lower()
        
        # 不同强化技能的价值
        setup_values = {
            'swordsdance': 50.0,      # 物攻+2
            'dragondance': 60.0,      # 物攻+1 速度+1
            'quiverdance': 70.0,      # 特攻+1 特防+1 速度+1
            'calmmind': 40.0,         # 特攻+1 特防+1
            'nastyplot': 45.0,        # 特攻+2
            'bulkup': 35.0,           # 物攻+1 物防+1
            'agility': 30.0,          # 速度+2
        }
        
        base_value = setup_values.get(move_name, 20.0)
        
        # 安全获取我方宝可梦
        my_pokemon, _ = get_active_pokemon(battle)
        
        if my_pokemon:
            # 根据当前HP调整价值
            my_hp_frac = my_pokemon.current_hp / my_pokemon.max_hp
            if my_hp_frac < 0.5:
                base_value *= 0.5  # 低HP时强化价值降低
        
        return base_value

    def estimate_recovery_value(self, move: Move, battle: AbstractBattle) -> float:
        """估算回复技能的生存价值"""
        move_name = str(move).lower()
        
        # 不同回复技能的恢复量
        recovery_amounts = {
            'recover': 0.5,           # 恢复50%HP
            'roost': 0.5,             # 恢复50%HP
            'synthesis': 0.5,         # 恢复50%HP
            'moonlight': 0.5,         # 恢复50%HP
            'rest': 1.0,              # 完全恢复但睡眠
            'slackoff': 0.5,          # 恢复50%HP
        }
        
        recovery_frac = recovery_amounts.get(move_name, 0.3)
        
        # 安全获取我方宝可梦
        my_pokemon, _ = get_active_pokemon(battle)
        
        if my_pokemon:
            # 根据当前HP需求调整价值
            my_hp_frac = my_pokemon.current_hp / my_pokemon.max_hp
            if my_hp_frac < 0.3:
                return recovery_frac * 100.0  # 低HP时回复价值很高
            elif my_hp_frac < 0.6:
                return recovery_frac * 50.0   # 中等HP时回复价值中等
            else:
                return recovery_frac * 20.0   # 高HP时回复价值较低
        else:
            return recovery_frac * 20.0   # 默认价值

    def estimate_status_value(self, move: Move, battle: AbstractBattle, opp_move_dist: List) -> float:
        """估算状态技能的控制价值"""
        move_name = str(move).lower()
        
        # 不同状态技能的价值
        status_values = {
            'thunderwave': 40.0,      # 麻痹：速度减半，25%无法行动
            'willowisp': 35.0,        # 烧伤：物攻减半，每回合扣血
            'toxic': 30.0,            # 中毒：每回合递增扣血
            'hypnosis': 50.0,         # 睡眠：无法行动2-4回合
            'sleepspore': 45.0,       # 睡眠：无法行动2-4回合
            'spore': 60.0,            # 睡眠：无法行动2-4回合（100%命中）
            'taunt': 25.0,            # 挑衅：无法使用非攻击技能
            'encore': 30.0,           # 再来一次：重复使用同一技能
        }
        
        base_value = status_values.get(move_name, 20.0)
        
        # 根据对手威胁度调整价值
        opp_threat = sum(opp_move['probability'] for opp_move in opp_move_dist if opp_move['probability'] > 0.3)
        if opp_threat > 0.5:
            base_value *= 1.5  # 高威胁对手时状态技能价值更高
        
        return base_value

    def estimate_field_value(self, move: Move, battle: AbstractBattle, strategic_target: str) -> float:
        """估算场地技能的全局价值"""
        move_name = str(move).lower()
        
        # 根据战略目标调整场地技能价值
        if strategic_target == 'hazard_control':
            if move_name in ['defog', 'rapidspin']:
                return 60.0  # 清场技能在场地控制目标下价值很高
            elif move_name in ['stealthrock', 'spikes', 'toxicspikes']:
                return 40.0  # 撒钉技能价值中等
        elif strategic_target == 'setup_disrupt':
            if move_name == 'taunt':
                return 50.0  # 挑衅在打断目标下价值很高
        
        # 默认场地技能价值
        field_values = {
            'stealthrock': 30.0,
            'spikes': 25.0,
            'toxicspikes': 20.0,
            'defog': 35.0,
            'rapidspin': 30.0,
            'trickroom': 40.0,
            'lightscreen': 25.0,
            'reflect': 25.0,
        }
        
        return field_values.get(move_name, 15.0)

    def estimate_protection_value(self, move: Move, battle: AbstractBattle, opp_move_dist: List) -> float:
        """估算保护技能的防御价值"""
        move_name = str(move).lower()
        
        # 根据对手威胁度调整保护价值
        high_threat_moves = [opp_move for opp_move in opp_move_dist if opp_move['probability'] > 0.4]
        if high_threat_moves:
            return 30.0  # 高威胁时保护价值高
        else:
            return 15.0  # 低威胁时保护价值低

    def estimate_priority_value(self, move: Move, battle: AbstractBattle) -> float:
        """估算先制技能的收割价值"""
        # 安全获取对手宝可梦
        opp_pokemon = getattr(battle, 'opponent_active_pokemon', None)
        if opp_pokemon is not None and hasattr(opp_pokemon, 'fainted'):
            opp_pokemon = cast(Pokemon, opp_pokemon)
        if not opp_pokemon:
            return 10.0  # 默认价值
        
        opp_hp_frac = opp_pokemon.current_hp / opp_pokemon.max_hp
        
        if opp_hp_frac < 0.3:
            return 50.0  # 对手低HP时先制技能价值很高
        elif opp_hp_frac < 0.6:
            return 25.0  # 对手中等HP时先制技能价值中等
        else:
            return 10.0  # 对手高HP时先制技能价值较低

    def apply_status_adjustments(self, utility: float, move: Move, move_type: str) -> float:
        """应用异常状态调整"""
        if self.status_adjustments.get('prefer_attacking', False) and move_type in ['physical_attack', 'special_attack']:
            utility += 20.0  # 睡眠状态优先攻击
        
        if self.status_adjustments.get('avoid_setup', False) and move_type == 'setup':
            utility -= 30.0  # 麻痹状态避免强化
        
        if self.status_adjustments.get('avoid_physical', False) and move_type == 'physical_attack':
            utility -= 25.0  # 烧伤状态避免物攻
        
        if self.status_adjustments.get('avoid_stalling', False) and move_type in ['recovery', 'protection']:
            utility -= 15.0  # 中毒状态避免拖延
        
        return utility

    # ============================== 7. 换人判定模块 ==============================
    def switch_evaluator(self, battle: AbstractBattle, opp_switch_probs: List) -> Dict:
        """改进的换人窗口判定 - 更智能的换人逻辑"""
        my_hp_frac = self.battle_state['my_hp']
        my_status = self.battle_state['my_status']
        opponent_threat = self.battle_state.get('opponent_threat', 'medium')
        turn_count = self.battle_state['turn_count']
        
        # 根据对手威胁度和对战阶段动态调整阈值 - 更保守的策略
        if opponent_threat == 'high':  # 高威胁对手（传说宝可梦等）
            urgent_hp_threshold = 0.10
            safe_hp_threshold = 0.50
        elif opponent_threat == 'medium':  # 中等威胁（OU级别）
            urgent_hp_threshold = 0.15
            safe_hp_threshold = 0.60
        else:  # 低威胁（NU/RU/UU级别）
            urgent_hp_threshold = 0.20
            safe_hp_threshold = 0.70
        
        # 根据对战阶段调整阈值
        if turn_count <= 5:  # 早期阶段更保守
            urgent_hp_threshold += 0.05
            safe_hp_threshold += 0.05
        elif turn_count >= 20:  # 后期阶段更激进
            urgent_hp_threshold -= 0.05
            safe_hp_threshold -= 0.05
        
        # 紧急换人判定（优先级最高）
        urgent_switch_needed = False
        urgent_reasons = []
        
        # 条件1：HP过低（根据威胁度和阶段调整）
        if my_hp_frac <= urgent_hp_threshold:
            urgent_switch_needed = True
            urgent_reasons.append('low_hp')
        
        # 条件2：被严重克制且对手速度更快
        if self.is_severely_weak_to_opponent(battle):
            urgent_switch_needed = True
            urgent_reasons.append('type_weakness')
        
        # 条件3：异常状态无法行动
        if my_status in ['slp', 'frz'] and not self.can_act_this_turn(battle):
            urgent_switch_needed = True
            urgent_reasons.append('status_paralysis')
        
        # 条件4：对手先制技能威胁
        if self.opponent_has_priority_threat(battle, opp_switch_probs):
            urgent_switch_needed = True
            urgent_reasons.append('priority_threat')
        
        # 条件5：对手有高威胁招式且我方无法有效反击
        if self.opponent_has_high_threat_moves(battle) and not self.can_effectively_counter(battle):
            urgent_switch_needed = True
            urgent_reasons.append('high_threat_moves')
        
        # 主动换人判定（安全窗口）
        safe_switch_window = False
        safe_reasons = []
        
        # 条件1：HP充足且有明显优势的换人选项
        if my_hp_frac >= safe_hp_threshold:
            if self.has_significant_advantage_switch_options(battle):
                safe_switch_window = True
                safe_reasons.append('high_hp_advantage')
        
        # 条件2：对手刚换入且可能不直接攻击
        if self.opponent_just_switched_and_may_not_attack(battle, opp_switch_probs):
            safe_switch_window = True
            safe_reasons.append('opponent_switch')
        
        # 条件3：有属性优势的换人选项且当前宝可梦效率不高
        if self.has_advantageous_switch_options(battle) and self.current_pokemon_ineffective(battle):
            safe_switch_window = True
            safe_reasons.append('type_advantage_ineffective')
        
        # 条件4：需要回复或清除状态
        if my_hp_frac < 0.6 and self.has_recovery_options(battle):
            safe_switch_window = True
            safe_reasons.append('need_recovery')
        
        return {
            'urgent_switch_needed': urgent_switch_needed,
            'urgent_reasons': urgent_reasons,
            'safe_switch_window': safe_switch_window,
            'safe_reasons': safe_reasons,
            'should_switch': urgent_switch_needed or safe_switch_window
        }

    def is_severely_weak_to_opponent(self, battle: AbstractBattle) -> bool:
        """检查是否被对手严重克制"""

        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        
        if not my_pokemon or not opp_pokemon or not my_pokemon.types or not opp_pokemon.types:
            return False
        
        # 计算对手招式对我方的相克效果
        max_effectiveness = 0.0
        for move in opp_pokemon.moves.values():
            if move.base_power > 0:
                effectiveness = self.calculate_move_effectiveness(move, my_pokemon)
                max_effectiveness = max(max_effectiveness, effectiveness)
        
        # 如果被4倍克制且对手速度更快，需要紧急换人
        if max_effectiveness >= 4.0:
            opp_speed = opp_pokemon.base_stats.get('speed', 0)
            my_speed = my_pokemon.base_stats.get('speed', 0)
            return opp_speed > my_speed
        
        return False

    def can_act_this_turn(self, battle: AbstractBattle) -> bool:
        """检查当前回合是否能行动"""
        # 安全获取我方宝可梦
        my_pokemon, _ = get_active_pokemon(battle)
        
        if not my_pokemon:
            return False
        
        my_status = my_pokemon.status
        
        if my_status == 'slp':
            # 睡眠状态有概率无法行动
            return random.random() > 0.33
        elif my_status == 'frz':
            # 冰冻状态有概率无法行动
            return random.random() > 0.20
        elif my_status == 'par':
            # 麻痹状态有概率无法行动
            return random.random() > 0.25
        
        return True

    def opponent_has_priority_threat(self, battle: AbstractBattle, opp_switch_probs: List) -> bool:
        """检查对手是否有先制技能威胁"""
        # 安全获取对手宝可梦
        opp_pokemon = getattr(battle, 'opponent_active_pokemon', None)
        if opp_pokemon is not None and hasattr(opp_pokemon, 'fainted'):
            opp_pokemon = cast(Pokemon, opp_pokemon)
        
        if not opp_pokemon:
            return False
        
        opp_moves = [str(move).lower() for move in opp_pokemon.moves.values()]
        priority_moves = ['extremespeed', 'suckerpunch', 'bulletpunch', 'machpunch', 'vacuumwave']
        
        has_priority = any(move in opp_moves for move in priority_moves)
        if not has_priority:
            return False
        
        # 检查对手HP是否足够使用先制技能
        opp_hp_frac = opp_pokemon.current_hp / opp_pokemon.max_hp
        return opp_hp_frac > 0.1  # 对手还有足够HP使用先制技能

    def opponent_just_switched_and_may_not_attack(self, battle: AbstractBattle, opp_switch_probs: List) -> bool:
        """检查对手是否刚换入且可能不直接攻击"""
        # 简化判断：如果对手有多个换人选项且概率较高，可能刚换入
        high_switch_prob = any(switch['probability'] > 0.4 for switch in opp_switch_probs)
        return high_switch_prob and battle.turn <= 5

    def has_advantageous_switch_options(self, battle: AbstractBattle) -> bool:
        """检查是否有属性优势的换人选项"""
        if not battle.available_switches:
            return False
        
        # 安全获取对手宝可梦
        opp_pokemon = getattr(battle, 'opponent_active_pokemon', None)
        if opp_pokemon is not None and hasattr(opp_pokemon, 'fainted'):
            opp_pokemon = cast(Pokemon, opp_pokemon)
        
        if not opp_pokemon or not opp_pokemon.moves:
            return False
        
        # 检查是否有能克制对手的换人选项
        first_move = list(opp_pokemon.moves.values())[0]
        for switch in battle.available_switches:
            if self.calculate_move_effectiveness(first_move, switch) < 1.0:  # 对手招式效果不好
                return True
        
        return False

    def has_significant_advantage_switch_options(self, battle: AbstractBattle) -> bool:
        """检查是否有明显优势的换人选项"""
        if not battle.available_switches:
            return False
        
        opp_pokemon = getattr(battle, 'opponent_active_pokemon', None)
        if opp_pokemon is not None and hasattr(opp_pokemon, 'fainted'):
            opp_pokemon = cast(Pokemon, opp_pokemon)
        
        if not opp_pokemon or not opp_pokemon.moves:
            return False
        
        # 检查是否有明显克制对手的换人选项
        for switch in battle.available_switches:
            advantage_score = 0
            for move in opp_pokemon.moves.values():
                if move.base_power > 0:
                    effectiveness = self.calculate_move_effectiveness(move, switch)
                    if effectiveness <= 0.5:  # 2倍抗性
                        advantage_score += 2
                    elif effectiveness < 1.0:  # 1.5倍抗性
                        advantage_score += 1
            
            if advantage_score >= 3:  # 有明显优势
                return True
        
        return False

    def current_pokemon_ineffective(self, battle: AbstractBattle) -> bool:
        """检查当前宝可梦是否效率不高"""
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        
        if not my_pokemon or not opp_pokemon:
            return False
        
        # 检查是否有有效招式
        effective_moves = 0
        for move in my_pokemon.moves.values():
            if move.base_power > 0:
                effectiveness = self.calculate_move_effectiveness(move, opp_pokemon)
                if effectiveness >= 1.0:  # 有效果
                    effective_moves += 1
        
        return effective_moves < 2  # 有效招式少于2个

    def opponent_has_high_threat_moves(self, battle: AbstractBattle) -> bool:
        """检查对手是否有高威胁招式"""
        opp_pokemon = getattr(battle, 'opponent_active_pokemon', None)
        if opp_pokemon is not None and hasattr(opp_pokemon, 'fainted'):
            opp_pokemon = cast(Pokemon, opp_pokemon)
        
        if not opp_pokemon or not opp_pokemon.moves:
            return False
        
        # 检查是否有高威力招式
        for move in opp_pokemon.moves.values():
            if move.base_power >= 120:  # 高威力招式
                return True
        
        return False

    def can_effectively_counter(self, battle: AbstractBattle) -> bool:
        """检查是否能有效反击对手"""
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        
        if not my_pokemon or not opp_pokemon:
            return False
        
        # 检查是否有能有效反击的招式
        for move in my_pokemon.moves.values():
            if move.base_power > 0:
                effectiveness = self.calculate_move_effectiveness(move, opp_pokemon)
                if effectiveness >= 2.0:  # 2倍克制
                    return True
        
        return False

    def has_recovery_options(self, battle: AbstractBattle) -> bool:
        """检查是否有回复选项"""
        if not battle.available_switches:
            return False
        
        # 检查换人选项中是否有回复技能
        for switch in battle.available_switches:
            for move in switch.moves.values():
                move_name = str(move).lower()
                if move_name in ['recover', 'roost', 'synthesis', 'moonlight', 'rest', 'slackoff']:
                    return True
        
        return False

    def choose_high_damage_move(self, battle: AbstractBattle) -> Optional[Any]:
        """选择高伤害攻击技能"""
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        if not my_pokemon or not opp_pokemon:
            return None
        
        best_move = None
        best_damage = 0
        
        for move in battle.available_moves:
            if move.base_power > 0:  # 只考虑攻击技能
                damage_info = self.calculate_detailed_damage(move, opp_pokemon, battle)
                mean_damage = damage_info['mean_damage']
                
                # 选择期望伤害最高的技能
                if mean_damage > best_damage:
                    best_damage = mean_damage
                    best_move = move
        
        if best_move and best_damage > 0:
            return self.create_order(best_move)
        
        return None

    def choose_best_switch(self, available_switches):
        """选择最佳换人"""
        if not available_switches:
            return self.choose_random_move(available_switches)
        
        # 使用战术评估选择最佳换人
        switch_utilities = []
        for switch in available_switches:
            utility = self.evaluate_switch_utility(switch, self.battle_state, 'momentum_gain')
            switch_utilities.append((switch, utility))
        
        best_switch = max(switch_utilities, key=lambda x: x[1])
        return self.create_order(best_switch[0])
    
    def evaluate_switch_utility(self, switch: Pokemon, battle: AbstractBattle, target: str) -> float:
        """评估换人效用"""
        utility = 0.0
        
        # 安全获取对手宝可梦
        opp_pokemon = getattr(battle, 'opponent_active_pokemon', None)
        if opp_pokemon is not None and hasattr(opp_pokemon, 'fainted'):
            opp_pokemon = cast(Pokemon, opp_pokemon)
        
        if opp_pokemon and opp_pokemon.moves:
            # 属性相克优势
            first_move = list(opp_pokemon.moves.values())[0]
            effectiveness = self.calculate_move_effectiveness(first_move, switch)
            if effectiveness < 1.0:  # 对手招式效果不好
                utility += 0.3
        
        # 考虑入场伤害（如隐形岩）
        entry_hazard_damage = self.calculate_entry_hazard_damage(switch, battle)
        utility -= entry_hazard_damage * 0.01
        
        return utility
    
    def calculate_entry_hazard_damage(self, pokemon: Pokemon, battle: AbstractBattle) -> float:
        """计算入场伤害"""
        damage = 0
        hazards = self.battle_state.get('hazards_my_side', [])
        
        if 'stealthrock' in hazards:
            # 隐形岩伤害基于属性相克
            rock_effectiveness = 1.0
            for pokemon_type in pokemon.types:
                eff = get_type_effectiveness('ROCK', pokemon_type.name.upper())
                rock_effectiveness *= eff
            damage += 12.5 * rock_effectiveness
        
        if 'spikes' in hazards:
            damage += 12.5
        
        return damage

    # ============================== 8. 动作执行模块 ==============================
    def executor(self, battle: AbstractBattle, action_utilities: List, switch_eval: Dict, priority_actions: List) -> Any:
        """执行最终动作选择 - 基于技能优先级的决策执行"""
        # 1. 紧急换人处理（最高优先级）
        if switch_eval['urgent_switch_needed']:
            return self.handle_urgent_switch(battle, action_utilities, switch_eval)
        
        # 2. 技能优先级检查
        priority_action = self.check_priority_actions(action_utilities, priority_actions, battle)
        if priority_action:
            return priority_action
        
        # 3. 主动换人检查
        if switch_eval['safe_switch_window']:
            switch_action = self.evaluate_safe_switch(battle, action_utilities, switch_eval)
            if switch_action:
                return switch_action
        
        # 4. 基于效用和技能优先级的最终选择
        return self.select_best_action(action_utilities, battle)

    def handle_urgent_switch(self, battle: AbstractBattle, action_utilities: List, switch_eval: Dict) -> Any:
        """处理紧急换人"""
        switch_actions = [a for a in action_utilities if a['type'] == 'switch']
        
        if not switch_actions:
            # 没有换人选项，选择最安全的招式
            return self.choose_safest_move(action_utilities, battle)
        
        # 选择最安全的换人（考虑入场伤害和属性相克）
        best_switch = None
        best_safety_score = -float('inf')
        
        for switch_action in switch_actions:
            switch_pokemon = switch_action['action']
            safety_score = self.calculate_switch_safety(switch_pokemon, battle)
            
            if safety_score > best_safety_score:
                best_safety_score = safety_score
                best_switch = switch_action['action']
        
        return self.create_order(best_switch) if best_switch else self.choose_safest_move(action_utilities, battle)

    def calculate_switch_safety(self, switch_pokemon: Pokemon, battle: AbstractBattle) -> float:
        """计算换人安全性分数"""
        safety_score = 0.0
        
        # 安全获取对手宝可梦
        opp_pokemon = getattr(battle, 'opponent_active_pokemon', None)
        if opp_pokemon is not None and hasattr(opp_pokemon, 'fainted'):
            opp_pokemon = cast(Pokemon, opp_pokemon)
        
        # 1. 属性相克优势
        if opp_pokemon and opp_pokemon.types and switch_pokemon.types:
            resistance = 1.0
            for opp_type in opp_pokemon.types:
                for my_type in switch_pokemon.types:
                    eff = get_type_effectiveness(opp_type.name.upper(), my_type.name.upper())
                    resistance *= eff
            
            if resistance < 0.5:
                safety_score += 50.0  # 4倍抗性
            elif resistance < 1.0:
                safety_score += 30.0  # 2倍抗性
            else:
                safety_score -= 20.0  # 被克制
        
        # 2. 入场伤害惩罚
        entry_damage = self.calculate_entry_hazard_damage(switch_pokemon, battle)
        safety_score -= entry_damage * 2.0
        
        # 3. 耐久度考虑
        if hasattr(switch_pokemon, 'base_stats'):
            hp = switch_pokemon.base_stats.get('hp', 0)
            defense = switch_pokemon.base_stats.get('defense', 0)
            sp_defense = switch_pokemon.base_stats.get('special-defense', 0)
            durability = (hp + defense + sp_defense) / 3.0
            safety_score += durability * 0.1
        
        return safety_score

    def check_priority_actions(self, action_utilities: List, priority_actions: List, battle: AbstractBattle) -> Any:
        """改进的优先级动作检查 - 更智能的优先级判断"""
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        if not my_pokemon or not opp_pokemon:
            return None
        
        my_hp_frac = my_pokemon.current_hp / my_pokemon.max_hp
        opp_hp_frac = opp_pokemon.current_hp / opp_pokemon.max_hp
        
        # 根据当前情况调整优先级
        adjusted_priorities = self.get_adjusted_priorities(battle, my_hp_frac, opp_hp_frac)
        
        for priority_type in adjusted_priorities:
            for action in action_utilities:
                if (action['type'] == 'move' and 
                    action.get('move_type') == priority_type and
                    action['utility'] > 0):  # 只考虑有正效用的动作
                    
                    # 额外检查：确保动作在当前情况下是合理的
                    if self.is_action_reasonable(action, battle, my_hp_frac, opp_hp_frac):
                        return self.create_order(action['action'])
        
        return None

    def get_adjusted_priorities(self, battle: AbstractBattle, my_hp_frac: float, opp_hp_frac: float) -> List[str]:
        """根据当前情况调整优先级顺序"""
        base_priorities = PRIORITY_ORDER.copy()
        
        # 根据HP情况调整优先级
        if my_hp_frac < 0.3:  # 低HP时优先生存
            # 将回复和保护技能提到最高优先级
            survival_priorities = ['recovery', 'protection', 'status']
            for priority in survival_priorities:
                if priority in base_priorities:
                    base_priorities.remove(priority)
                    base_priorities.insert(0, priority)
        
        elif my_hp_frac > 0.8 and opp_hp_frac < 0.3:  # 高HP且对手低HP时优先攻击
            # 将攻击技能提到更高优先级
            attack_priorities = ['physical_attack', 'special_attack', 'priority']
            for priority in attack_priorities:
                if priority in base_priorities:
                    base_priorities.remove(priority)
                    base_priorities.insert(2, priority)  # 在回复和保护之后
        
        # 根据对战阶段调整
        turn_count = battle.turn
        if turn_count <= 3:  # 早期阶段
            # 优先场地控制和状态技能
            early_priorities = ['field', 'status', 'setup']
            for priority in early_priorities:
                if priority in base_priorities:
                    base_priorities.remove(priority)
                    base_priorities.insert(1, priority)
        
        elif turn_count >= 15:  # 后期阶段
            # 优先攻击和先制技能
            late_priorities = ['priority', 'physical_attack', 'special_attack']
            for priority in late_priorities:
                if priority in base_priorities:
                    base_priorities.remove(priority)
                    base_priorities.insert(0, priority)
        
        return base_priorities

    def is_action_reasonable(self, action: Dict, battle: AbstractBattle, my_hp_frac: float, opp_hp_frac: float) -> bool:
        """检查动作在当前情况下是否合理"""
        move = action['action']
        move_type = action.get('move_type', 'other')
        
        # 检查回复技能是否合理
        if move_type == 'recovery':
            # 只有在HP较低时才使用回复技能
            return my_hp_frac < 0.7
        
        # 检查保护技能是否合理
        if move_type == 'protection':
            # 只有在有威胁时才使用保护技能
            return self.opponent_has_high_threat_moves(battle) or my_hp_frac < 0.5
        
        # 检查强化技能是否合理
        if move_type == 'setup':
            # 只有在安全时才使用强化技能
            return my_hp_frac > 0.6 and not self.opponent_has_high_threat_moves(battle)
        
        # 检查状态技能是否合理
        if move_type == 'status':
            # 检查对手是否已经有状态
            opp_pokemon = getattr(battle, 'opponent_active_pokemon', None)
            if opp_pokemon and opp_pokemon.status:
                return False  # 对手已有状态，不需要再使用状态技能
        
        return True

    def evaluate_safe_switch(self, battle: AbstractBattle, action_utilities: List, switch_eval: Dict) -> Any:
        """评估主动换人"""
        switch_actions = [a for a in action_utilities if a['type'] == 'switch']
        
        if not switch_actions:
            return None
        
        # 选择效用最高的换人，但要有足够的优势
        best_switch = max(switch_actions, key=lambda x: x['utility'])
        
        # 如果换人效用明显高于当前最佳招式，则换人
        move_actions = [a for a in action_utilities if a['type'] == 'move']
        if move_actions:
            best_move = max(move_actions, key=lambda x: x['utility'])
            if best_switch['utility'] > best_move['utility'] + 20.0:  # 换人优势阈值
                return self.create_order(best_switch['action'])
        
        return None

    def select_best_action(self, action_utilities: List, battle: AbstractBattle) -> Any:
        """选择最佳动作"""
        if not action_utilities:
            return self.choose_random_move(battle.available_moves)
        
        # 按效用排序，但考虑技能优先级
        def action_priority(action):
            utility = action['utility']
            move_type = action.get('move_type', 'other')
            
            # 技能优先级调整
            priority_multiplier = PRIORITY_MULTIPLIER.get(move_type, 1.0)
            
            return utility * priority_multiplier
        
        best_action = max(action_utilities, key=action_priority)
        action = best_action['action']
        
        # 根据动作类型创建正确的订单
        if best_action['type'] == 'move':
            return self.create_order(action)
        elif best_action['type'] == 'switch':
            return self.create_order(action)
        else:
            return self.choose_random_move(battle.available_moves)

    def choose_safest_move(self, action_utilities: List, battle: AbstractBattle = None) -> Any:
        """选择最安全的招式"""
        move_actions = [a for a in action_utilities if a['type'] == 'move']
        
        if not move_actions:
            # 如果没有招式选项，返回一个默认的随机招式
            if battle and battle.available_moves:
                return self.choose_random_move(battle.available_moves)
            else:
                # 如果连battle都没有，返回None让上层处理
                return None
        
        # 优先选择保护技能，其次选择风险最低的招式
        protection_actions = [a for a in move_actions if a.get('move_type') == 'protection']
        if protection_actions:
            return self.create_order(protection_actions[0]['action'])
        
        # 选择效用最高的招式
        best_action = max(move_actions, key=lambda x: x['utility'])
        return self.create_order(best_action['action'])

    def record_action(self, action: Any, battle: AbstractBattle):
        """记录动作用于学习"""
        # 安全获取宝可梦
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        
        self.opponent_history.append({
            'turn': battle.turn,
            'my_action': str(action),
            'opp_pokemon': opp_pokemon.species if opp_pokemon else None,
            'my_pokemon': my_pokemon.species if my_pokemon else None
        })

    # ============================== 辅助方法 ==============================

    def calculate_move_effectiveness(self, move: Move, target: Pokemon) -> float:
        """简化的类型相克计算 - 优先使用内置API，失败则用备用方案"""
        if not move.type or not target.types:
            return 1.0
        
        # 优先使用内置API获取更准确的类型相克
        try:
            effectiveness = float(target.damage_multiplier(move))
            # 确保有效性在合理范围内
            if 0.0 <= effectiveness <= 4.0:
                return effectiveness
            else:
                # 如果API返回异常值，使用备用方案
                raise ValueError("API returned invalid effectiveness")
        except:
            # 备用方案：使用你的类型相克表
            effectiveness = 1.0
            for target_type in target.types:
                eff = get_type_effectiveness(move.type.name.upper(), target_type.name.upper())
                effectiveness *= eff
            return max(0.0, min(effectiveness, 4.0))  # 限制在合理范围内

    def calculate_ko_probability(self, move: Move, target: Pokemon, battle: AbstractBattle) -> float:
        """简化的KO概率计算"""
        if move.base_power == 0:
            return 0.0
        
        # 使用改进的伤害计算
        dmg_info = self.calculate_detailed_damage(move, target, battle)
        
        # 基于对手当前HP计算KO概率
        target_hp_frac = target.current_hp / target.max_hp if target.max_hp > 0 else 1.0
        
        if dmg_info['mean_damage'] >= target.current_hp:
            return 1.0
        elif dmg_info['min_damage'] >= target.current_hp:
            return 0.5
        else:
            # 基于伤害比例估算KO概率
            damage_ratio = dmg_info['mean_damage'] / target.current_hp
            return min(damage_ratio * 0.8, 0.9)  # 保守估计，避免过度乐观

    def validate_damage_calculation(self, move: Move, target: Pokemon, battle: AbstractBattle) -> bool:
        """验证伤害计算的合理性"""
        dmg_info = self.calculate_detailed_damage(move, target, battle)
        
        # 检查伤害是否在合理范围内
        if dmg_info['mean_damage'] < 0:
            return False
        
        # 检查KO概率是否合理
        if dmg_info['ko_prob'] > 1.0 or dmg_info['ko_prob'] < 0:
            return False
        
        # 检查伤害是否过高（可能是计算错误）
        if dmg_info['mean_damage'] > target.max_hp * 2:
            return False
        
        return True
    
    def classify_move(self, move: Move) -> str:
        """技能分类 - 根据招式特征分类"""
        move_name = str(move).lower()
        
        # 1. 攻击技能（Attack Moves）
        if move.base_power > 0:
            if move.category == 'Physical':
                return 'physical_attack'
            elif move.category == 'Special':
                return 'special_attack'
            else:
                return 'attack'
        
        # 2. 优先检查低级别格式特定分类
        format_specific_categories = ['nu_stall', 'ru_control', 'uu_offense']
        for category in format_specific_categories:
            if move_name in MOVE_CLASSIFICATION.get(category, set()):
                return category
        
        # 3. 使用字典结构进行通用技能分类
        for category, moves in MOVE_CLASSIFICATION.items():
            if category not in format_specific_categories and move_name in moves:
                return category
        
        # 默认分类
        return 'other'
