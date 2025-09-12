#!/usr/bin/env python3
"""
简单对战测试 - 验证bots是否能正确接受挑战
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

async def test_simple_battle():
    """测试简单的1v1对战"""
    print("🎮 开始简单对战测试...")
    
    # 创建两个简单的players
    player1 = RandomPlayer(
        team=None,
        account_configuration=AccountConfiguration("test_player1", None),
        battle_format="gen9randombattle"
    )
    
    player2 = MaxBasePowerPlayer(
        team=None,
        account_configuration=AccountConfiguration("test_player2", None),
        battle_format="gen9randombattle"
    )
    
    print(f"✅ 创建了玩家: {player1.username} 和 {player2.username}")
    
    # 尝试运行cross_evaluate
    try:
        print("🔄 开始对战...")
        results = await pke.cross_evaluate([player1, player2], n_challenges=1)
        print("✅ 对战完成！")
        print(f"结果: {results}")
        return True
    except Exception as e:
        print(f"❌ 对战失败: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple_battle())
    if success:
        print("🎉 测试成功！")
    else:
        print("💥 测试失败！")
