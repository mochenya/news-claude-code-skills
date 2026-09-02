---
name: md-to-pdf
description: >
  使用 Pandoc + Typst 引擎将 Markdown 转换为 PDF，也支持直接编译 Typst 源文件。
  当用户提到"生成 PDF"、"转成 PDF"、"导出 PDF"、"输出 PDF"、"做个 PDF"，
  或者对话中已经有了文本内容并且需要最终输出为 PDF 文件时，都应触发本 skill。
  即使用户只是说"帮我排版成文档"、"生成一份报告"而没有明确说 PDF，
  只要上下文暗示需要一个可分发的文档文件，也应考虑使用。
---

# Markdown / Typst → PDF 生成

通过 Pandoc + Typst 引擎快速将 Markdown 转为 PDF。Typst 编译速度快、中文支持好、排版质量高。

## 工作流程

根据输入情况选择路径：

1. **已有 .md 文件** → 直接用 pandoc 转换
2. **需要先写内容** → 先生成 .md 文件，再转换
3. **已有 .typ 文件** → 直接用 typst compile 编译
4. **需要精细排版** → 写 .typ 文件，用 typst compile

大多数场景走路径 1 或 2 即可。只有用户明确需要 typst 特有功能（精细排版控制、复杂布局）时才走路径 3/4。

## 核心命令

### Markdown → PDF（最常用）

```bash
pandoc input.md -o output.pdf --pdf-engine=typst \
  -V mainfont="Noto Serif CJK SC" \
  -V sansfont="Noto Sans CJK SC" \
  -V monofont="Noto Sans Mono CJK SC"
```

`mainfont` 是必须的——pandoc 3.x 的 typst 模板在字体列表为空时会报错。

### Typst 直接编译

```bash
typst compile input.typ output.pdf
```

## 常用选项

通过 `-V key=value` 传递给 pandoc，或写在 markdown 的 YAML frontmatter 中：

| 选项 | 说明 | 示例值 |
|------|------|--------|
| mainfont | 正文字体（必填） | Noto Serif CJK SC |
| sansfont | 无衬线字体 | Noto Sans CJK SC |
| monofont | 等宽字体 | Noto Sans Mono CJK SC |
| fontsize | 字号 | 11pt |
| papersize | 纸张 | a4 |
| margin-top | 上边距 | 2cm |
| margin-bottom | 下边距 | 2cm |
| margin-left | 左边距 | 2.5cm |
| margin-right | 右边距 | 2.5cm |
| lang | 语言 | zh |

### 带目录

```bash
pandoc input.md -o output.pdf --pdf-engine=typst --toc \
  -V mainfont="Noto Serif CJK SC"
```

### YAML Frontmatter 方式

在 markdown 文件头部写配置，pandoc 会自动读取：

```markdown
---
title: 文档标题
author: 作者
date: 2026-05-20
mainfont: Noto Serif CJK SC
sansfont: Noto Sans CJK SC
monofont: Noto Sans Mono CJK SC
papersize: a4
margin-top: 2cm
margin-bottom: 2cm
margin-left: 2.5cm
margin-right: 2.5cm
---

正文内容...
```

这样转换时只需：

```bash
pandoc input.md -o output.pdf --pdf-engine=typst
```

## 默认配置

除非用户另有要求，使用以下默认值：

- 字体：Noto Serif CJK SC（正文）、Noto Sans CJK SC（标题/无衬线）、Noto Sans Mono CJK SC（代码）
- 纸张：A4
- 边距：上下 2cm，左右 2.5cm
- 字号：11pt
- 语言：zh

## 输出文件命名

- 如果输入是 `report.md`，输出为 `report.pdf`
- 如果是从头生成内容，根据内容主题命名，如 `weekly-report.pdf`
- 输出到与输入文件相同的目录，除非用户指定其他位置

## 注意事项

- 转换前确认 markdown 语法正确，特别是表格和代码块的闭合
- 如果 markdown 中引用了本地图片，确保路径正确（相对于 markdown 文件位置）
- 数学公式用 `$...$`（行内）和 `$$...$$`（块级），pandoc 会正确传递给 typst
- 如果遇到字体相关错误，首先检查 mainfont 是否设置

## 参考文档

按需查阅，不必每次都读：

- `references/pandoc-cli.md` — pandoc 命令行选项、Markdown 扩展、过滤器、模板操作、调试技巧。当需要用到非常规 pandoc 选项（如合并多文件、自定义模板、Lua 过滤器）时查阅。
- `references/typst-basics.md` — typst 语法基础：页面设置、字体、表格、图片、公式、页眉页脚、模板片段。当需要超出 pandoc 能力的精细排版控制（自定义封面、多栏布局、复杂表格）时查阅。
