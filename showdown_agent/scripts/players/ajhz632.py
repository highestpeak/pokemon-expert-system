from poke_env.battle import AbstractBattle, Pokemon, Move
from poke_env.player import Player
from typing import Dict, List, Tuple, Optional, Any, cast
import random
import math

team = """
Ribombee @ Focus Sash
Ability: Sweet Veil
Tera Type: Fairy
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
- Sticky Web
- Stun Spore
- Quiver Dance
- Moonblast

Arceus-Fairy @ Pixie Plate
Ability: Multitype
Tera Type: Fairy
EVs: 248 HP / 120 Def / 16 SpA / 124 Spe
Modest Nature
- Judgment
- Earth Power
- Calm Mind
- Recover

Koraidon @ Choice Band
Ability: Orichalcum Pulse
Tera Type: Fire
EVs: 252 Atk / 4 Def / 252 Spe
Jolly Nature
- Low Kick
- Dragon Claw
- U-turn
- Flare Blitz

Zacian-Crowned @ Rusted Sword
Ability: Intrepid Sword
Tera Type: Flying
EVs: 252 Atk / 4 SpD / 252 Spe
Jolly Nature
- Swords Dance
- Behemoth Blade
- Substitute
- Play Rough

Rayquaza @ Heavy-Duty Boots
Ability: Air Lock
Tera Type: Flying
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Dragon Dance
- Dragon Ascent
- Extreme Speed
- Earthquake

Necrozma-Dusk-Mane @ Assault Vest
Ability: Prism Armor
Tera Type: Steel
EVs: 248 HP / 200 Def / 60 SpD
Impish Nature
- Sunsteel Strike
- Earthquake
- Photon Geyser
- Rock Slide

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
            'W_K': 1.5,  # 提高KO权重
            'W_D': 1.2,  # 提高伤害权重
            'W_R': 1.0,  # 风险权重
            'W_F': 0.3,  # 降低场地权重
            'W_S': 0.5,  # 降低强化权重
            'W_C': 1.0   # 换人成本
        }
    },
    'status_stall': {
        'target': 'stall_break',
        'priority_actions': ['taunt', 'attack', 'setup', 'strong_attack'],
        'tactical_weights': {
            'W_K': 2.0,  # 大幅提高KO权重
            'W_D': 1.5,  # 提高伤害权重
            'W_R': 0.8,  # 降低风险权重（受队攻击力低）
            'W_F': 0.2,  # 大幅降低场地权重
            'W_S': 0.3,  # 降低强化权重
            'W_C': 0.8   # 降低换人成本
        }
    },
    'entry_hazard': {
        'target': 'hazard_control',
        'priority_actions': ['defog', 'rapidspin', 'taunt', 'attack'],
        'tactical_weights': {
            'W_K': 1.3,  # 提高KO权重
            'W_D': 1.1,  # 提高伤害权重
            'W_R': 1.0,  # 风险权重
            'W_F': 1.5,  # 大幅提高场地权重
            'W_S': 0.7,  # 降低强化权重
            'W_C': 1.2   # 提高换人成本
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

    def choose_move(self, battle: AbstractBattle):
        # **濒死判断**：是 AI 的第一个分支点（Switch vs. Move）
        my_pokemon, _ = get_active_pokemon(battle)
        if my_pokemon is not None and not my_pokemon.fainted:
            # **异常状态修正**：必须要有，否则 AI 会傻乎乎地让睡着的宝可梦硬抗
            self.adjust_for_status(my_pokemon)
            
            # 执行完整的策略pipeline
            best_action = self.execute_strategy_pipeline(battle)
            
            # 记录行为用于学习
            self.record_action(best_action, battle)
            
            return best_action
        else:
            # 如果 active_pokemon 不存在或为 None，尝试切换
            return self.choose_best_switch(battle.available_switches)

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
        
        # 7. 换人判定
        switch_evaluation = self.switch_evaluator(battle, opp_switch_probs)
        
        # 8. 动作执行
        best_action = self.executor(battle, action_utilities, switch_evaluation, priority_actions)
        
        return best_action

    # ============================== 1. 感知模块 ==============================
    def update_battle_state(self, battle: AbstractBattle):
        """更新对战状态和对手历史行为"""
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        
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
            'hazards_opp_side': self.get_hazards(battle, my_side=False)
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
            'stall_recovery': 0.0     # 回复受队
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
        
        return combos

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
                prob = 0.2 + opponent_model_effectiveness * 0.3  # 基础概率 + 相克加成
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
        if resistance < 0.5:
            return 0.7
        elif resistance < 1.0:
            return 0.4
        else:
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
        
        # 评估换人选项
        for switch in battle.available_switches:
            utility = self.evaluate_switch_utility(switch, battle, strategic_target, tactical_weights)
            action_utilities.append({
                'action': switch,
                'utility': utility,
                'type': 'switch'
            })
        
        return action_utilities

    def evaluate_action_utility(self, move: Move, battle: AbstractBattle, opp_move_dist: List, 
                              strategic_target: str, tactical_weights: Dict) -> float:
        """基于技能分类的动作效用评估 - 数值决策引擎核心"""
        move_type = self.classify_move(move)
        utility = 0.0

        my_pokemon, opp_pokemon = get_active_pokemon(battle)

        # 安全获取宝可梦
        if not my_pokemon or not opp_pokemon:
            return utility
        
        # 基础伤害计算
        if move.base_power > 0:
            dmg_info = self.calculate_detailed_damage(move, opp_pokemon, battle)
            P_my_KO = dmg_info['ko_prob']
            E_dmg = dmg_info['mean_damage']
            
            # 攻击技能效用
            utility += (tactical_weights['W_K'] * P_my_KO * 100.0 +  # KO概率价值
                       tactical_weights['W_D'] * E_dmg * 0.1)        # 伤害价值
        
        # 计算对手反击风险
        P_opp_incoming_KO = 0.0
        for opp_move in opp_move_dist:
            if opp_move['probability'] > 0.1:
                opp_dmg_info = self.calculate_detailed_damage(
                    opp_move['move'], my_pokemon, battle
                )
                P_opp_incoming_KO += opp_move['probability'] * opp_dmg_info['ko_prob']
        
        # 风险惩罚
        utility -= tactical_weights['W_R'] * P_opp_incoming_KO * 50.0
        
        # 根据技能类型添加特殊效用
        if move_type == 'setup':
            # 强化技能：考虑未来回合收益
            setup_value = self.estimate_setup_value(move, battle, tactical_weights)
            utility += tactical_weights['W_S'] * setup_value
            
        elif move_type == 'recovery':
            # 回复技能：生存时间延长价值
            recovery_value = self.estimate_recovery_value(move, battle)
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
            # 保护技能：防御和探招价值
            protection_value = self.estimate_protection_value(move, battle, opp_move_dist)
            utility += protection_value * 20.0
            
        elif move_type == 'priority':
            # 先制技能：确保先手价值
            priority_value = self.estimate_priority_value(move, battle)
            utility += priority_value * 25.0
        
        # 异常状态调整
        if hasattr(self, 'status_adjustments'):
            utility = self.apply_status_adjustments(utility, move, move_type)
        
        return utility

    def calculate_detailed_damage(self, move: Move, target: Pokemon, battle: AbstractBattle) -> Dict:
        """详细伤害计算 - 包含KO概率和期望伤害"""
        if move.base_power == 0:
            return {'ko_prob': 0.0, 'mean_damage': 0.0, 'min_damage': 0.0, 'max_damage': 0.0}
        
        # 基础伤害计算（简化版）
        base_damage = move.base_power
        effectiveness = self.calculate_move_effectiveness(move, target)
        
        # 考虑STAB加成
        stab_multiplier = 1.0
        if move.type and target.types:
            for target_type in target.types:
                if move.type.name.upper() == target_type.name.upper():
                    stab_multiplier = 1.5
                    break
        
        # 考虑属性相克
        total_damage = base_damage * effectiveness * stab_multiplier
        
        # 计算KO概率（基于目标当前HP）
        target_hp_frac = target.current_hp / target.max_hp
        ko_prob = min(total_damage / (target.max_hp * 0.1), 1.0) if target_hp_frac > 0 else 1.0
        
        return {
            'ko_prob': ko_prob,
            'mean_damage': total_damage,
            'min_damage': total_damage * 0.85,
            'max_damage': total_damage * 1.15
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

    def evaluate_move_utility(self, move: Move, battle: AbstractBattle, opp_move_dist: List, target: str) -> float:
        """评估招式效用"""
        utility = 0.0
        
        # 安全获取对手宝可梦
        opp_pokemon = getattr(battle, 'opponent_active_pokemon', None)
        if opp_pokemon is not None and hasattr(opp_pokemon, 'fainted'):
            opp_pokemon = cast(Pokemon, opp_pokemon)
        if not opp_pokemon:
            return utility
        
        # 基础伤害计算
        if move.base_power > 0:
            damage = self.calculate_damage(move, opp_pokemon)
            utility += damage * 0.01  # 伤害转换为效用
        
        # 属性相克加成
        effectiveness = self.calculate_move_effectiveness(move, opp_pokemon)
        utility += effectiveness * 0.2
        
        # 战略目标匹配
        if target == 'hazard_control' and 'defog' in str(move).lower():
            utility += 0.5
        elif target == 'setup_disrupt' and 'taunt' in str(move).lower():
            utility += 0.4
        
        # 异常状态调整
        if hasattr(self, 'status_adjustments'):
            # 睡眠状态：优先攻击招式
            if self.status_adjustments.get('prefer_attacking', False) and move.base_power > 0:
                utility += 0.3
            
            # 避免强化招式
            if self.status_adjustments.get('avoid_setup', False) and self.is_setup_move(move):
                utility -= 0.5
            
            # 避免物理攻击（烧伤状态）
            if self.status_adjustments.get('avoid_physical', False) and move.category == 'Physical':
                utility -= 0.4
            
            # 避免拖延招式（中毒状态）
            if self.status_adjustments.get('avoid_stalling', False) and self.is_stalling_move(move):
                utility -= 0.3
        
        # 安全获取我方宝可梦
        my_pokemon, _ = get_active_pokemon(battle)
        
        if my_pokemon:
            # 考虑对手可能的反应
            for opp_move in opp_move_dist:
                if opp_move['probability'] > 0.3:
                    # 如果对手可能使用克制招式，降低效用
                    if self.is_move_super_effective(opp_move['move'], my_pokemon):
                        utility -= 0.2
        
        return utility

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

    def calculate_damage(self, move: Move, target: Pokemon) -> float:
        """简化的伤害计算"""
        if move.base_power == 0:
            return 0
        
        # 简化的伤害公式
        base_damage = move.base_power
        effectiveness = self.calculate_move_effectiveness(move, target)
        
        return base_damage * effectiveness

    def is_move_super_effective(self, move: Move, target: Pokemon) -> bool:
        """判断招式是否效果绝佳"""
        effectiveness = self.calculate_move_effectiveness(move, target)
        return effectiveness > 1.5

    def calculate_entry_hazard_damage(self, pokemon: Pokemon, battle: AbstractBattle) -> float:
        """计算入场伤害"""
        damage = 0
        hazards = self.battle_state['hazards_my_side']
        
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

    # ============================== 7. 换人判定模块 ==============================
    def switch_evaluator(self, battle: AbstractBattle, opp_switch_probs: List) -> Dict:
        """换人窗口判定 - 紧急换人和主动换人逻辑"""
        my_hp_frac = self.battle_state['my_hp']
        my_status = self.battle_state['my_status']
        
        # 紧急换人判定（优先级最高）
        urgent_switch_needed = False
        urgent_reasons = []
        
        # 条件1：HP过低
        if my_hp_frac <= 0.20:
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
        
        # 主动换人判定（安全窗口）
        safe_switch_window = False
        safe_reasons = []
        
        # 条件1：HP充足
        if my_hp_frac >= 0.6:
            safe_switch_window = True
            safe_reasons.append('high_hp')
        
        # 条件2：对手刚换入且可能不直接攻击
        if self.opponent_just_switched_and_may_not_attack(battle, opp_switch_probs):
            safe_switch_window = True
            safe_reasons.append('opponent_switch')
        
        # 条件3：有属性优势的换人选项
        if self.has_advantageous_switch_options(battle):
            safe_switch_window = True
            safe_reasons.append('type_advantage')
        
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
            return self.choose_safest_move(action_utilities)
        
        # 选择最安全的换人（考虑入场伤害和属性相克）
        best_switch = None
        best_safety_score = -float('inf')
        
        for switch_action in switch_actions:
            switch_pokemon = switch_action['action']
            safety_score = self.calculate_switch_safety(switch_pokemon, battle)
            
            if safety_score > best_safety_score:
                best_safety_score = safety_score
                best_switch = switch_action['action']
        
        return best_switch if best_switch else self.choose_safest_move(action_utilities)

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
        """检查优先级动作"""
        # 技能优先级：生存 > 控制 > 强化 > 攻击 > 先制
        priority_order = ['recovery', 'protection', 'status', 'field', 'setup', 'physical_attack', 'special_attack', 'priority']
        
        for priority_type in priority_order:
            for action in action_utilities:
                if (action['type'] == 'move' and 
                    action.get('move_type') == priority_type and
                    action['utility'] > 0):  # 只考虑有正效用的动作
                    return action['action']
        
        return None

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
                return best_switch['action']
        
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
            priority_multiplier = {
                'recovery': 1.2,      # 回复技能优先级最高
                'protection': 1.1,    # 保护技能次之
                'status': 1.05,       # 状态技能
                'field': 1.0,         # 场地技能
                'setup': 0.9,         # 强化技能
                'physical_attack': 0.8,  # 物理攻击
                'special_attack': 0.8,   # 特殊攻击
                'priority': 0.7,      # 先制技能
                'other': 0.5          # 其他技能
            }.get(move_type, 1.0)
            
            return utility * priority_multiplier
        
        best_action = max(action_utilities, key=action_priority)
        return best_action['action']

    def choose_safest_move(self, action_utilities: List) -> Any:
        """选择最安全的招式"""
        move_actions = [a for a in action_utilities if a['type'] == 'move']
        
        if not move_actions:
            return None
        
        # 优先选择保护技能，其次选择风险最低的招式
        protection_actions = [a for a in move_actions if a.get('move_type') == 'protection']
        if protection_actions:
            return protection_actions[0]['action']
        
        # 选择效用最高的招式
        return max(move_actions, key=lambda x: x['utility'])['action']

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
        return best_switch[0]

    def choose_best_move(self, moves, opponent_active):
        """选择最佳招式"""
        if not moves:
            return self.choose_random_move(moves)
        
        # 使用战术评估选择最佳招式
        move_utilities = []
        for move in moves.values():
            if move.current_pp > 0:
                utility = self.evaluate_move_utility(move, self.battle_state, [], 'momentum_gain')
                move_utilities.append((move, utility))
        
        if move_utilities:
            best_move = max(move_utilities, key=lambda x: x[1])
            return best_move[0]
        
        return self.choose_random_move(moves)

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

    def is_setup_move(self, move: Move) -> bool:
        """判断是否为强化招式"""
        setup_moves = [
            'swordsdance', 'dragon dance', 'quiverdance', 'calmmind', 'nastyplot',
            'bulk up', 'iron defense', 'amnesia', 'agility', 'rock polish',
            'work up', 'growth', 'hone claws', 'coil', 'shift gear'
        ]
        return str(move).lower() in setup_moves

    def is_stalling_move(self, move: Move) -> bool:
        """判断是否为拖延招式"""
        stalling_moves = [
            'protect', 'detect', 'spiky shield', 'baneful bunker', 'obstruct',
            'substitute', 'rest', 'recover', 'roost', 'synthesis', 'moonlight',
            'milk drink', 'soft boiled', 'heal order', 'slack off', 'shore up'
        ]
        return str(move).lower() in stalling_moves

    # ============================== 辅助方法 ==============================
    
    def calculate_move_effectiveness(self, move: Move, target: Pokemon) -> float:
        """计算招式对目标的相克效果"""
        if not move.type or not target.types:
            return 0.5
        
        effectiveness = 1.0
        for target_type in target.types:
            eff = get_type_effectiveness(move.type.name.upper(), target_type.name.upper())
            effectiveness *= eff
        
        return effectiveness
    
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
        
        # 2-7. 使用字典结构进行技能分类
        for category, moves in MOVE_CLASSIFICATION.items():
            if move_name in moves:
                return category
        
        # 默认分类
        return 'other'
