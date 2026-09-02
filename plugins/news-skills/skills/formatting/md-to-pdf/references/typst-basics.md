# Typst 基础语法参考

当 pandoc 转换无法满足排版需求时，直接编写 .typ 文件用 `typst compile` 生成 PDF。

## 目录

1. [文档结构](#文档结构)
2. [文本格式](#文本格式)
3. [页面设置](#页面设置)
4. [字体配置](#字体配置)
5. [标题与目录](#标题与目录)
6. [列表](#列表)
7. [表格](#表格)
8. [代码块](#代码块)
9. [图片](#图片)
10. [数学公式](#数学公式)
11. [页眉页脚](#页眉页脚)
12. [多栏布局](#多栏布局)
13. [常用模板片段](#常用模板片段)

---

## 文档结构

```typst
// 页面设置放最前面
#set page(paper: "a4", margin: (top: 2cm, bottom: 2cm, left: 2.5cm, right: 2.5cm))
#set text(font: "Noto Serif CJK SC", size: 11pt, lang: "zh")

// 正文
= 一级标题

正文内容。
```

## 文本格式

```typst
*粗体*
_斜体_
`行内代码`
#underline[下划线]
#strike[删除线]
#highlight[高亮]
#link("https://example.com")[链接文字]
```

## 页面设置

```typst
#set page(
  paper: "a4",
  margin: (top: 2cm, bottom: 2cm, left: 2.5cm, right: 2.5cm),
  numbering: "1",  // 页码格式
)
```

## 字体配置

```typst
// 全局字体
#set text(font: "Noto Serif CJK SC", size: 11pt, lang: "zh")

// 多字体回退（英文用第一个，中文回退到第二个）
#set text(font: ("Linux Libertine", "Noto Serif CJK SC"), size: 11pt)
```

## 标题与目录

```typst
// 标题
= 一级标题
== 二级标题
=== 三级标题

// 生成目录
#outline()

// 标题编号
#set heading(numbering: "1.1")
```

## 列表

```typst
// 无序列表
- 项目一
- 项目二
  - 嵌套项

// 有序列表
+ 第一步
+ 第二步
+ 第三步
```

## 表格

```typst
#table(
  columns: (1fr, 2fr, 1fr),
  inset: 8pt,
  align: (left, left, center),
  [*名称*], [*说明*], [*状态*],
  [Pandoc], [文档转换], [稳定],
  [Typst], [排版引擎], [活跃],
)
```

## 代码块

```typst
// 行内代码
`code`

// 代码块
#raw(block: true, lang: "python", "def hello():\n    print('Hello')")

// 或用三反引号
```python
def hello():
    print("Hello")
`` `
```

## 图片

```typst
// 基本图片
#image("path/to/image.png", width: 80%)

// 带标题的图片
#figure(
  image("chart.png", width: 70%),
  caption: [图 1：数据趋势图],
)
```

## 数学公式

```typst
// 行内公式
$E = m c^2$

// 块级公式
$ sum_(i=1)^n x_i = integral_0^1 f(x) dif x $
```

## 页眉页脚

```typst
#set page(
  header: [
    #set text(8pt)
    _文档标题_
    #h(1fr)
    #datetime.today().display()
  ],
  footer: [
    #set text(8pt)
    #h(1fr)
    #counter(page).display("1 / 1", both: true)
  ],
)
```

## 多栏布局

```typst
// 双栏
#columns(2)[
  左栏内容...
  #colbreak()
  右栏内容...
]
```

## 常用模板片段

### 简单报告

```typst
#set page(paper: "a4", margin: 2cm, numbering: "1")
#set text(font: "Noto Serif CJK SC", size: 11pt, lang: "zh")
#set heading(numbering: "1.1")
#set par(justify: true, leading: 0.8em)

#align(center)[
  #text(size: 20pt, weight: "bold")[报告标题]
  #v(0.5em)
  #text(size: 12pt)[作者名 | #datetime.today().display()]
]

#v(1em)
#outline(indent: 1em)
#pagebreak()

= 第一章
正文...
```

### 封面页

```typst
#page(margin: 0pt)[
  #align(center + horizon)[
    #text(size: 28pt, weight: "bold")[文档标题]
    #v(1em)
    #text(size: 14pt)[副标题]
    #v(3em)
    #text(size: 12pt)[
      作者名 \
      组织名 \
      #datetime.today().display()
    ]
  ]
]
```
