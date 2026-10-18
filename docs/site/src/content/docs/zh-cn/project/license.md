---
title: 许可证
description: rh 采用 Apache License 2.0；复制它的文件的仓库需要做什么。
sidebar:
  order: 3
---

rh 采用 Apache License 2.0 许可。全文见仓库根目录的 [`LICENSE`](https://github.com/doem97/research-harness/blob/main/LICENSE)。

## 接入的仓库

接入时的复制命令会把 rh 的文件复制进你的仓库，但不包括 rh 的 `LICENSE`。Apache-2.0 第 4(a) 条要求再分发这些文件的人，把一份许可证交给接收者。

所以，如果你的仓库会公开或分享出去，就随复制来的文件保留一份 rh 的许可证，例如存成 `.github/RH-LICENSE`：

```sh
cp <rh clone>/LICENSE <你的仓库>/.github/RH-LICENSE
```

这个文件名不会和你项目自己的 `LICENSE` 冲突，而且 `.github/**` 本来就在 guard 的 `layout` 里。你的项目照样用自己的许可证。

## 相关页面

- [状态](/research-harness/zh-cn/project/status/)
- [接入 rh](/research-harness/zh-cn/guides/adopt/)
