---
title: License
description: CVSM is licensed under the Apache License 2.0; what that asks of a repo that copies its files.
sidebar:
  order: 3
---

CVSM is licensed under the Apache License, Version 2.0. The full text is in [`LICENSE`](https://github.com/doem97/cvsm/blob/main/LICENSE) at the root of the repository.

## Adopting repos

The adoption copy command copies CVSM's files into your repo but leaves out CVSM's `LICENSE`. Apache-2.0 §4(a) asks anyone who redistributes the files to give recipients a copy of the licence.

So if your repo is published or shared, keep a copy of CVSM's licence with the copied files, for example as `.github/CVSM-LICENSE`:

```sh
cp <cvsm clone>/LICENSE <your repo>/.github/CVSM-LICENSE
```

That name doesn't clash with your project's own `LICENSE`, and `.github/**` is already in guard's `layout`. Your project keeps its own licence.

## Related

- [Status](/cvsm/project/status/)
- [Adopt CVSM](/cvsm/guides/adopt/)
