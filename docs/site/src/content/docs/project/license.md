---
title: License
description: rh is licensed under the Apache License 2.0; what that asks of a repo that copies its files.
sidebar:
  order: 3
---

rh is licensed under the Apache License, Version 2.0. The full text is in [`LICENSE`](https://github.com/doem97/research-harness/blob/main/LICENSE) at the root of the repository.

## Adopting repos

The adoption copy command copies rh's files into your repo but leaves out rh's `LICENSE`. Apache-2.0 §4(a) asks anyone who redistributes the files to give recipients a copy of the licence.

So if your repo is published or shared, keep a copy of rh's licence with the copied files, for example as `.github/RH-LICENSE`:

```sh
cp <rh clone>/LICENSE <your repo>/.github/RH-LICENSE
```

That name doesn't clash with your project's own `LICENSE`, and `.github/**` is already in guard's `layout`. Your project keeps its own licence.

## Related

- [Status](/research-harness/project/status/)
- [Adopt rh](/research-harness/guides/adopt/)
