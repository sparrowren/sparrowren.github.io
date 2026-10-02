# sparrowren.github.io

个人学术阅读站点：在线拍卖、资源调度与边缘智能方向的论文精读。

线上地址：<https://sparrowren.github.io/>

## 结构

```
index.html                       首页（论文清单）
blog/index.html                  原博客占位页
papers/<slug>/index.html         中文全文译本（段落对照阅读器）
papers/<slug>/source.pdf         原文 PDF
papers/<slug>/assets/            译本引用的图片 / 本地 MathJax
recent/                          近期论文原文（作者版 / 预印本）
```

## 已收录

| 目录 | 论文 | 中文译本 |
|---|---|---|
| `papers/ton2016-online-auction` | An Online Auction Framework for Dynamic Resource Provisioning in Cloud Computing (IEEE/ACM ToN) | 有 |
| `papers/eris` | Eris: An Online Auction for Scheduling Unbiased Distributed Learning Over Edge Networks | 有 |
| `papers/serving-longcontext` | Serving Long-Context LLMs at the Mobile Edge | 有 |
| `papers/cached-model-as-a-resource` | Cached Model-as-a-Resource (IEEE ToN 2026) | 有 |
| `papers/edge-ai-inference-tmc2025` | Edge AI Inference as a Service via Dynamic Resources From Repeated Auctions (IEEE TMC 2025) | 原文 |
| `papers/toward-market-assisted-ai-cloud-inference` | Toward Market-Assisted AI Cloud Inference for Streamed Data | 原文 |

## 构建

站点由 `../_work/build_site.py` 从「拍卖」文件夹的译本与 PDF 生成：

```bash
python ../_work/build_site.py
```

脚本会清空本目录（保留 `.git`）后重建，因此**不要直接在这里手改文件**，改动请回到生成脚本。

## 版权

原文版权归原作者与出版方所有；中文译本为个人学习笔记，仅供学习交流。
