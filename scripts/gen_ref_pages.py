"""按源码模块自动生成 API 参考页。

该脚本由 ``mkdocs-gen-files`` 在 ``mkdocs build`` 期间执行。
输入是 ``ztxexp`` 包下的 Python 源文件，输出为虚拟 Markdown 页面，
并交给 ``mkdocstrings`` 从 docstring 渲染 API 文档。
"""

from __future__ import annotations

from pathlib import Path

import mkdocs_gen_files

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "ztxexp"
PACKAGE_INIT = PACKAGE_DIR / "__init__.py"
README_PATH = ROOT / "README.md"

nav = mkdocs_gen_files.Nav()


def _write_homepage() -> None:
    """生成站点首页。

    规则：
    1. 优先使用仓库根目录 README.md 作为首页内容；
    2. 若 README 缺失，则退回到最小首页模板。
    """
    if README_PATH.exists():
        content = README_PATH.read_text(encoding="utf-8")
        with mkdocs_gen_files.open("index.md", "w") as file_obj:
            file_obj.write(content)
        mkdocs_gen_files.set_edit_path("index.md", README_PATH.relative_to(ROOT))
        return

    with mkdocs_gen_files.open("index.md", "w") as file_obj:
        file_obj.write("# ztxexp\n\n")
        file_obj.write("README.md 未找到，当前为自动生成的兜底首页。\n\n")
        file_obj.write("## 导航\n\n")
        file_obj.write("- [包级 API（ztxexp）](reference/ztxexp/index.md)\n")
        file_obj.write("- [执行器 API（ExpRunner）](reference/ztxexp/runner.md)\n")
    mkdocs_gen_files.set_edit_path("index.md", PACKAGE_INIT.relative_to(ROOT))


_write_homepage()

for source_path in sorted(PACKAGE_DIR.rglob("*.py")):
    relative_source = source_path.relative_to(ROOT)
    module_path = relative_source.with_suffix("")
    parts = list(module_path.parts)

    if parts[-1] == "__init__":
        parts = parts[:-1]
        identifier = ".".join(parts) if parts else "ztxexp"
        doc_path = Path("reference", *parts, "index.md") if parts else Path("reference/index.md")
        nav_parts = tuple(parts) if parts else ("ztxexp",)
    else:
        identifier = ".".join(module_path.parts)
        doc_path = Path("reference", *parts).with_suffix(".md")
        nav_parts = tuple(parts)

    # literate-nav 的 SUMMARY.md 位于 reference/ 目录，链接需要相对路径。
    nav[nav_parts] = doc_path.relative_to("reference").as_posix()

    with mkdocs_gen_files.open(doc_path, "w") as file_obj:
        file_obj.write(f"# `{identifier}`\n\n")
        file_obj.write(f"::: {identifier}\n")

    mkdocs_gen_files.set_edit_path(doc_path, relative_source)

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
