from poke_env.battle import AbstractBattle, Pokemon, Move
from poke_env.player import Player
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

def get_active_pokemon(battle: AbstractBattle) -> Tuple[Optional[Pokemon], Optional[Pokemon]]:
    """安全获取我方和对手的当前宝可梦"""
    my_pokemon = getattr(battle, 'active_pokemon', None)
    opp_pokemon = getattr(battle, 'opponent_active_pokemon', None)
    
    if my_pokemon and hasattr(my_pokemon, 'fainted'):
        my_pokemon = cast(Pokemon, my_pokemon)
    if opp_pokemon and hasattr(opp_pokemon, 'fainted'):
        opp_pokemon = cast(Pokemon, opp_pokemon)
    
    return my_pokemon, opp_pokemon

class CustomAgent(Player):
    
    def __init__(self, *args, **kwargs):
        super().__init__(team=team, *args, **kwargs)
        self.battle_logger = None
        self.current_battle_id = None
        self.performance_stats = {
            'total_battles': 0,
            'wins': 0,
            'losses': 0,
            'total_turns': 0,
            'total_decision_time': 0.0
        }
        self.setup_logging()

    def setup_logging(self):
        """设置详细的日志系统"""
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

    def setup_battle_logging(self, battle: AbstractBattle):
        """为每个对战设置独立的日志文件"""
        if not self.current_battle_id or self.current_battle_id != battle.battle_tag:
            self.current_battle_id = battle.battle_tag
            # 初始文件名，稍后根据结果更新
            self.battle_id = f"battle_{int(time.time())}_{battle.battle_tag}"
            
            # 创建对战专用日志器
            self.battle_logger = logging.getLogger(f'battle_{self.battle_id}')
            self.battle_logger.setLevel(logging.DEBUG)
            
            # 清除现有处理器
            for handler in self.battle_logger.handlers[:]:
                self.battle_logger.removeHandler(handler)
            
            # 创建对战日志文件
            battle_log_file = os.path.join(self.results_dir, f'{self.battle_id}.log')
            battle_file_handler = logging.FileHandler(battle_log_file, encoding='utf-8')
            battle_file_handler.setLevel(logging.DEBUG)
            
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            battle_file_handler.setFormatter(formatter)
            self.battle_logger.addHandler(battle_file_handler)
            
            # 记录对战开始时间
            self.battle_start_time = time.time()
            
            # 记录对战开始信息
            self.battle_logger.info("=== 对战开始 ===")
            self.battle_logger.info(f"对战ID: {self.battle_id}")
            self.battle_logger.info(f"对战标签: {battle.battle_tag}")
            self.battle_logger.info(f"对手: {battle.opponent_username}")
            
            # 记录我方首发宝可梦
            my_pokemon, opp_pokemon = get_active_pokemon(battle)
            if my_pokemon:
                self.battle_logger.info(f"我方首发: {my_pokemon.species} (HP: {my_pokemon.current_hp:.2f})")
            if opp_pokemon:
                self.battle_logger.info(f"对手首发: {opp_pokemon.species} (HP: {opp_pokemon.current_hp:.2f})")
                # 记录对手已知招式
                known_moves = [move.id for move in opp_pokemon.moves.values() if move.current_pp > 0]
                self.battle_logger.info(f"对手招式: {known_moves}")

    def choose_move(self, battle: AbstractBattle):
        """简化的主要决策函数"""
        start_time = time.time()
        
        # 设置对战日志
        self.setup_battle_logging(battle)
        
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
        
        # 记录回合开始信息
        self.log_turn_start(battle, my_pokemon, opp_pokemon)
        
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
        
        # 记录伤害计算
        self.log_damage_calculations(battle, my_pokemon, opp_pokemon)
        
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
        """简化的招式评估"""
        utility = 0.0
        move_type = self.classify_move(move)
        
        # 基础伤害计算
        if move.base_power > 0:
            damage_info = self.calculate_damage(move, opp_pokemon, my_pokemon)
            ko_prob = damage_info['ko_prob']
            mean_damage = damage_info['mean_damage']
            
            # KO价值
            utility += ko_prob * 100.0
            
            # 伤害价值
            utility += mean_damage * 0.1
            
            # 风险惩罚
            if self.is_risky_move(move, my_pokemon, opp_pokemon):
                utility -= 30.0
        
        # 根据技能类型调整
        if move_type == 'recovery':
            if my_pokemon.current_hp / my_pokemon.max_hp < 0.5:
                utility += 50.0
        elif move_type == 'setup':
            if my_pokemon.current_hp / my_pokemon.max_hp > 0.6:
                utility += 30.0
        elif move_type == 'status':
            if not opp_pokemon.status:
                utility += 25.0
        elif move_type == 'protection':
            if self.opponent_has_threat_moves(opp_pokemon):
                utility += 20.0
        elif move_type == 'priority':
            if opp_pokemon.current_hp / opp_pokemon.max_hp < 0.3:
                utility += 40.0
        
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
        """简化的伤害计算"""
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
        move_name = move.id.lower()
        
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
        best_damage = 0
        
        for move in battle.available_moves:
            if move.base_power > 0:
                damage_info = self.calculate_damage(move, opp_pokemon, my_pokemon)
                if damage_info['mean_damage'] > best_damage:
                    best_damage = damage_info['mean_damage']
                    best_move = move
        
        if best_move and best_damage > 0:
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

    def log_turn_start(self, battle: AbstractBattle, my_pokemon: Optional[Pokemon], opp_pokemon: Optional[Pokemon]):
        """记录回合开始信息"""
        if self.battle_logger:
            self.battle_logger.info(f"--- 第 {battle.turn} 回合 ---")
            if my_pokemon:
                status_str = f"状态:{my_pokemon.status}" if my_pokemon.status else "状态:None"
                self.battle_logger.info(f"我方状态: {my_pokemon.species} HP:{my_pokemon.current_hp:.2f} {status_str}")
            if opp_pokemon:
                status_str = f"状态:{opp_pokemon.status}" if opp_pokemon.status else "状态:None"
                self.battle_logger.info(f"对手状态: {opp_pokemon.species} HP:{opp_pokemon.current_hp:.2f} {status_str}")

    def log_damage_calculations(self, battle: AbstractBattle, my_pokemon: Optional[Pokemon], opp_pokemon: Optional[Pokemon]):
        """记录伤害计算过程"""
        if not self.battle_logger or not my_pokemon or not opp_pokemon:
            return
        
        for move in my_pokemon.moves.values():
            if move.current_pp > 0 and move.base_power > 0:
                damage_info = self.calculate_damage(move, opp_pokemon, my_pokemon)
                self.battle_logger.debug(f"伤害计算: {move.id} (Move object) -> {opp_pokemon.species}")
                self.battle_logger.debug(f"  基础威力: {move.base_power}")
                self.battle_logger.debug(f"  期望伤害: {damage_info['mean_damage']:.1f}")
                self.battle_logger.debug(f"  KO概率: {damage_info['ko_prob']:.2f}")

    def log_decision(self, battle: AbstractBattle, action, decision_time: float):
        """记录决策"""
        self.performance_stats['total_decision_time'] += decision_time
        self.performance_stats['total_turns'] += 1
        
        if self.battle_logger:
            self.battle_logger.info(f"决策时间: {decision_time:.3f}秒")
            
            # 解析动作类型
            action_str = str(action)
            if "move" in action_str:
                move_name = action_str.split("move ")[-1] if "move " in action_str else "unknown"
                self.battle_logger.info(f"选择动作: /choose move {move_name}")
            elif "switch" in action_str:
                pokemon_name = action_str.split("switch ")[-1] if "switch " in action_str else "unknown"
                self.battle_logger.info(f"选择动作: /choose switch {pokemon_name}")
            else:
                self.battle_logger.info(f"选择动作: {action_str}")
            
            self.battle_logger.info(f"策略信息: {{'reason': 'strategy_pipeline'}}")
        
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
        
        # 记录对战结束信息
        if self.battle_logger:
            self.battle_logger.info("=== 对战结束 ===")
            self.battle_logger.info(f"结果: {'胜利' if won else '失败'}")
            self.battle_logger.info(f"对战时长: {time.time() - getattr(self, 'battle_start_time', time.time()):.2f}秒")
            self.battle_logger.info(f"总回合数: {battle.turn}")
        
        # 根据结果重命名日志文件
        self.rename_battle_log_file(battle)
        
        # 记录结果
        win_rate = self.performance_stats['wins'] / self.performance_stats['total_battles']
        avg_decision_time = self.performance_stats['total_decision_time'] / self.performance_stats['total_turns'] if self.performance_stats['total_turns'] > 0 else 0
        
        self.main_logger.info(f"对战结束: {'胜利' if won else '失败'} (胜率: {win_rate:.2f}, 平均决策时间: {avg_decision_time:.3f}s)")
        
        # 保存性能统计
        self.save_performance_stats()
        
        super()._battle_finished_callback(battle)

    def rename_battle_log_file(self, battle: AbstractBattle):
        """根据对战结果重命名日志文件"""
        if not hasattr(self, 'battle_id') or not self.battle_id:
            return
        
        old_file_path = os.path.join(self.results_dir, f'{self.battle_id}.log')
        
        if not os.path.exists(old_file_path):
            return
        
        # 确定结果前缀
        if battle.won is True:
            result_prefix = "battle_win"
        elif battle.won is False:
            result_prefix = "battle_loss"
        else:
            result_prefix = "battle_tie"  # 平局或未知结果
        
        # 提取原始文件名中的时间戳和标签部分
        parts = self.battle_id.split('_', 1)  # 分割出 "battle" 和剩余部分
        if len(parts) > 1:
            suffix = parts[1]  # 时间戳和标签部分
        else:
            suffix = self.battle_id
        
        new_filename = f"{result_prefix}_{suffix}.log"
        new_file_path = os.path.join(self.results_dir, new_filename)
        
        try:
            # 重命名文件
            os.rename(old_file_path, new_file_path)
            self.main_logger.info(f"日志文件已重命名: {os.path.basename(old_file_path)} -> {os.path.basename(new_file_path)}")
        except OSError as e:
            self.main_logger.error(f"重命名日志文件失败: {e}")

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
