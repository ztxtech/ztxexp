from ztxexp.analyzer import ResultAnalyzer

print("=" * 20 + " Cleaning Up Results Directory " + "=" * 20)

try:
    analyzer = ResultAnalyzer(results_path='./results_demo')
except FileNotFoundError as e:
    print(e)
    exit()

# --- 场景1: 清理所有失败或未完成的实验 ---
# 这是最常见的用法。它会查找所有没有 `_SUCCESS` 标记的文件夹。
print("\n--- Scenario 1: Cleaning incomplete runs (Dry Run) ---")
analyzer.clean_results(dry_run=True)
# 如果对结果满意，可以执行真正的删除：
# analyzer.clean_results(dry_run=False)


# --- 场景2: 根据自定义条件清理成功的实验 ---
# 例如，我们想删除所有Transformer模型的实验结果，因为我们决定不再使用它。
print("\n--- Scenario 2: Deleting all 'Transformer' model results (Dry Run) ---")


def filter_for_transformer(config_dict):
    """如果模型的名字是Transformer，则返回True (表示要删除)"""
    return config_dict.get('model') == 'Transformer'


analyzer.clean_results(
    filter_func=filter_for_transformer,
    dry_run=True
)
# 真实删除:
# analyzer.clean_results(filter_func=filter_for_transformer, dry_run=False)


# --- 场景3: 组合条件清理 ---
# 例如，清理所有准确率低于0.8的ResNet实验
print("\n--- Scenario 3: Deleting low-accuracy 'ResNet' runs (Dry Run) ---")


def filter_low_acc_resnet(config_dict):
    if config_dict.get('model') == 'ResNet':
        if config_dict.get('accuracy', 1.0) < 0.8:
            return True
    return False


# 注意：这里我们不设置incomplete_marker，因为我们只想在成功的实验中筛选
analyzer.clean_results(
    incomplete_marker=None,
    filter_func=filter_low_acc_resnet,
    dry_run=True
)
