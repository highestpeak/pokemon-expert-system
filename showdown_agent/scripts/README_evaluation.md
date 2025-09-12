# Pokémon专家系统综合评测实验

本实验系统实现了对Pokémon专家系统的三类核心指标评测：**胜率**、**规则强度**和**稳定性**。

## 🎯 评测指标

### 1. 胜率 (Win Rate)
- **定义**: 直接对战效果的金标准
- **计算**: `WR = Wins / (Wins + Losses)`
- **统计**: Wilson 95%置信区间
- **意义**: 跨对手/环境可横向比较的最终效果

### 2. 规则强度 (Strategy Strength)  
- **定义**: 战术压制力与收尾效率
- **子指标**:
  - 对局时长/回合数 (越短越强)
  - 胜利时剩余宝可梦数 (越多优势越大)
  - 胜利时平均剩余HP% (越高优势越大)
- **意义**: 衡量"赢得如何"，区分"险胜"与"碾压"

### 3. 稳定性 (Stability)
- **定义**: 鲁棒性与泛化能力
- **子指标**:
  - 跨tier泛化 (方差越小越稳)
  - 对手特异失败分析
  - 高不确定性场景表现
- **意义**: 真实环境下的适应性

## 🚀 快速开始

### 1. 环境准备
```bash
# 确保已安装依赖
pip install poke-env scipy numpy pandas matplotlib seaborn

# 确保Pokémon Showdown服务器运行
# 在项目根目录运行: node pokemon-showdown start --no-security
```

### 2. 运行评测
```bash
# 快速评测 (用于测试，5局/配对)
python run_evaluation.py --quick

# 默认评测 (推荐，20局/配对)  
python run_evaluation.py --default

# 全面评测 (50局/配对，所有tier)
python run_evaluation.py --comprehensive

# 稳定性测试 (100局/配对，专注稳定性)
python run_evaluation.py --stability
```

### 3. 自定义配置
```bash
# 交互式创建配置
python run_evaluation.py --create-config

# 使用自定义配置
python run_evaluation.py --custom my_config.json
```

## 📊 输出结果

评测完成后，结果保存在 `evaluation_results/` 目录：

```
evaluation_results/
├── metrics_summary.csv          # 指标汇总表
├── metrics_<agent>.json         # 各agent详细指标
├── battle_summary.csv           # 对战记录汇总
├── figures/
│   └── comprehensive_evaluation.png  # 可视化图表
├── reports/
│   └── evaluation_report.md     # 详细报告
└── logs/                        # 对战日志
    └── battle_*.json           # 单局对战详情
```

## 🔧 配置说明

### Tier配置
- `gen9ubers`: 最高级别，包含传说宝可梦 (难度5)
- `gen9ou`: OverUsed，最常用环境 (难度4)  
- `gen9uu`: UnderUsed，次常用环境 (难度3)
- `gen9ru`: RarelyUsed，较少使用环境 (难度2)
- `gen9nu`: NeverUsed，几乎不使用环境 (难度1)
- `gen9randombattle`: 随机对战 (难度3)

### 对手池配置
- `RandomPlayer`: 完全随机选择行动 (难度1)
- `MaxBasePowerPlayer`: 总是选择威力最高技能 (难度2)
- `SimpleHeuristicsPlayer`: 使用简单启发式规则 (难度3)
- `StrongBot1/2`: 社区强bot示例 (难度4)

### 实验参数
- `matches_per_pair`: 每对agent的对战次数
- `seeds_count`: 随机种子数量
- `max_turns`: 单局最大回合数
- `parallel_battles`: 并行对战数

## 📈 结果解读

### 胜率指标
```csv
agent_name,win_rate,win_rate_ci_lower,win_rate_ci_upper,total_matches,wins,losses
my_agent,0.750,0.650,0.830,100,75,25
```
- `win_rate`: 胜率
- `win_rate_ci_lower/upper`: 95%置信区间
- 置信区间不重叠表示差异显著

### 规则强度指标
```csv
agent_name,median_turns,mean_turns,median_remain_mons,mean_remain_hp
my_agent,45.0,48.2,3.0,65.5
```
- `median_turns`: 中位数回合数 (越小越强)
- `mean_remain_hp`: 平均剩余HP% (越高优势越大)

### 稳定性指标
```csv
agent_name,stability_score,tier_variance,min_tier_win_rate,max_tier_win_rate
my_agent,0.820,0.045,0.650,0.850
```
- `stability_score`: 综合稳定性评分 (0-1)
- `tier_variance`: 跨tier胜率方差 (越小越稳)

## 🎨 可视化报告

系统自动生成以下图表：
1. **胜率对比图**: 含95%置信区间的胜率对比
2. **规则强度散点图**: 回合数 vs 剩余HP的关系
3. **稳定性柱状图**: 各agent的稳定性评分
4. **综合雷达图**: 多维度能力对比

## 🔍 失败原因分析

系统自动分析失败原因并分类：
- **Team Preview Error**: 队伍预览误判
- **Switch Error**: 换人不当
- **Move Selection Error**: 技能选择错误
- **Resource Drain**: 资源管理失败
- **Hax Dominated**: 运气因素主导
- **Endgame Mishandling**: 收尾环节错误

## ⚙️ 高级用法

### 1. 自定义实验配置
```python
from experiment_config import CONFIG_MANAGER

# 创建自定义配置
config = CONFIG_MANAGER.create_custom_config(
    experiment_name="My Custom Test",
    matches_per_pair=50,
    enabled_tiers=["gen9ou", "gen9uu"],
    enabled_opponents=["RandomPlayer", "SimpleHeuristicsPlayer"]
)

# 保存配置
CONFIG_MANAGER.save_config(config, "my_config.json")
```

### 2. 批量实验
```bash
# 运行多个配置
python run_evaluation.py --quick
python run_evaluation.py --default  
python run_evaluation.py --stability
```

### 3. 结果分析
```python
import pandas as pd
import matplotlib.pyplot as plt

# 加载结果
df = pd.read_csv('evaluation_results/metrics_summary.csv')

# 自定义分析
plt.figure(figsize=(10, 6))
plt.bar(df['agent_name'], df['win_rate'])
plt.title('Agent胜率对比')
plt.ylabel('胜率')
plt.xticks(rotation=45)
plt.show()
```

## 🐛 故障排除

### 常见问题

1. **"没有找到自定义agent"**
   - 检查 `players/` 目录是否有 `.py` 文件
   - 确保文件中有 `CustomAgent` 类

2. **"对战失败"**
   - 确保Pokémon Showdown服务器正在运行
   - 检查网络连接
   - 查看日志文件了解具体错误

3. **"内存不足"**
   - 减少 `matches_per_pair` 参数
   - 减少 `parallel_battles` 参数
   - 使用 `--quick` 模式测试

4. **"结果文件为空"**
   - 检查对战是否正常完成
   - 查看 `evaluation.log` 日志文件
   - 确保有足够的磁盘空间

### 调试模式
```bash
# 启用详细日志
export PYTHONPATH=.
python -u run_evaluation.py --quick 2>&1 | tee debug.log
```

## 📚 技术细节

### 统计方法
- **Wilson置信区间**: 用于胜率估计，比正态近似更准确
- **Mann-Whitney U检验**: 用于非正态分布的比较
- **方差分析**: 用于跨tier稳定性评估

### 随机性控制
- 固定种子集确保可重复性
- 先手/后手对称设计
- 每100局轮换种子避免"玄学种子"

### 性能优化
- 并行对战减少总时间
- 增量保存避免数据丢失
- 内存友好的日志格式

## 🤝 贡献指南

欢迎贡献新的评测指标、对手类型或可视化功能！

1. Fork项目
2. 创建功能分支
3. 实现新功能
4. 添加测试
5. 提交Pull Request

## 📄 许可证

本项目遵循MIT许可证。

---

**注意**: 本实验系统基于Pokémon Showdown模拟器，仅用于学术研究和教育目的。
