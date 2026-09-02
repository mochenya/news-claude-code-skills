# Pandoc CLI 参考

pandoc 是通用文档转换工具，这里聚焦 Markdown → PDF（via Typst）场景的常用选项。

## 基本语法

```bash
pandoc [输入文件...] -o 输出文件 [选项...]
```

## 核心选项

| 选项 | 说明 | 示例 |
|------|------|------|
| `-o FILE` | 输出文件（根据扩展名自动判断格式） | `-o report.pdf` |
| `-f FORMAT` | 输入格式（通常自动检测） | `-f markdown` |
| `-t FORMAT` | 输出格式 | `-t typst` |
| `--pdf-engine=ENGINE` | PDF 引擎 | `--pdf-engine=typst` |
| `-V KEY=VALUE` | 设置模板变量 | `-V mainfont="Noto Serif CJK SC"` |
| `--template=FILE` | 自定义模板 | `--template=my.typ` |
| `--toc` | 生成目录 | |
| `--toc-depth=N` | 目录深度 | `--toc-depth=3` |
| `-N` | 标题自动编号 | |
| `--standalone` / `-s` | 生成完整文档（PDF 时自动启用） | |
| `--metadata=KEY:VALUE` | 设置元数据 | `--metadata=title:"报告"` |

## 输入相关

```bash
# 多个输入文件（按顺序合并）
pandoc ch1.md ch2.md ch3.md -o book.pdf --pdf-engine=typst -V mainfont="Noto Serif CJK SC"

# 从 stdin 读取
echo "# Hello" | pandoc -o hello.pdf --pdf-engine=typst -V mainfont="Noto Serif CJK SC"

# 指定输入编码（默认 UTF-8）
pandoc input.md -o output.pdf --pdf-engine=typst
```

## 模板变量（-V）

用于 typst 引擎时可用的变量：

```bash
# 字体
-V mainfont="Noto Serif CJK SC"    # 正文字体（必填）
-V sansfont="Noto Sans CJK SC"     # 无衬线字体
-V monofont="Noto Sans Mono CJK SC" # 等宽字体
-V fontsize=11pt                    # 字号

# 页面
-V papersize=a4                     # 纸张大小：a4, letter, a5...
-V margin-top=2cm
-V margin-bottom=2cm
-V margin-left=2.5cm
-V margin-right=2.5cm

# 布局
-V columns=2                        # 多栏

# 语言
-V lang=zh
-V dir=ltr                          # 文字方向
```

## Markdown 扩展

pandoc 的 markdown 支持很多扩展，默认大部分已启用：

```bash
# 查看默认启用的扩展
pandoc --list-extensions=markdown | grep "+"

# 启用/禁用特定扩展
pandoc -f markdown+hard_line_breaks input.md -o output.pdf --pdf-engine=typst -V mainfont="Noto Serif CJK SC"
pandoc -f markdown-smart input.md -o output.pdf --pdf-engine=typst -V mainfont="Noto Serif CJK SC"
```

常用扩展：

| 扩展 | 说明 | 默认 |
|------|------|------|
| `yaml_metadata_block` | YAML frontmatter | 开 |
| `table_captions` | 表格标题 | 开 |
| `fenced_code_blocks` | 围栏代码块 | 开 |
| `footnotes` | 脚注 | 开 |
| `tex_math_dollars` | $...$ 数学公式 | 开 |
| `hard_line_breaks` | 换行即断行 | 关 |
| `emoji` | :emoji: 语法 | 关 |

## 元数据与 YAML Frontmatter

在 markdown 文件头部的 YAML 块会被 pandoc 读取为元数据和模板变量：

```yaml
---
title: 文档标题
subtitle: 副标题
author:
  - 作者一
  - 作者二
date: 2026-05-20
abstract: |
  这是摘要内容，支持多行。
mainfont: Noto Serif CJK SC
papersize: a4
toc: true
---
```

命令行 `-V` 和 `--metadata` 会覆盖 frontmatter 中的同名字段。

## 过滤器

```bash
# Lua 过滤器（轻量，推荐）
pandoc input.md -o output.pdf --pdf-engine=typst --lua-filter=filter.lua -V mainfont="Noto Serif CJK SC"

# 查看内置 Lua 过滤器
ls $(pandoc --print-default-data-file "" 2>/dev/null || echo "/usr/share/pandoc")/filters/ 2>/dev/null
```

## 模板操作

```bash
# 导出默认 typst 模板（用于自定义）
pandoc -D typst > custom-template.typ

# 使用自定义模板
pandoc input.md -o output.pdf --pdf-engine=typst --template=custom-template.typ -V mainfont="Noto Serif CJK SC"
```

## 格式转换（非 PDF）

pandoc 也能做其他格式转换，偶尔有用：

```bash
# Markdown → Typst 源文件（不编译 PDF，用于手动调整）
pandoc input.md -o output.typ

# Markdown → HTML
pandoc input.md -o output.html -s

# Markdown → DOCX
pandoc input.md -o output.docx
```

## 调试

```bash
# 查看 pandoc 生成的中间 typst 代码
pandoc input.md -t typst -o intermediate.typ

# 然后手动编译检查
typst compile intermediate.typ output.pdf

# 查看支持的输出格式
pandoc --list-output-formats

# 查看支持的 PDF 引擎
pandoc --list-highlight-languages  # 代码高亮支持的语言
```

## 常见问题

**字体报错 "font fallback list must not be empty"**
→ 必须指定 `-V mainfont="..."`，pandoc 3.x 的 typst 模板不允许空字体列表。

**中文显示为方块或乱码**
→ 确认 mainfont 指向一个包含中文字形的字体。用 `typst fonts | grep CJK` 查看可用中文字体。

**图片路径找不到**
→ pandoc 以 markdown 文件所在目录为基准解析相对路径。用 `--resource-path=DIR` 指定额外搜索路径。

**表格超出页面宽度**
→ 考虑减少列数，或转为 typst 直接编写以获得更精细的列宽控制。
