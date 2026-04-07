import pandas as pd

# 定义层级范围，包含右侧值
level_ranges = [
    (0, 300),
    (301, 1000),
    (1001, 3000),
    (3001, 5000),
    (5001, 8000),
    (8001, 15000),
    (15001, 30000),
    (30001, 70000)
]

# 定义一个函数，用于确定每个达人所属的层级
def get_level(income):
    for i, (lower, upper) in enumerate(level_ranges):
        if lower <= income <= upper:
            return i + 1
    return None

# 读取达人收益数据
try:
    df = pd.read_excel('达人收益.xlsx')
except FileNotFoundError:
    print("未找到 '达人收益.xlsx' 文件，请检查文件路径。")
    exit(1)
except Exception as e:
    print(f"读取文件时出现错误: {e}")
    exit(1)

# 为每周收益添加层级信息
weeks = ['第1周收益', '第2周收益', '第3周收益', '第4周收益']
for week in weeks:
    df[f'{week[:-2]}层级'] = df[week].apply(get_level)

# 确定每个达人的最终层级
def get_final_level(row):
    levels = [row[f'{week[:-2]}层级'] for week in weeks]
    level_counts = {level: levels.count(level) for level in set(levels) if level is not None}
    if not level_counts:
        return 1
    max_count = max(level_counts.values())
    top_levels = [level for level, count in level_counts.items() if count == max_count]
    if len(top_levels) == 1:
        return top_levels[0]
    # 若多个层级次数相同，比较对应收益总和
    total_income_per_level = {}
    for level in top_levels:
        income_sum = sum([row[weeks[i]] for i in range(4) if levels[i] == level])
        total_income_per_level[level] = income_sum
    return max(total_income_per_level, key=total_income_per_level.get)

df['最终层级'] = df.apply(get_final_level, axis=1)

# 筛选出获奖达人（层级2及以上）
winning_dafs = df[df['最终层级'] > 1]

# 计算获奖达人的总收益
total_winning_income = 0
for week in weeks:
    total_winning_income += winning_dafs[week].sum()

# 计算奖金总数，为获奖达人收益的 0.035 倍
bonus_pool = total_winning_income * 0.035

# 计算每个层级的总收益
level_income = {}
for level in range(2, len(level_ranges) + 1):
    level_df = winning_dafs[winning_dafs['最终层级'] == level]
    level_total_income = 0
    for week in weeks:
        level_total_income += level_df[week].sum()
    level_income[level] = level_total_income

# 计算每个层级的收益占比
total_income_above_level1 = sum(level_income.values())
level_income_ratio = {level: income / total_income_above_level1 for level, income in level_income.items()}

# 计算每个层级的总奖金
level_bonus_total = {1: 0}
for level, ratio in level_income_ratio.items():
    level_bonus_total[level] = bonus_pool * ratio

# 计算每个层级内每个达人的奖金
level_bonus_per_daf = {1: 0}
for level in range(2, len(level_ranges) + 1):
    level_df = winning_dafs[winning_dafs['最终层级'] == level]
    num_dafs = len(level_df)
    if num_dafs > 0:
        level_bonus_per_daf[level] = level_bonus_total[level] / num_dafs
    else:
        level_bonus_per_daf[level] = 0

# 输出每个层级内每个达人的奖金
print("各层级内每个达人的奖金：")
for level in range(1, len(level_ranges) + 1):
    print(f"层级{level}: {level_bonus_per_daf.get(level, 0):.2f} 元")