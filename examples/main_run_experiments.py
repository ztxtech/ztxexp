import argparse

from my_experiment import experiment_entrypoint
from ztxexp.manager import ExpManager
from ztxexp.runner import ExpRunner


# --- 1. 定义参数、空间和自定义逻辑 ---
def get_base_args():
    parser = argparse.ArgumentParser(description="高级配置示例")
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--d_model', type=int, default=128)
    return parser.parse_args()


# 定义复杂的搜索空间
GRID_SPACE = {'lr': [0.001, 0.01, 0.1]}  # 0.1会触发失败
VARIANT_SPACE = {'model': ['ResNet', 'Transformer']}
DATASET_VARIANTS = {'dataset': ['CIFAR100', 'SVHN']}


# 定义一个自定义修改器
def modifier_func(args: argparse.Namespace) -> argparse.Namespace:
    """如果模型是Transformer，则加倍其维度"""
    if args.model == 'Transformer':
        args.d_model = 256
    return args


# 定义一个自定义过滤器
def filter_func(args: argparse.Namespace) -> bool:
    """过滤掉Transformer模型在SVHN数据集上的实验（假设不兼容）"""
    if args.model == 'Transformer' and args.dataset == 'SVHN':
        print(f"Filtering out: Transformer on SVHN with lr={args.lr}")
        return False
    return True


# --- 2. 使用ExpManager构建实验流水线 ---
print("=" * 20 + " 1. Managing Configurations " + "=" * 20)
base_args = get_base_args()
manager = ExpManager(base_args)

configs_to_run = (
    manager.add_grid_search(GRID_SPACE)  # 第1步：网格搜索学习率
    .add_variants(VARIANT_SPACE)  # 第2步：为每个学习率添加模型变体
    .add_variants(DATASET_VARIANTS)  # 第3步：再添加数据集变体
    .add_modifier(modifier_func)  # 第4步：应用修改器
    .add_filter(filter_func)  # 第5步：应用过滤器
    .filter_completed('./results_demo')  # 第6步：过滤已完成的
    .get_configs()  # 第7步：生成最终配置列表
)

# --- 3. 使用ExpRunner并行执行 ---
print("\n" + "=" * 20 + " 2. Running Experiments " + "=" * 20)
if not configs_to_run:
    print("🎉 All planned experiments are already completed!")
else:
    runner = ExpRunner(
        configs=configs_to_run,
        exp_function=experiment_entrypoint,
        results_root='./results_demo'
    )
    # 使用joblib并行运行，设置4个工作进程
    runner.run(execution_mode='joblib', num_workers=4)
