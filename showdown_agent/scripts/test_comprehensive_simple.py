#!/usr/bin/env python3
"""
简化版comprehensive_evaluation测试
"""

import asyncio
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append(str(Path(__file__).parent))

import poke_env as pke
from poke_env import AccountConfiguration
from bots.random import CustomAgent as RandomPlayer
from bots.max_damage import CustomAgent as MaxBasePowerPlayer

async def test_comprehensive_simple():
    """测试简化版comprehensive evaluation"""
    print("🎮 开始简化版comprehensive evaluation测试...")
    
    # 创建agents（只创建一个）
    agents = []
    players_dir = Path(__file__).parent / "players"
    
    for py_file in players_dir.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
            
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, "CustomAgent"):
                agent_class = getattr(module, "CustomAgent")
                config = AccountConfiguration(py_file.stem, None)
                agent = agent_class(account_configuration=config, battle_format="gen9ubers")
                agents.append(agent)
                print(f"✅ 加载了agent: {py_file.stem}")
                break  # 只加载一个agent
        except Exception as e:
            print(f"❌ 加载agent {py_file} 失败: {e}")
    
    if not agents:
        print("❌ 没有找到agent")
        return False
    
    # 创建对手（只创建一个）
    opponents = []
    
    # 加载team文件
    bot_teams_folders = Path(__file__).parent / "bots" / "teams"
    bot_teams = {}
    
    if bot_teams_folders.exists():
        for team_file in bot_teams_folders.glob("*.txt"):
            with open(team_file, "r", encoding="utf-8") as f:
                bot_teams[team_file.stem] = f.read()
    
    # 只创建一个对手
    try:
        opponent = RandomPlayer(
            team=None,
            account_configuration=AccountConfiguration("test_opponent", None),
            battle_format="gen9randombattle"
        )
        opponents.append(opponent)
        print(f"✅ 创建了对手: {opponent.username}")
    except Exception as e:
        print(f"❌ 创建对手失败: {e}")
        return False
    
    # 运行测试
    for agent in agents:
        print(f"🔄 测试agent: {agent.username}")
        
        # 创建测试列表：当前agent + 所有对手
        test_agents = [agent] + opponents
        print(f"开始对战，总共 {len(test_agents)} 个玩家")
        
        try:
            cross_evaluation_results = await pke.cross_evaluate(test_agents, n_challenges=1)
            print(f"✅ Agent {agent.username} 对战完成！")
            print(f"结果: {cross_evaluation_results}")
            return True
            
        except Exception as e:
            print(f"❌ Agent {agent.username} 对战失败: {e}")
            return False

if __name__ == "__main__":
    success = asyncio.run(test_comprehensive_simple())
    if success:
        print("🎉 测试成功！")
    else:
        print("💥 测试失败！")
