"""按源码模块自动生成 API 参考页。

该脚本由 ``mkdocs-gen-files`` 在 ``mkdocs build`` 期间执行。
输入是 ``ztxexp`` 包下的 Python 源文件，输出为虚拟 Markdown 页面，
并交给 ``mkdocstrings`` 从 docstring 渲染 API 文档。
"""

from __future__ import annotations

import ast
from pathlib import Path

import mkdocs_gen_files

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "ztxexp"
PACKAGE_INIT = PACKAGE_DIR / "__init__.py"
README_PATH = ROOT / "README.md"
TEMPLATE_DIR = ROOT / "examples" / "template_library"

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


def _extract_docstring(source_text: str) -> str:
    """提取模块 docstring。

    Args:
        source_text: Python 源码文本。

    Returns:
        str: 提取到的 docstring；提取失败时返回空字符串。
    """
    try:
        module_node = ast.parse(source_text)
    except SyntaxError:
        return ""
    return ast.get_docstring(module_node) or ""


def _write_template_library() -> None:
    """生成示例模板库文档页面。"""
    template_nav = mkdocs_gen_files.Nav()
    docs_root = Path("examples-lib")
    matrix_rows: list[tuple[str, str, str]] = []

    with mkdocs_gen_files.open(docs_root / "index.md", "w") as file_obj:
        file_obj.write("# 示例模板库\n\n")
        file_obj.write("该页面由 `examples/template_library` 目录自动生成。\n\n")
        file_obj.write("复制策略：\n\n")
        file_obj.write("1. 找到匹配场景模板；\n")
        file_obj.write("2. 复制脚本并替换 `exp_fn` 内伪逻辑；\n")
        file_obj.write("3. 直接运行并观察标准产物目录。\n")
    template_nav[("场景总览",)] = "index.md"
    mkdocs_gen_files.set_edit_path(docs_root / "index.md", README_PATH.relative_to(ROOT))

    catalog_source = TEMPLATE_DIR / "README.md"
    if catalog_source.exists():
        with mkdocs_gen_files.open(docs_root / "catalog.md", "w") as file_obj:
            file_obj.write(catalog_source.read_text(encoding="utf-8"))
        template_nav[("模板索引表",)] = "catalog.md"
        mkdocs_gen_files.set_edit_path(docs_root / "catalog.md", catalog_source.relative_to(ROOT))

    if not TEMPLATE_DIR.exists():
        with mkdocs_gen_files.open(docs_root / "SUMMARY.md", "w") as nav_file:
            nav_file.writelines(template_nav.build_literate_nav())
        return

    for source_path in sorted(TEMPLATE_DIR.rglob("*.py")):
        relative_source = source_path.relative_to(ROOT)
        relative_template = source_path.relative_to(TEMPLATE_DIR).with_suffix("")
        doc_path = (docs_root / Path(*relative_template.parts)).with_suffix(".md")
        nav_parts = tuple(relative_template.parts)

        source_text = source_path.read_text(encoding="utf-8")
        module_doc = _extract_docstring(source_text)

        with mkdocs_gen_files.open(doc_path, "w") as file_obj:
            file_obj.write(f"# 模板：`{relative_template.as_posix()}`\n\n")
            file_obj.write(f"源文件：`{relative_source.as_posix()}`\n\n")

            if module_doc:
                file_obj.write("## 场景说明\n\n")
                file_obj.write(module_doc.strip() + "\n\n")

            file_obj.write("## 一键复制起步\n\n")
            file_obj.write("```bash\n")
            file_obj.write(f"cp {relative_source.as_posix()} your_experiment.py\n")
            file_obj.write("python your_experiment.py\n")
            file_obj.write("```\n\n")

            file_obj.write("## 模板代码\n\n")
            file_obj.write("```python\n")
            file_obj.write(source_text.rstrip() + "\n")
            file_obj.write("```\n")

        category = relative_template.parts[0] if relative_template.parts else "unknown"
        matrix_rows.append(
            (
                category,
                relative_template.as_posix(),
                f"cp {relative_source.as_posix()} your_experiment.py",
            )
        )

        template_nav[nav_parts] = doc_path.relative_to(docs_root).as_posix()
        mkdocs_gen_files.set_edit_path(doc_path, relative_source)

    with mkdocs_gen_files.open(docs_root / "matrix.md", "w") as file_obj:
        file_obj.write("# 场景复制矩阵\n\n")
        file_obj.write("| 场景分类 | 模板路径 | 复制命令 |\n")
        file_obj.write("| --- | --- | --- |\n")
        for category, template_path, copy_cmd in sorted(matrix_rows):
            file_obj.write(f"| `{category}` | `{template_path}` | `{copy_cmd}` |\n")
    template_nav[("场景复制矩阵",)] = "matrix.md"
    mkdocs_gen_files.set_edit_path(
        docs_root / "matrix.md",
        (TEMPLATE_DIR / "README.md").relative_to(ROOT),
    )

    with mkdocs_gen_files.open(docs_root / "SUMMARY.md", "w") as nav_file:
        nav_file.writelines(template_nav.build_literate_nav())


_write_template_library()
