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

# Team configuration
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

# Simplified move classification
MOVE_TYPES = {
    'setup': {'swordsdance', 'dragondance', 'quiverdance', 'calmmind', 'nastyplot', 'bulkup', 'agility'},
    'recovery': {'recover', 'roost', 'synthesis', 'moonlight', 'rest', 'slackoff'},
    'status': {'thunderwave', 'willowisp', 'toxic', 'hypnosis', 'sleepspore', 'taunt'},
    'field': {'stealthrock', 'spikes', 'toxicspikes', 'defog', 'rapidspin'},
    'protection': {'protect', 'detect', 'substitute'},
    'priority': {'extremespeed', 'suckerpunch', 'bulletpunch', 'machpunch', 'vacuumwave'}
}

# Move priority weights
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
    """Safely get current Pokemon for both sides"""
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
        """Setup detailed logging system"""
        self.results_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'results')
        os.makedirs(self.results_dir, exist_ok=True)
        
        self.main_logger = logging.getLogger(f'simplified_agent_{id(self)}')
        self.main_logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        for handler in self.main_logger.handlers[:]:
            self.main_logger.removeHandler(handler)
        
        # Create file handler
        log_file = os.path.join(self.results_dir, 'simplified_agent.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.main_logger.addHandler(file_handler)

    def setup_battle_logging(self, battle: AbstractBattle):
        """Setup independent log file for each battle"""
        if not self.current_battle_id or self.current_battle_id != battle.battle_tag:
            self.current_battle_id = battle.battle_tag
            # Initial filename, will be updated based on results later
            self.battle_id = f"battle_{int(time.time())}_{battle.battle_tag}"
            
            # Create battle-specific logger
            self.battle_logger = logging.getLogger(f'battle_{self.battle_id}')
            self.battle_logger.setLevel(logging.DEBUG)
            
            # Clear existing handlers
            for handler in self.battle_logger.handlers[:]:
                self.battle_logger.removeHandler(handler)
            
            # Create battle log file
            battle_log_file = os.path.join(self.results_dir, f'{self.battle_id}.log')
            battle_file_handler = logging.FileHandler(battle_log_file, encoding='utf-8')
            battle_file_handler.setLevel(logging.DEBUG)
            
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            battle_file_handler.setFormatter(formatter)
            self.battle_logger.addHandler(battle_file_handler)
            
            # Record battle start time
            self.battle_start_time = time.time()
            
            # Record battle start information
            self.battle_logger.info("=== Battle Started ===")
            self.battle_logger.info(f"Battle ID: {self.battle_id}")
            self.battle_logger.info(f"Battle Tag: {battle.battle_tag}")
            self.battle_logger.info(f"Opponent: {battle.opponent_username}")
            
            # Record our lead Pokemon
            my_pokemon, opp_pokemon = get_active_pokemon(battle)
            if my_pokemon:
                self.battle_logger.info(f"Our Lead: {my_pokemon.species} (HP: {my_pokemon.current_hp:.2f})")
            if opp_pokemon:
                self.battle_logger.info(f"Opponent Lead: {opp_pokemon.species} (HP: {opp_pokemon.current_hp:.2f})")
                # Record opponent's known moves
                known_moves = [move.id for move in opp_pokemon.moves.values() if move.current_pp > 0]
                self.battle_logger.info(f"Opponent Moves: {known_moves}")

    def choose_move(self, battle: AbstractBattle):
        """Simplified main decision function"""
        start_time = time.time()
        
        # Setup battle logging
        self.setup_battle_logging(battle)
        
        # Record battle start
        if battle.turn == 1:
            self.main_logger.info(f"Starting battle: {battle.battle_tag}")
        
        # Handle forced switch
        if battle.force_switch:
            if battle.available_switches:
                action = self.choose_best_switch(battle.available_switches)
                self.log_decision(battle, action, time.time() - start_time)
                return action
            else:
                action = self.choose_random_move(battle.available_moves)
                self.log_decision(battle, action, time.time() - start_time)
                return action
        
        # Get current Pokemon
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        
        # Record turn start information
        self.log_turn_start(battle, my_pokemon, opp_pokemon)
        
        # Handle fainted Pokemon
        if not my_pokemon or my_pokemon.fainted:
            if battle.available_switches:
                action = self.choose_best_switch(battle.available_switches)
                self.log_decision(battle, action, time.time() - start_time)
                return action
            else:
                action = self.choose_random_move(battle.available_moves)
                self.log_decision(battle, action, time.time() - start_time)
                return action
        
        # Handle status conditions
        if my_pokemon.status in ['slp', 'frz'] and not self.can_act_this_turn(my_pokemon):
            if battle.available_switches:
                action = self.choose_best_switch(battle.available_switches)
                self.log_decision(battle, action, time.time() - start_time)
                return action
        
        # Record damage calculations
        self.log_damage_calculations(battle, my_pokemon, opp_pokemon)
        
        # Prioritize high damage attacks
        high_damage_action = self.choose_high_damage_move(battle)
        if high_damage_action:
            self.log_decision(battle, high_damage_action, time.time() - start_time)
            return high_damage_action
        
        # Evaluate all available actions
        action_utilities = self.evaluate_all_actions(battle)
        
        # Choose best action
        if action_utilities:
            best_action = max(action_utilities, key=lambda x: x['utility'])
            action = self.create_order(best_action['action'])
            self.log_decision(battle, action, time.time() - start_time)
            return action
        
        # Fallback plan
        if battle.available_switches:
            action = self.choose_best_switch(battle.available_switches)
        else:
            action = self.choose_random_move(battle.available_moves)
        
        self.log_decision(battle, action, time.time() - start_time)
        return action

    def evaluate_all_actions(self, battle: AbstractBattle) -> List[Dict]:
        """Evaluate all available actions"""
        action_utilities = []
        my_pokemon, opp_pokemon = get_active_pokemon(battle)
        
        if not my_pokemon or not opp_pokemon:
            return action_utilities
        
        # Evaluate moves
        for move in my_pokemon.moves.values():
            if move.current_pp > 0:
                utility = self.evaluate_move(move, battle, my_pokemon, opp_pokemon)
                action_utilities.append({
                    'action': move,
                    'utility': utility,
                    'type': 'move',
                    'move_type': self.classify_move(move)
                })
        
        # Evaluate switches
        for switch in battle.available_switches:
            utility = self.evaluate_switch(switch, battle, opp_pokemon)
            action_utilities.append({
                'action': switch,
                'utility': utility,
                'type': 'switch'
            })
        
        return action_utilities

    def evaluate_move(self, move: Move, battle: AbstractBattle, my_pokemon: Pokemon, opp_pokemon: Pokemon) -> float:
        """Simplified move evaluation"""
        utility = 0.0
        move_type = self.classify_move(move)
        
        # Basic damage calculation
        if move.base_power > 0:
            damage_info = self.calculate_damage(move, opp_pokemon, my_pokemon)
            ko_prob = damage_info['ko_prob']
            mean_damage = damage_info['mean_damage']
            
            # KO value
            utility += ko_prob * 100.0
            
            # Damage value
            utility += mean_damage * 0.1
            
            # Risk penalty
            if self.is_risky_move(move, my_pokemon, opp_pokemon):
                utility -= 30.0
        
        # Adjust based on move type
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
        
        # Apply move priority weights
        utility *= PRIORITY_WEIGHTS.get(move_type, 1.0)
        
        return utility

    def evaluate_switch(self, switch: Pokemon, battle: AbstractBattle, opp_pokemon: Pokemon) -> float:
        """Simplified switch evaluation"""
        utility = 0.0
        
        if opp_pokemon and opp_pokemon.moves:
            # Type advantage
            for move in opp_pokemon.moves.values():
                if move.base_power > 0:
                    effectiveness = self.calculate_effectiveness(move, switch)
                    if effectiveness < 1.0:  # Resistance
                        utility += 20.0
                    elif effectiveness > 1.0:  # Weakness
                        utility -= 15.0
        
        # Entry damage penalty
        entry_damage = self.calculate_entry_damage(switch, battle)
        utility -= entry_damage * 0.5
        
        return utility

    def calculate_damage(self, move: Move, target: Pokemon, attacker: Pokemon) -> Dict:
        """Simplified damage calculation"""
        if move.base_power == 0:
            return {'ko_prob': 0.0, 'mean_damage': 0.0}
        
        # Base power
        base_power = move.base_power
        
        # Type effectiveness
        try:
            effectiveness = float(target.damage_multiplier(move))
        except:
            effectiveness = self.calculate_effectiveness(move, target)
        
        if effectiveness == 0:
            return {'ko_prob': 0.0, 'mean_damage': 0.0}
        
        # STAB bonus
        stab = 1.5 if move.type and attacker.types and any(move.type.name.upper() == t.name.upper() for t in attacker.types) else 1.0
        
        # Basic damage calculation
        level_factor = 0.44
        base_damage = base_power * level_factor * effectiveness * stab
        
        # Random factor
        min_damage = base_damage * 0.85
        max_damage = base_damage * 1.0
        mean_damage = (min_damage + max_damage) / 2
        
        # KO probability
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
        """Calculate type effectiveness"""
        if not move.type or not target.types:
            return 1.0
        
        try:
            effectiveness = float(target.damage_multiplier(move))
            return max(0.0, min(effectiveness, 4.0))
        except:
            # Simplified calculation
            return 1.0

    def calculate_entry_damage(self, pokemon: Pokemon, battle: AbstractBattle) -> float:
        """Calculate entry damage"""
        damage = 0.0
        
        # Stealth Rock damage
        if battle.side_conditions.get('stealthrock', 0) > 0:
            damage += 12.5
        
        # Spikes damage
        if battle.side_conditions.get('spikes', 0) > 0:
            damage += 12.5
        
        return damage

    def classify_move(self, move: Move) -> str:
        """Move classification"""
        move_name = move.id.lower()
        
        # Attack moves
        if move.base_power > 0:
            if move.category == 'Physical':
                return 'physical_attack'
            elif move.category == 'Special':
                return 'special_attack'
            else:
                return 'attack'
        
        # Other move types
        for move_type, moves in MOVE_TYPES.items():
            if move_name in moves:
                return move_type
        
        return 'other'

    def is_risky_move(self, move: Move, my_pokemon: Pokemon, opp_pokemon: Pokemon) -> bool:
        """Determine if move is risky"""
        # Attack moves are more dangerous at low HP
        if move.base_power > 0 and my_pokemon.current_hp / my_pokemon.max_hp < 0.3:
            return True
        
        # More dangerous when severely resisted
        if self.calculate_effectiveness(move, opp_pokemon) < 0.5:
            return True
        
        return False

    def opponent_has_threat_moves(self, opp_pokemon: Pokemon) -> bool:
        """Check if opponent has threatening moves"""
        if not opp_pokemon or not opp_pokemon.moves:
            return False
        
        for move in opp_pokemon.moves.values():
            if move.base_power >= 100:  # High power moves
                return True
        
        return False

    def choose_high_damage_move(self, battle: AbstractBattle) -> Optional[Any]:
        """Choose high damage move"""
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
        """Choose best switch"""
        if not available_switches:
            return self.choose_random_move(available_switches)
        
        # Simplified choice: randomly select one
        return self.choose_random_move(available_switches)

    def choose_random_move(self, available_moves):
        """Randomly choose move"""
        if not available_moves:
            return None
        
        move = random.choice(available_moves)
        return self.create_order(move)

    def can_act_this_turn(self, pokemon: Pokemon) -> bool:
        """Check if Pokemon can act this turn"""
        if pokemon.status == 'slp':
            return random.random() > 0.33
        elif pokemon.status == 'frz':
            return random.random() > 0.20
        elif pokemon.status == 'par':
            return random.random() > 0.25
        
        return True

    def log_turn_start(self, battle: AbstractBattle, my_pokemon: Optional[Pokemon], opp_pokemon: Optional[Pokemon]):
        """Log turn start information"""
        if self.battle_logger:
            self.battle_logger.info(f"--- Turn {battle.turn} ---")
            if my_pokemon:
                status_str = f"Status:{my_pokemon.status}" if my_pokemon.status else "Status:None"
                self.battle_logger.info(f"Our Status: {my_pokemon.species} HP:{my_pokemon.current_hp:.2f} {status_str}")
            if opp_pokemon:
                status_str = f"Status:{opp_pokemon.status}" if opp_pokemon.status else "Status:None"
                self.battle_logger.info(f"Opponent Status: {opp_pokemon.species} HP:{opp_pokemon.current_hp:.2f} {status_str}")

    def log_damage_calculations(self, battle: AbstractBattle, my_pokemon: Optional[Pokemon], opp_pokemon: Optional[Pokemon]):
        """Log damage calculation process"""
        if not self.battle_logger or not my_pokemon or not opp_pokemon:
            return
        
        for move in my_pokemon.moves.values():
            if move.current_pp > 0 and move.base_power > 0:
                damage_info = self.calculate_damage(move, opp_pokemon, my_pokemon)
                self.battle_logger.debug(f"Damage calculation: {move.id} (Move object) -> {opp_pokemon.species}")
                self.battle_logger.debug(f"  Base power: {move.base_power}")
                self.battle_logger.debug(f"  Expected damage: {damage_info['mean_damage']:.1f}")
                self.battle_logger.debug(f"  KO probability: {damage_info['ko_prob']:.2f}")

    def log_decision(self, battle: AbstractBattle, action, decision_time: float):
        """Log decision"""
        self.performance_stats['total_decision_time'] += decision_time
        self.performance_stats['total_turns'] += 1
        
        if self.battle_logger:
            self.battle_logger.info(f"Decision time: {decision_time:.3f}s")
            
            # Parse action type
            action_str = str(action)
            if "move" in action_str:
                move_name = action_str.split("move ")[-1] if "move " in action_str else "unknown"
                self.battle_logger.info(f"Selected action: /choose move {move_name}")
            elif "switch" in action_str:
                pokemon_name = action_str.split("switch ")[-1] if "switch " in action_str else "unknown"
                self.battle_logger.info(f"Selected action: /choose switch {pokemon_name}")
            else:
                self.battle_logger.info(f"Selected action: {action_str}")
            
            self.battle_logger.info(f"Strategy info: {{'reason': 'strategy_pipeline'}}")
        
        if battle.turn % 10 == 0:  # Log every 10 turns
            self.main_logger.info(f"Turn {battle.turn}: {action} (Decision time: {decision_time:.3f}s)")

    def _battle_finished_callback(self, battle: AbstractBattle):
        """Battle finished callback"""
        won = battle.won
        self.performance_stats['total_battles'] += 1
        
        if won:
            self.performance_stats['wins'] += 1
        else:
            self.performance_stats['losses'] += 1
        
        # Record battle end information
        if self.battle_logger:
            self.battle_logger.info("=== Battle Ended ===")
            self.battle_logger.info(f"Result: {'Victory' if won else 'Defeat'}")
            self.battle_logger.info(f"Battle duration: {time.time() - getattr(self, 'battle_start_time', time.time()):.2f}s")
            self.battle_logger.info(f"Total turns: {battle.turn}")
        
        # Rename log file based on result
        self.rename_battle_log_file(battle)
        
        # Record results
        win_rate = self.performance_stats['wins'] / self.performance_stats['total_battles']
        avg_decision_time = self.performance_stats['total_decision_time'] / self.performance_stats['total_turns'] if self.performance_stats['total_turns'] > 0 else 0
        
        self.main_logger.info(f"Battle ended: {'Victory' if won else 'Defeat'} (Win rate: {win_rate:.2f}, Avg decision time: {avg_decision_time:.3f}s)")
        
        # Save performance stats
        self.save_performance_stats()
        
        super()._battle_finished_callback(battle)

    def rename_battle_log_file(self, battle: AbstractBattle):
        """Rename log file based on battle result"""
        if not hasattr(self, 'battle_id') or not self.battle_id:
            return
        
        old_file_path = os.path.join(self.results_dir, f'{self.battle_id}.log')
        
        if not os.path.exists(old_file_path):
            return
        
        # Determine result prefix
        if battle.won is True:
            result_prefix = "battle_win"
        elif battle.won is False:
            result_prefix = "battle_loss"
        else:
            result_prefix = "battle_tie"  # Tie or unknown result
        
        # Extract timestamp and tag parts from original filename
        parts = self.battle_id.split('_', 1)  # Split "battle" and remaining parts
        if len(parts) > 1:
            suffix = parts[1]  # Timestamp and tag parts
        else:
            suffix = self.battle_id
        
        new_filename = f"{result_prefix}_{suffix}.log"
        new_file_path = os.path.join(self.results_dir, new_filename)
        
        try:
            # Rename file
            os.rename(old_file_path, new_file_path)
            self.main_logger.info(f"Log file renamed: {os.path.basename(old_file_path)} -> {os.path.basename(new_file_path)}")
        except OSError as e:
            self.main_logger.error(f"Failed to rename log file: {e}")

    def save_performance_stats(self):
        """Save performance statistics"""
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
