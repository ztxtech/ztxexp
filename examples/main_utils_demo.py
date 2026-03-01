from __future__ import annotations

from ztxexp import utils

print("=" * 20 + " Standalone Utils Demo " + "=" * 20)

logger = utils.setup_logger("utils_demo", "./utils_demo.log")
logger.info("Logger is ready.")

with utils.timer("processing", logger=logger):
    _ = [i * i for i in range(200000)]

cfg = {"lr": 0.01, "model": "tiny", "layers": [2, 2, 6, 2]}
print("hash:", utils.config_to_hash(cfg, length=10))
utils.pretty_print_dict(cfg)
print("memory:", utils.get_memory_usage())

try:
    import torch

    model = torch.nn.Linear(10, 2)
    optimizer = torch.optim.Adam(model.parameters())
    ckpt = "./demo_model.pth"
    utils.save_torch_model(model, optimizer, epoch=1, path=ckpt)
    model, optimizer, epoch = utils.load_torch_model(model, optimizer, path=ckpt)
    print("torch checkpoint loaded, epoch=", epoch)
except ImportError:
    print("torch is not installed; skip torch checkpoint demo.")
