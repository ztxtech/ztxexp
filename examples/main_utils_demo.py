import torch

from ztxexp import utils

print("=" * 20 + " Demonstrating Standalone Utils " + "=" * 20)

# --- 1. 日志设置 ---
logger = utils.setup_logger('my_util_test', './my_test.log')
logger.info("Logger setup complete.")

# --- 2. 计时器 ---
with utils.timer("Data Processing", logger=logger):
    # 模拟耗时操作
    data = [i * i for i in range(10_000_000)]
    logger.info("Data processing finished.")

# --- 3. 配置哈希 ---
my_config = {'lr': 0.01, 'model': 'ResNet', 'layers': [3, 4, 6, 3]}
config_hash = utils.config_to_hash(my_config, length=10)
logger.info(f"Config hash is: {config_hash}")

# --- 4. 打印与内存监控 ---
print("\n--- Pretty Printing Config ---")
utils.pretty_print_dict(my_config)
logger.info(f"Current memory usage: {utils.get_memory_usage()}")

# --- 5. PyTorch模型保存/加载 (示例) ---
model = torch.nn.Linear(10, 2)
optimizer = torch.optim.Adam(model.parameters())
model_path = './my_model.pth'

print("\n--- Saving and Loading PyTorch Model ---")
utils.save_torch_model(model, optimizer, epoch=10, path=model_path)
logger.info(f"Model saved to {model_path}")

model, optimizer, epoch = utils.load_torch_model(model, optimizer, path=model_path)
logger.info(f"Model loaded. Current epoch is {epoch}")
