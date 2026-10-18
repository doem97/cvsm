---
title: 状态
description: rh 处于预发布阶段：这对接口、本站和已知局限意味着什么。
sidebar:
  order: 1
---

rh 处于预发布阶段。它已经用来开发它自己，但在第一个正式版之前，接口仍可能变化。

## 预发布意味着什么

- [保持不变的接口](/research-harness/zh-cn/reference/interfaces/)是对接入方的实现而言的；在第一个正式版之前，rh 自己仍可能改它们。
- 截至 2026-10-18，还没有 tag 或带版本号的发布。在接入提交里记下你复制的 rh commit，以后好对照 rh 的改动。
- 本文档站随第一个正式版发布在 GitHub Pages 上。

## 已知局限

- **结果文字只有中文。** 参考实现 `results.py` 的表头、标注和 `规格核对` 各行都是中文。项目要用别的语言，就改 `results.py`。
- 其他内置文字也是中文：issue 表单的说明、`merge.py` 的输出，以及 skill 为讨论、PR 正文和汇报规定的语言。`AGENTS.md` 的 `Language` 一行设定项目自己的语言；写死中文的这些文件需要相应修改。
- `run.py` 和 `results.py` 是单机参考实现。集群、调度器和远程存储由各接入方自己适配，见[适配你的环境](/research-harness/zh-cn/guides/adapt-your-environment/)。
- 私有仓库的分支保护需要 GitHub 付费套餐。

## 相关页面

- [用 rh 开发 rh](/research-harness/zh-cn/project/built-with-rh/)
- [许可证](/research-harness/zh-cn/project/license/)
- [接入 rh](/research-harness/zh-cn/guides/adopt/)
