import pandas as pd

from ztxexp.analyzer import ResultAnalyzer

# 设置pandas显示选项，使其更美观
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

print("=" * 20 + " Analyzing All Results " + "=" * 20)

# --- 1. 初始化分析器 ---
# 即使文件夹不存在，也会优雅地处理，但这里我们假设它存在
try:
    analyzer = ResultAnalyzer(results_path='./results_demo')
except FileNotFoundError as e:
    print(e)
    exit()

# --- 2. 聚合到DataFrame并显示 ---
# to_dataframe只会加载有_SUCCESS标记的成功实验
df = analyzer.to_dataframe(results_filename='results.json')

if df.empty:
    print("No successful experiments found to analyze.")
else:
    print("\n--- Aggregated DataFrame ---")
    # 打印部分关键列
    print(df[['setting', 'model', 'dataset', 'lr', 'accuracy', 'loss', 'time_taken_sec']])

    # --- 3. 保存到CSV ---
    csv_path = './results_demo/summary.csv'
    analyzer.to_csv(output_path=csv_path, sort_by=['dataset', 'model', 'lr'])
    print(f"\n📋 Summary saved to {csv_path}")

    # --- 4. 生成数据透视表 ---
    excel_path = './results_demo/pivot_summary.xlsx'
    analyzer.to_pivot_excel(
        output_path=excel_path,
        df=df,
        index_cols=['dataset', 'model'],  # 行索引
        column_cols=['lr'],  # 列索引
        value_cols=['accuracy'],  # 表格中的值
        add_ranking=True  # 添加 (1st), (2nd) 等排名
    )
    print(f"📊 Pivot table with ranking saved to {excel_path}")
