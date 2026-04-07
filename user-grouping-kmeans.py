import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import os
import warnings
warnings.filterwarnings('ignore')
# 调试信息：输出当前工作目录和文件列表
print("当前工作目录:", os.getcwd())
print("当前目录下的文件列表:", os.listdir())

def load_data():
    """文件读取函数，支持读取指定路径的 Excel 文件，这里假设文件为宽格式，包含达人ID和四周的收益"""
    file_path = "达人收益.xlsx"
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"文件 {file_path} 不存在，请检查文件路径。")
        print(f"当前工作目录: {os.getcwd()}")  # 输出当前工作目录
        return None
    try:
        print("尝试读取文件...")
        # 尝试使用不同的引擎读取文件
        try:
            data = pd.read_excel(file_path, engine='openpyxl')
        except:
            data = pd.read_excel(file_path, engine='xlrd')
        print("文件读取成功，正在处理数据...")
        print("数据列名:", data.columns)  # 输出数据列名进行检查
        print("已成功读取文件，即将开始分层计算...")
        # 假设文件包含达人ID和四周的收益列
        return data[['达人ID', '第1周收益', '第2周收益', '第3周收益', '第4周收益']]
    except pd.errors.ParserError:
        print(f"文件 {file_path} 不是有效的 Excel 文件，请检查文件格式。")
    except Exception as e:
        print(f"读取文件时出错: {e}")
    return None

def auto_stratify(df):
    """自动分层函数"""
    # 去除四周收益都低于100的达人
    # 使用逻辑与操作符 & 检查四周收益是否都低于100，然后取反筛选出不符合该条件的达人
    df = df[~((df['第1周收益'] < 10) & (df['第2周收益'] < 10) & (df['第3周收益'] < 10) & (df['第4周收益'] < 10))].copy()

    # 数据预处理，计算四周收益的总和作为聚类特征
    df['四周总收益'] = df[['第1周收益', '第2周收益', '第3周收益', '第4周收益']].sum(axis=1)
    df = df.dropna(subset=['四周总收益']).copy()
    X = df[['四周总收益']].values

    # 标准化处理（消除量纲影响）
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 确定最优聚类数（肘部法则）
    inertia = []
    print("开始计算肘部法则...")
    for k in range(2, 10):
        print(f"正在计算 k = {k} 的惯性值...")
        kmeans = KMeans(n_clusters=k, random_state=42)
        kmeans.fit(X_scaled)
        inertia.append(kmeans.inertia_)
        print(f"k = {k} 的惯性值计算完成")
    print("肘部法则计算完成")

    # 绘制肘部曲线
    plt.figure(figsize=(8, 4))
    plt.plot(range(2, 10), inertia, marker='o')
    plt.title('肘部法则确定最优聚类数')
    plt.xlabel('聚类数')
    plt.ylabel('惯性值')
    plt.show()

    # 用户选择聚类数（这里固定为 6 层）
    n_clusters = 8

    # 执行 K - means 聚类
    print("开始执行 K - means 聚类...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    df['簇标签'] = kmeans.fit_predict(X_scaled)
    print("K - means 聚类完成")

    # 计算各簇中心点
    cluster_centers = scaler.inverse_transform(kmeans.cluster_centers_)
    cluster_centers = np.sort(cluster_centers, axis=0)

    # 生成动态分层规则
    strata_rules = []
    for i in range(n_clusters):
        if i == 0:
            lower = 0
        else:
            lower = cluster_centers[i - 1][0]
        upper = cluster_centers[i][0]
        strata_rules.append((f'层级{i + 1}', (lower, upper)))

    # 转换为分层标签
    df['层级'] = pd.cut(
        df['四周总收益'],
        bins=[rule[1][0] for rule in strata_rules] + [np.inf],
        labels=[rule[0] for rule in strata_rules],
        right=False
    )

    # 计算活动总奖励，基于四周总收益
    total_income = df['四周总收益'].sum()
    total_reward = total_income * 0.03
   # print(f"活动总奖励: {total_reward:.2f} 元")

    # 计算各层级的四周总收益总和
    strata_income = df.groupby('层级')['四周总收益'].sum()

    # 计算各层级的奖励分配比例（层级 1 不参与奖励分配）
    strata_income_without_level1 = strata_income.drop('层级1', errors='ignore')
    total_income_without_level1 = strata_income_without_level1.sum()
    strata_reward_ratio = strata_income_without_level1 / total_income_without_level1

   # print("各层级奖励支出占比（层级 1 不奖励）:")
    #for strata, ratio in strata_reward_ratio.items():
       # print(f"{strata}: {ratio * 100:.2f}%")

    # 计算各层级的奖励金额（层级 1 不奖励）
    strata_reward = strata_reward_ratio * total_reward

    # 计算每个层级达人的数量
    strata_count = df.groupby('层级')['达人ID'].count()

    # 输出层级的数值范围和对应层级一个达人的奖励金额（层级 1 不奖励）
    print("层级数值范围及对应层级一个达人的奖励金额（层级 1 不奖励）:")
    for i, (strata, (lower, upper)) in enumerate(strata_rules):
        if strata == '层级1':
            reward_per_person = 0
        else:
            reward_per_person = strata_reward[strata] / strata_count[strata] if strata_count[strata] > 0 else 0
        print(f"{strata}: {lower:.2f}元 - {upper:.2f}元，单个达人奖励: {reward_per_person:.2f} 元")

    # 计算每个层级达人的相同奖励金额（层级 1 不奖励）
    def calculate_reward(row):
        strata = row['层级']
        if strata == '层级1':
            return 0
        return strata_reward[strata] / strata_count[strata]

    df['奖励金额'] = df.apply(calculate_reward, axis=1)

    return df[['达人ID', '第1周收益', '第2周收益', '第3周收益', '第4周收益', '四周总收益', '层级', '奖励金额']]

def main():
    print("开始执行 main 函数，即将调用 load_data 函数...")
    # 加载数据
    try:
        df = load_data()
        print(f"load_data 函数返回结果: {df}")
        if df is None:
            print("load_data 函数返回 None，程序退出。")
            return
    except Exception as e:
        print(f"数据加载失败: {str(e)}")
        return

    # 执行自动分层
    try:
        result = auto_stratify(df)
    except Exception as e:
        print(f"分层计算失败: {str(e)}")
        return

    # 输出结果
    print("\n分层计算结果：")
    print(result.head())

    # 保存结果
    result.to_csv('分层结果.csv', index=False)
    print("\n结果已保存为 '分层结果.csv'，可在左侧文件列表下载")

if __name__ == "__main__":
    main()
    