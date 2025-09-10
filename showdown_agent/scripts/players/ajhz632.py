"""
增强版宝可梦对战AI - 参考rlal223策略优化
主要改进：
1. 精确的属性相克表
2. 完整的STAB加成计算
3. 天气和场地效果支持
4. 特性和道具修正
5. 状态修正（烧伤等）
6. 增强的伤害计算精度
7. 更智能的招式评估系统
"""

from poke_env.battle import AbstractBattle, Pokemon, Move
from poke_env.player import Player
from poke_env.battle import Weather, PokemonType, MoveCategory, Status, Field
from typing import Dict, List, Tuple, Optional, Any, cast
import random
import math
import logging
import os
import time
import json
from datetime import datetime

# 队伍配置
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

# 简化的技能分类
MOVE_TYPES = {
    'setup': {'swordsdance', 'dragondance', 'quiverdance', 'calmmind', 'nastyplot', 'bulkup', 'agility'},
    'recovery': {'recover', 'roost', 'synthesis', 'moonlight', 'rest', 'slackoff'},
    'status': {'thunderwave', 'willowisp', 'toxic', 'hypnosis', 'sleepspore', 'taunt'},
    'field': {'stealthrock', 'spikes', 'toxicspikes', 'defog', 'rapidspin'},
    'protection': {'protect', 'detect', 'substitute'},
    'priority': {'extremespeed', 'suckerpunch', 'bulletpunch', 'machpunch', 'vacuumwave'}
}

# 技能优先级权重
PRIORITY_WEIGHTS = {
    'recovery': 1.5,
    'protection': 1.3,
    'status': 1.2,
    'field': 1.1,
    'setup': 1.0,
    'physical_attack': 0.9,
    'special_attack': 0.9,
    'priority': 0.8,
    'other': 0.5
}

# 完整的属性相克表
TYPE_EFFECTIVENESS = {
    "Normal":   {"Normal": 1.0, "Fire": 1.0, "Water": 1.0, "Electric": 1.0, "Grass": 1.0, "Ice": 1.0, "Fighting": 1.0, "Poison": 1.0, "Ground": 1.0, "Flying": 1.0, "Psychic": 1.0, "Bug": 1.0, "Rock": 0.5, "Ghost": 0.0, "Dragon": 1.0, "Dark": 1.0, "Steel": 0.5, "Fairy": 1.0},
    "Fire":     {"Normal": 1.0, "Fire": 0.5, "Water": 0.5, "Electric": 1.0, "Grass": 2.0, "Ice": 2.0, "Fighting": 1.0, "Poison": 1.0, "Ground": 1.0, "Flying": 1.0, "Psychic": 1.0, "Bug": 2.0, "Rock": 0.5, "Ghost": 1.0, "Dragon": 0.5, "Dark": 1.0, "Steel": 2.0, "Fairy": 1.0},
    "Water":    {"Normal": 1.0, "Fire": 2.0, "Water": 0.5, "Electric": 1.0, "Grass": 0.5, "Ice": 1.0, "Fighting": 1.0, "Poison": 1.0, "Ground": 2.0, "Flying": 1.0, "Psychic": 1.0, "Bug": 1.0, "Rock": 2.0, "Ghost": 1.0, "Dragon": 0.5, "Dark": 1.0, "Steel": 1.0, "Fairy": 1.0},
    "Electric": {"Normal": 1.0, "Fire": 1.0, "Water": 2.0, "Electric": 0.5, "Grass": 0.5, "Ice": 1.0, "Fighting": 1.0, "Poison": 1.0, "Ground": 0.0, "Flying": 2.0, "Psychic": 1.0, "Bug": 1.0, "Rock": 1.0, "Ghost": 1.0, "Dragon": 0.5, "Dark": 1.0, "Steel": 1.0, "Fairy": 1.0},
    "Grass":    {"Normal": 1.0, "Fire": 0.5, "Water": 2.0, "Electric": 1.0, "Grass": 0.5, "Ice": 1.0, "Fighting": 1.0, "Poison": 0.5, "Ground": 2.0, "Flying": 0.5, "Psychic": 1.0, "Bug": 0.5, "Rock": 2.0, "Ghost": 1.0, "Dragon": 0.5, "Dark": 1.0, "Steel": 0.5, "Fairy": 1.0},
    "Ice":      {"Normal": 1.0, "Fire": 0.5, "Water": 0.5, "Electric": 1.0, "Grass": 2.0, "Ice": 0.5, "Fighting": 1.0, "Poison": 1.0, "Ground": 2.0, "Flying": 2.0, "Psychic": 1.0, "Bug": 1.0, "Rock": 1.0, "Ghost": 1.0, "Dragon": 2.0, "Dark": 1.0, "Steel": 0.5, "Fairy": 1.0},
    "Fighting": {"Normal": 2.0, "Fire": 1.0, "Water": 1.0, "Electric": 1.0, "Grass": 1.0, "Ice": 2.0, "Fighting": 1.0, "Poison": 0.5, "Ground": 1.0, "Flying": 0.5, "Psychic": 0.5, "Bug": 0.5, "Rock": 2.0, "Ghost": 0.0, "Dragon": 1.0, "Dark": 2.0, "Steel": 2.0, "Fairy": 0.5},
    "Poison":   {"Normal": 1.0, "Fire": 1.0, "Water": 1.0, "Electric": 1.0, "Grass": 2.0, "Ice": 1.0, "Fighting": 1.0, "Poison": 0.5, "Ground": 0.5, "Flying": 1.0, "Psychic": 1.0, "Bug": 1.0, "Rock": 0.5, "Ghost": 0.5, "Dragon": 1.0, "Dark": 1.0, "Steel": 0.0, "Fairy": 2.0},
    "Ground":   {"Normal": 1.0, "Fire": 2.0, "Water": 1.0, "Electric": 2.0, "Grass": 0.5, "Ice": 1.0, "Fighting": 1.0, "Poison": 2.0, "Ground": 1.0, "Flying": 0.0, "Psychic": 1.0, "Bug": 0.5, "Rock": 2.0, "Ghost": 1.0, "Dragon": 1.0, "Dark": 1.0, "Steel": 2.0, "Fairy": 1.0},
    "Flying":   {"Normal": 1.0, "Fire": 1.0, "Water": 1.0, "Electric": 0.5, "Grass": 2.0, "Ice": 1.0, "Fighting": 2.0, "Poison": 1.0, "Ground": 1.0, "Flying": 1.0, "Psychic": 1.0, "Bug": 2.0, "Rock": 0.5, "Ghost": 1.0, "Dragon": 1.0, "Dark": 1.0, "Steel": 0.5, "Fairy": 1.0},
    "Psychic":  {"Normal": 1.0, "Fire": 1.0, "Water": 1.0, "Electric": 1.0, "Grass": 1.0, "Ice": 1.0, "Fighting": 2.0, "Poison": 2.0, "Ground": 1.0, "Flying": 1.0, "Psychic": 0.5, "Bug": 1.0, "Rock": 1.0, "Ghost": 1.0, "Dragon": 1.0, "Dark": 0.0, "Steel": 0.5, "Fairy": 1.0},
    "Bug":      {"Normal": 1.0, "Fire": 0.5, "Water": 1.0, "Electric": 1.0, "Grass": 2.0, "Ice": 1.0, "Fighting": 0.5, "Poison": 0.5, "Ground": 1.0, "Flying": 0.5, "Psychic": 2.0, "Bug": 1.0, "Rock": 1.0, "Ghost": 0.5, "Dragon": 1.0, "Dark": 2.0, "Steel": 0.5, "Fairy": 0.5},
    "Rock":     {"Normal": 1.0, "Fire": 2.0, "Water": 1.0, "Electric": 1.0, "Grass": 1.0, "Ice": 2.0, "Fighting": 0.5, "Poison": 1.0, "Ground": 0.5, "Flying": 2.0, "Psychic": 1.0, "Bug": 2.0, "Rock": 1.0, "Ghost": 1.0, "Dragon": 1.0, "Dark": 1.0, "Steel": 0.5, "Fairy": 1.0},
    "Ghost":    {"Normal": 0.0, "Fire": 1.0, "Water": 1.0, "Electric": 1.0, "Grass": 1.0, "Ice": 1.0, "Fighting": 1.0, "Poison": 1.0, "Ground": 1.0, "Flying": 1.0, "Psychic": 2.0, "Bug": 1.0, "Rock": 1.0, "Ghost": 2.0, "Dragon": 1.0, "Dark": 0.5, "Steel": 1.0, "Fairy": 1.0},
    "Dragon":   {"Normal": 1.0, "Fire": 1.0, "Water": 1.0, "Electric": 1.0, "Grass": 1.0, "Ice": 1.0, "Fighting": 1.0, "Poison": 1.0, "Ground": 1.0, "Flying": 1.0, "Psychic": 1.0, "Bug": 1.0, "Rock": 1.0, "Ghost": 1.0, "Dragon": 2.0, "Dark": 1.0, "Steel": 0.5, "Fairy": 0.0},
    "Dark":     {"Normal": 1.0, "Fire": 1.0, "Water": 1.0, "Electric": 1.0, "Grass": 1.0, "Ice": 1.0, "Fighting": 0.5, "Poison": 1.0, "Ground": 1.0, "Flying": 1.0, "Psychic": 2.0, "Bug": 1.0, "Rock": 1.0, "Ghost": 2.0, "Dragon": 1.0, "Dark": 0.5, "Steel": 1.0, "Fairy": 0.5},
    "Steel":    {"Normal": 1.0, "Fire": 0.5, "Water": 0.5, "Electric": 0.5, "Grass": 1.0, "Ice": 2.0, "Fighting": 1.0, "Poison": 1.0, "Ground": 1.0, "Flying": 1.0, "Psychic": 1.0, "Bug": 1.0, "Rock": 2.0, "Ghost": 1.0, "Dragon": 1.0, "Dark": 1.0, "Steel": 0.5, "Fairy": 2.0},
    "Fairy":    {"Normal": 1.0, "Fire": 0.5, "Water": 1.0, "Electric": 1.0, "Grass": 1.0, "Ice": 1.0, "Fighting": 2.0, "Poison": 0.5, "Ground": 1.0, "Flying": 1.0, "Psychic": 1.0, "Bug": 1.0, "Rock": 1.0, "Ghost": 1.0, "Dragon": 2.0, "Dark": 2.0, "Steel": 0.5, "Fairy": 1.0}
}

def get_active_pokemon(battle: AbstractBattle) -> Tuple[Optional[Pokemon], Optional[Pokemon]]:
    """安全获取我方和对手的当前宝可梦"""
    my_pokemon = getattr(battle, 'active_pokemon', None)
    opp_pokemon = getattr(battle, 'opponent_active_pokemon', None)
    
    if my_pokemon and hasattr(my_pokemon, 'fainted'):
        my_pokemon = cast(Pokemon, my_pokemon)
    if opp_pokemon and hasattr(opp_pokemon, 'fainted'):
        opp_pokemon = cast(Pokemon, opp_pokemon)
    
    return my_pokemon, opp_pokemon

def get_type_effectiveness_multiplier(attack_type: PokemonType, defense_type: PokemonType) -> float:
    """获取属性相克倍数"""
    attack_str = attack_type.name.title()
    defense_str = defense_type.name.title()
    return TYPE_EFFECTIVENESS.get(attack_str, {}).get(defense_str, 1.0)

def calculate_stab(attacker: Pokemon, move: Move) -> float:
    """计算STAB加成"""
    if not move.type or not attacker.types:
        return 1.0
    
    # 检查招式属性是否与宝可梦属性匹配
    has_stab = move.type in attacker.types
    
    if not has_stab:
        return 1.0
    
    # 适应力特性使STAB从1.5倍变为2倍
    if attacker.ability == "adaptability":
        return 2.0
    else:
        return 1.5

def calculate_weather_modifier(move: Move, battle: AbstractBattle) -> float:
    """计算天气修正"""
    if not battle.weather or not move.type:
        return 1.0
    
    # 晴天增强火系，削弱水系
    if Weather.SUNNYDAY in battle.weather or Weather.DESOLATELAND in battle.weather:
        if move.type == PokemonType.FIRE:
            return 1.5
        elif move.type == PokemonType.WATER:
            return 0.5
    
    # 雨天增强水系，削弱火系
    elif Weather.RAINDANCE in battle.weather or Weather.PRIMORDIALSEA in battle.weather:
        if move.type == PokemonType.WATER:
            return 1.5
        elif move.type == PokemonType.FIRE:
            return 0.5
    
    return 1.0

def calculate_terrain_modifier(attacker: Pokemon, move: Move, battle: AbstractBattle) -> float:
    """计算场地修正"""
    if not hasattr(battle, 'fields') or not battle.fields or not move.type:
        return 1.0
    
    # 检查是否在地面上（简化判断）
    is_grounded = True
    if (PokemonType.FLYING in attacker.types or 
        attacker.ability == "levitate" or 
        getattr(attacker, 'item', None) == "airballoon"):
        is_grounded = False
    
    if not is_grounded:
        return 1.0
    
    # 场地增强
    if Field.ELECTRIC_TERRAIN in battle.fields and move.type == PokemonType.ELECTRIC:
        return 1.3
    elif Field.GRASSY_TERRAIN in battle.fields and move.type == PokemonType.GRASS:
        return 1.3
    elif Field.PSYCHIC_TERRAIN in battle.fields and move.type == PokemonType.PSYCHIC:
        return 1.3
    
    return 1.0

def calculate_ability_modifiers(attacker: Pokemon, defender: Pokemon, move: Move, attack_stat: int, battle: AbstractBattle) -> int:
    """计算特性修正"""
    attacker_ability = attacker.ability
    defender_ability = defender.ability
    
    # 攻击方特性
    if attacker_ability == "hugepower" and move.category == MoveCategory.PHYSICAL:
        attack_stat = int(attack_stat * 2)
    elif attacker_ability == "purepower" and move.category == MoveCategory.PHYSICAL:
        attack_stat = int(attack_stat * 2)
    elif attacker_ability == "guts" and attacker.status == Status.BRN and move.category == MoveCategory.PHYSICAL:
        attack_stat = int(attack_stat * 1.5)
    elif attacker_ability == "technician" and (move.base_power or 80) <= 60:
        attack_stat = int(attack_stat * 1.2)
    
    # 道具修正
    attacker_item = getattr(attacker, 'item', None)
    if attacker_item == "choiceband" and move.category == MoveCategory.PHYSICAL:
        attack_stat = int(attack_stat * 1.5)
    elif attacker_item == "choicespecs" and move.category == MoveCategory.SPECIAL:
        attack_stat = int(attack_stat * 1.5)
    elif attacker_item == "lifeorb":
        attack_stat = int(attack_stat * 1.3)
    
    return attack_stat

def calculate_enhanced_damage(move: Move, target: Pokemon, attacker: Pokemon, battle: AbstractBattle) -> Dict:
    """增强的伤害计算函数"""
    if move.base_power == 0 or move.category == MoveCategory.STATUS:
        return {'ko_prob': 0.0, 'mean_damage': 0.0, 'min_damage': 0, 'max_damage': 0}
    
    # 基础威力
    base_power = move.base_power or 80
    
    # 获取攻击和防御属性
    attack_stat_name = "atk" if move.category == MoveCategory.PHYSICAL else "spa"
    defense_stat_name = "def" if move.category == MoveCategory.PHYSICAL else "spd"
    
    # 特殊处理：Body Press使用防御作为攻击
    if move.id == "bodypress":
        attack_stat_name = "def"
    
    # 获取基础属性值
    attack_stat = getattr(attacker, 'stats', {}).get(attack_stat_name, 300)
    defense_stat = getattr(target, 'stats', {}).get(defense_stat_name, 300)
    
    # 检查属性值是否有效
    if attack_stat is None:
        attack_stat = 300  # 默认值
    if defense_stat is None:
        defense_stat = 300  # 默认值
    
    # 应用特性修正
    attack_stat = calculate_ability_modifiers(attacker, target, move, attack_stat, battle)
    
    # 计算属性相克
    effectiveness = 1.0
    if move.type and target.types:
        for def_type in target.types:
            effectiveness *= get_type_effectiveness_multiplier(move.type, def_type)
    
    if effectiveness == 0:
        return {'ko_prob': 0.0, 'mean_damage': 0.0, 'min_damage': 0, 'max_damage': 0}
    
    # 计算STAB
    stab_multiplier = calculate_stab(attacker, move)
    
    # 计算天气修正
    weather_modifier = calculate_weather_modifier(move, battle)
    
    # 计算场地修正
    terrain_modifier = calculate_terrain_modifier(attacker, move, battle)
    
    # 烧伤修正（物理招式）
    burn_modifier = 1.0
    if (attacker.status == Status.BRN and move.category == MoveCategory.PHYSICAL 
        and attacker.ability != "guts" and move.id != "facade"):
        burn_modifier = 0.5
    
    # 基础伤害公式
    level = getattr(attacker, 'level', 100)
    base_damage = math.floor(
        math.floor(
            (math.floor(2 * level / 5 + 2) * base_power) * attack_stat / defense_stat
        ) / 50 + 2
    )
    
    # 应用所有修正
    final_damage = math.floor(
        base_damage * effectiveness * stab_multiplier * burn_modifier * weather_modifier * terrain_modifier
    )
    
    # 随机伤害范围 (85-100%)
    min_damage = max(1, math.floor(final_damage * 0.85))
    max_damage = max(1, final_damage)
    mean_damage = (min_damage + max_damage) / 2
    
    # 计算KO概率
    target_hp = target.current_hp
    if mean_damage >= target_hp:
        ko_prob = 0.95
    elif max_damage >= target_hp:
        ko_prob = 0.75
    elif min_damage >= target_hp:
        ko_prob = 0.25
    else:
        damage_ratio = mean_damage / target_hp if target_hp > 0 else 0
        ko_prob = min(damage_ratio * 0.8, 0.9)
    
    return {
        'ko_prob': min(ko_prob, 1.0),
        'mean_damage': max(mean_damage, 0.0),
        'min_damage': min_damage,
        'max_damage': max_damage
    }

class CustomAgent(Player):
    
    def __init__(self, *args, **kwargs):
        super().__init__(team=team, *args, **kwargs)
        self.battle_logger = None
        self.performance_stats = {
            'total_battles': 0,
            'wins': 0,
            'losses': 0,
            'total_turns': 0,
            'total_decision_time': 0.0
        }
        self.setup_logging()

    def setup_logging(self):
        """设置简化的日志系统"""
        self.results_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'results')
        os.makedirs(self.results_dir, exist_ok=True)
        
        self.main_logger = logging.getLogger(f'simplified_agent_{id(self)}')
        self.main_logger.setLevel(logging.INFO)
        
        # 清除现有处理器
        for handler in self.main_logger.handlers[:]:
            self.main_logger.removeHandler(handler)
        
        # 创建文件处理器
        log_file = os.path.join(self.results_dir, 'simplified_agent.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.main_logger.addHandler(file_handler)

    def choose_move(self, battle: AbstractBattle):
        """简化的主要决策函数"""
        start_time = time.time()
        
        # 保存当前对战状态以供伤害计算使用
        self._current_battle = battle
        
        # 记录对战开始
        if battle.turn == 1:
            self.main_logger.info(f"开始对战: {battle.battle_tag}")
        
        # 强制换人处理
        if battle.force_switch:
            if battle.available_switches:
                action = self.choose_best_switch(battle.available_switches)
                self.log_decision(battle, action, time.time() - start_time)
                return action
            else:
                action = self.choose_random_move(battle.available_moves)
                self.log_decision(battle, action, time.time() - start_time)
                return action
        
        # 获取当前宝可梦
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        
        # 宝可梦濒死处理
        if not my_pokemon or my_pokemon.fainted:
            if battle.available_switches:
                action = self.choose_best_switch(battle.available_switches)
                self.log_decision(battle, action, time.time() - start_time)
                return action
            else:
                action = self.choose_random_move(battle.available_moves)
                self.log_decision(battle, action, time.time() - start_time)
                return action
        
        # 异常状态处理
        if my_pokemon.status in ['slp', 'frz'] and not self.can_act_this_turn(my_pokemon):
            if battle.available_switches:
                action = self.choose_best_switch(battle.available_switches)
                self.log_decision(battle, action, time.time() - start_time)
                return action
        
        # 优先尝试高伤害攻击
        high_damage_action = self.choose_high_damage_move(battle)
        if high_damage_action:
            self.log_decision(battle, high_damage_action, time.time() - start_time)
            return high_damage_action
        
        # 评估所有可用动作
        action_utilities = self.evaluate_all_actions(battle)
        
        # 选择最佳动作
        if action_utilities:
            best_action = max(action_utilities, key=lambda x: x['utility'])
            action = self.create_order(best_action['action'])
            self.log_decision(battle, action, time.time() - start_time)
            return action
        
        # 后备方案
        if battle.available_switches:
            action = self.choose_best_switch(battle.available_switches)
        else:
            action = self.choose_random_move(battle.available_moves)
        
        self.log_decision(battle, action, time.time() - start_time)
        return action

    def evaluate_all_actions(self, battle: AbstractBattle) -> List[Dict]:
        """评估所有可用动作"""
        action_utilities = []
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        
        if not my_pokemon or not opp_pokemon:
            return action_utilities
        
        # 评估招式
        for move in my_pokemon.moves.values():
            if move.current_pp > 0:
                utility = self.evaluate_move(move, battle, my_pokemon, opp_pokemon)
                action_utilities.append({
                    'action': move,
                    'utility': utility,
                    'type': 'move',
                    'move_type': self.classify_move(move)
                })
        
        # 评估换人
        for switch in battle.available_switches:
            utility = self.evaluate_switch(switch, battle, opp_pokemon)
            action_utilities.append({
                'action': switch,
                'utility': utility,
                'type': 'switch'
            })
        
        return action_utilities

    def evaluate_move(self, move: Move, battle: AbstractBattle, my_pokemon: Pokemon, opp_pokemon: Pokemon) -> float:
        """增强的招式评估"""
        utility = 0.0
        move_type = self.classify_move(move)
        
        # 基础伤害计算
        if move.base_power > 0:
            damage_info = self.calculate_damage(move, opp_pokemon, my_pokemon)
            ko_prob = damage_info['ko_prob']
            mean_damage = damage_info['mean_damage']
            min_damage = damage_info.get('min_damage', mean_damage)
            max_damage = damage_info.get('max_damage', mean_damage)
            
            # KO价值（更高权重）
            utility += ko_prob * 150.0
            
            # 伤害价值
            utility += mean_damage * 0.15
            
            # 稳定性奖励（最小伤害较高）
            if min_damage > 0:
                stability = min_damage / max_damage if max_damage > 0 else 0
                utility += stability * 20.0
            
            # 风险惩罚
            if self.is_risky_move(move, my_pokemon, opp_pokemon):
                utility -= 30.0
            
            # 属性相克奖励
            if move.type and opp_pokemon.types:
                effectiveness = 1.0
                for def_type in opp_pokemon.types:
                    effectiveness *= get_type_effectiveness_multiplier(move.type, def_type)
                
                if effectiveness > 1.0:
                    utility += 30.0  # 克制奖励
                elif effectiveness < 1.0:
                    utility -= 20.0  # 被克制惩罚
        
        # 根据技能类型调整
        if move_type == 'recovery':
            hp_ratio = my_pokemon.current_hp / my_pokemon.max_hp if my_pokemon.max_hp > 0 else 1.0
            if hp_ratio < 0.5:
                utility += 60.0
            elif hp_ratio < 0.7:
                utility += 30.0
        elif move_type == 'setup':
            hp_ratio = my_pokemon.current_hp / my_pokemon.max_hp if my_pokemon.max_hp > 0 else 1.0
            if hp_ratio > 0.6:
                utility += 40.0
        elif move_type == 'status':
            if not opp_pokemon.status:
                utility += 30.0
        elif move_type == 'protection':
            if self.opponent_has_threat_moves(opp_pokemon):
                utility += 25.0
        elif move_type == 'priority':
            opp_hp_ratio = opp_pokemon.current_hp / opp_pokemon.max_hp if opp_pokemon.max_hp > 0 else 1.0
            if opp_hp_ratio < 0.3:
                utility += 50.0
        
        # 应用技能优先级权重
        utility *= PRIORITY_WEIGHTS.get(move_type, 1.0)
        
        return utility

    def evaluate_switch(self, switch: Pokemon, battle: AbstractBattle, opp_pokemon: Pokemon) -> float:
        """简化的换人评估"""
        utility = 0.0
        
        if opp_pokemon and opp_pokemon.moves:
            # 属性相克优势
            for move in opp_pokemon.moves.values():
                if move.base_power > 0:
                    effectiveness = self.calculate_effectiveness(move, switch)
                    if effectiveness < 1.0:  # 抗性
                        utility += 20.0
                    elif effectiveness > 1.0:  # 被克制
                        utility -= 15.0
        
        # 入场伤害惩罚
        entry_damage = self.calculate_entry_damage(switch, battle)
        utility -= entry_damage * 0.5
        
        return utility

    def calculate_damage(self, move: Move, target: Pokemon, attacker: Pokemon) -> Dict:
        """使用增强的伤害计算"""
        # 获取当前对战状态
        battle = getattr(self, '_current_battle', None)
        if not battle:
            # 如果没有对战状态，使用简化计算
            return self._calculate_simple_damage(move, target, attacker)
        
        return calculate_enhanced_damage(move, target, attacker, battle)
    
    def _calculate_simple_damage(self, move: Move, target: Pokemon, attacker: Pokemon) -> Dict:
        """简化的伤害计算（后备方案）"""
        if move.base_power == 0:
            return {'ko_prob': 0.0, 'mean_damage': 0.0}
        
        # 基础威力
        base_power = move.base_power
        
        # 类型相克
        try:
            effectiveness = float(target.damage_multiplier(move))
        except:
            effectiveness = self.calculate_effectiveness(move, target)
        
        if effectiveness == 0:
            return {'ko_prob': 0.0, 'mean_damage': 0.0}
        
        # STAB加成
        stab = 1.5 if move.type and attacker.types and any(move.type.name.upper() == t.name.upper() for t in attacker.types) else 1.0
        
        # 基础伤害计算
        level_factor = 0.44
        base_damage = base_power * level_factor * effectiveness * stab
        
        # 随机因子
        min_damage = base_damage * 0.85
        max_damage = base_damage * 1.0
        mean_damage = (min_damage + max_damage) / 2
        
        # KO概率
        if mean_damage >= target.current_hp:
            ko_prob = 0.95
        elif max_damage >= target.current_hp:
            ko_prob = 0.75
        elif min_damage >= target.current_hp:
            ko_prob = 0.25
        else:
            damage_ratio = mean_damage / target.current_hp if target.current_hp > 0 else 0
            ko_prob = min(damage_ratio * 0.8, 0.9)
        
        return {
            'ko_prob': min(ko_prob, 1.0),
            'mean_damage': max(mean_damage, 0.0)
        }

    def calculate_effectiveness(self, move: Move, target: Pokemon) -> float:
        """计算类型相克"""
        if not move.type or not target.types:
            return 1.0
        
        try:
            effectiveness = float(target.damage_multiplier(move))
            return max(0.0, min(effectiveness, 4.0))
        except:
            # 简化计算
            return 1.0

    def calculate_entry_damage(self, pokemon: Pokemon, battle: AbstractBattle) -> float:
        """计算入场伤害"""
        damage = 0.0
        
        # 隐形岩伤害
        if battle.side_conditions.get('stealthrock', 0) > 0:
            damage += 12.5
        
        # 撒钉伤害
        if battle.side_conditions.get('spikes', 0) > 0:
            damage += 12.5
        
        return damage

    def classify_move(self, move: Move) -> str:
        """技能分类"""
        move_name = str(move).lower()
        
        # 攻击技能
        if move.base_power > 0:
            if move.category == 'Physical':
                return 'physical_attack'
            elif move.category == 'Special':
                return 'special_attack'
            else:
                return 'attack'
        
        # 其他技能类型
        for move_type, moves in MOVE_TYPES.items():
            if move_name in moves:
                return move_type
        
        return 'other'

    def is_risky_move(self, move: Move, my_pokemon: Pokemon, opp_pokemon: Pokemon) -> bool:
        """判断是否为危险招式"""
        # 低HP时攻击技能更危险
        if move.base_power > 0 and my_pokemon.current_hp / my_pokemon.max_hp < 0.3:
            return True
        
        # 被严重克制时更危险
        if self.calculate_effectiveness(move, opp_pokemon) < 0.5:
            return True
        
        return False

    def opponent_has_threat_moves(self, opp_pokemon: Pokemon) -> bool:
        """检查对手是否有威胁招式"""
        if not opp_pokemon or not opp_pokemon.moves:
            return False
        
        for move in opp_pokemon.moves.values():
            if move.base_power >= 100:  # 高威力招式
                return True
        
        return False

    def choose_high_damage_move(self, battle: AbstractBattle) -> Optional[Any]:
        """选择高伤害招式"""
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        if not my_pokemon or not opp_pokemon:
            return None
        
        best_move = None
        best_score = -1
        
        for move in battle.available_moves:
            if move.base_power > 0:
                damage_info = self.calculate_damage(move, opp_pokemon, my_pokemon)
                
                # 综合评分：KO概率 + 伤害值
                score = damage_info['ko_prob'] * 100 + damage_info['mean_damage'] * 0.1
                
                # 优先考虑能KO的招式
                if damage_info['ko_prob'] > 0.8:
                    score += 50
                
                if score > best_score:
                    best_score = score
                    best_move = move
        
        if best_move and best_score > 0:
            return self.create_order(best_move)
        
        return None

    def choose_best_switch(self, available_switches):
        """选择最佳换人"""
        if not available_switches:
            return self.choose_random_move(available_switches)
        
        # 简化选择：随机选择一个
        return self.choose_random_move(available_switches)

    def choose_random_move(self, available_moves):
        """随机选择招式"""
        if not available_moves:
            return None
        
        move = random.choice(available_moves)
        return self.create_order(move)

    def can_act_this_turn(self, pokemon: Pokemon) -> bool:
        """检查当前回合是否能行动"""
        if pokemon.status == 'slp':
            return random.random() > 0.33
        elif pokemon.status == 'frz':
            return random.random() > 0.20
        elif pokemon.status == 'par':
            return random.random() > 0.25
        
        return True

    def log_decision(self, battle: AbstractBattle, action, decision_time: float):
        """记录决策"""
        self.performance_stats['total_decision_time'] += decision_time
        self.performance_stats['total_turns'] += 1
        
        if battle.turn % 10 == 0:  # 每10回合记录一次
            self.main_logger.info(f"回合 {battle.turn}: {action} (决策时间: {decision_time:.3f}s)")

    def _battle_finished_callback(self, battle: AbstractBattle):
        """战斗结束回调"""
        won = battle.won
        self.performance_stats['total_battles'] += 1
        
        if won:
            self.performance_stats['wins'] += 1
        else:
            self.performance_stats['losses'] += 1
        
        # 记录结果
        win_rate = self.performance_stats['wins'] / self.performance_stats['total_battles']
        avg_decision_time = self.performance_stats['total_decision_time'] / self.performance_stats['total_turns'] if self.performance_stats['total_turns'] > 0 else 0
        
        self.main_logger.info(f"对战结束: {'胜利' if won else '失败'} (胜率: {win_rate:.2f}, 平均决策时间: {avg_decision_time:.3f}s)")
        
        # 保存性能统计
        self.save_performance_stats()
        
        super()._battle_finished_callback(battle)

    def save_performance_stats(self):
        """保存性能统计"""
        stats_file = os.path.join(self.results_dir, 'simplified_performance.json')
        
        win_rate = self.performance_stats['wins'] / self.performance_stats['total_battles'] if self.performance_stats['total_battles'] > 0 else 0
        avg_decision_time = self.performance_stats['total_decision_time'] / self.performance_stats['total_turns'] if self.performance_stats['total_turns'] > 0 else 0
        
        stats = {
            'total_battles': self.performance_stats['total_battles'],
            'wins': self.performance_stats['wins'],
            'losses': self.performance_stats['losses'],
            'win_rate': win_rate,
            'total_turns': self.performance_stats['total_turns'],
            'avg_decision_time': avg_decision_time,
            'last_updated': datetime.now().isoformat()
        }
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
