# sparrowren.github.io

个人学术阅读站点：在线拍卖、资源调度与边缘智能方向的论文精读。

线上地址：<https://sparrowren.github.io/>

## 结构

```
index.html                       首页（论文清单）
blog/index.html                  原博客占位页
papers/<slug>/index.html         中英对照阅读稿
papers/<slug>/source.pdf         原文 PDF
papers/<slug>/assets/            阅读稿引用的图片 / 本地 MathJax
recent/                          近期论文原文（作者版 / 预印本）
```

## 已收录

四篇已完成中英对照（阅读稿取自 `../中英文对照论文集/<目录>/translation-reading.html`）：

| 目录 | 论文 | 出处 | 对照量 |
|---|---|---|---|
| `papers/ton2016-online-auction` | An Online Auction Framework for Dynamic Resource Provisioning in Cloud Computing | IEEE/ACM ToN 2016 | 180 段 / 32 公式 |
| `papers/eris` | Eris: An Online Auction for Scheduling Unbiased Distributed Learning Over Edge Networks | IEEE TMC 2024 | 257 段 / 48 公式 |
| `papers/serving-longcontext` | Serving Long-Context LLMs at the Mobile Edge | IEEE ToN 2026 | 278 段 / 39 公式 |
| `papers/cached-model-as-a-resource` | Cached Model-as-a-Resource | IEEE ToN 2026 | 219 段 / 33 公式 |

仅原文、译本整理中：

| 目录 | 论文 | 出处 |
|---|---|---|
| `papers/edge-ai-inference-tmc2025` | Edge AI Inference as a Service via Dynamic Resources From Repeated Auctions | IEEE TMC 2025 |
| `papers/toward-market-assisted-ai-cloud-inference` | Toward Market-Assisted AI: Cloud Inference for Streamed Data via Model Ensembles From Auctions | IEEE ToN 2025 |

## 构建

站点由 `../_work/build_site.py` 从「拍卖」文件夹生成：

```bash
python ../_work/build_site.py
```

脚本按「清单同步」的方式重建：覆盖该写的文件，再清掉本目录里多余的残留（`.git` 不动）。
译本只搬阅读稿实际引用到的资源，因此**不要直接在这里手改文件**，改动请回到生成脚本。

## 版权

原文版权归原作者与出版方所有；中文译本为个人学习笔记，仅供学习交流。
