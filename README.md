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
_astro/  courses/                主题产物与课程代码库
```

## 已收录

六篇已完成中英对照：

| 目录 | 论文 | 出处 | 对照量 |
|---|---|---|---|
| `papers/ton2016-online-auction` | An Online Auction Framework for Dynamic Resource Provisioning in Cloud Computing（**数学强化版**） | IEEE/ACM ToN 2016 | 122 段 / 32 公式 / 66 译注 |
| `papers/eris` | Eris: An Online Auction for Scheduling Unbiased Distributed Learning Over Edge Networks | IEEE TMC 2024 | 257 段 / 48 公式 / 46 译注 |
| `papers/serving-longcontext` | Serving Long-Context LLMs at the Mobile Edge | IEEE ToN 2026 | 278 段 / 39 公式 / 85 译注 |
| `papers/cached-model-as-a-resource` | Cached Model-as-a-Resource | IEEE ToN 2026 | 219 段 / 33 公式 / 78 译注 |
| `papers/toward-market-assisted-ai-cloud-inference` | Toward Market-Assisted AI: Cloud Inference for Streamed Data via Model Ensembles From Auctions | IEEE ToN 2025 | 260 段 / 22 公式 / 37 译注 |
| `papers/edge-ai-inference-tmc2025` | Edge AI Inference as a Service via Dynamic Resources From Repeated Auctions | IEEE TMC 2025 | 58 段 / 26 公式 / 14 译注 |

`ton2016-online-auction` 是**数学强化版**：在逐段对照之上加了三层教学——
开头的导读（六个问题 / 三个零件 / 3.30 的三笔账 / 全篇地图）、
文末的数学基础工具箱（记号约定、对偶含具体小例子、五条不等式、椭球法与分离预言机、
竞争比结构、符号总表），以及一份 15 条批判与存疑清单，逐条标出原文的排印错误与论证缝隙。
保真版（不含教学层）在 `论文/01_云端资源在线拍卖框架/中英对照译本.html`。

仅原文、译本尚未整理：`recent/` 下的四篇作者版 / 预印本。

## 构建

**站点现在是 Astro 构建产物直接提交**（`index.html` / `_astro/` / `courses/` 均为产物，
本地没有源码），所以不要再跑 `_work/build_site.py`——它会把主题和课程区覆盖回旧版。

更新方式：改 `_work/publish_<slug>_enhanced.py` 这类**幂等补丁脚本**，它只动产物里的目标文件，
重复执行结果一致（跑完用 `md5sum` 复核）。补丁覆盖三件事：写译本产物、
同步首页卡片统计、更新顶部 stat 胶囊的合计值。

```bash
python ../_work/publish_ton2016_enhanced.py
node   ../_work/verify_site_ton2016.cjs      # 需先在站点目录起 http.server
```

**不要直接在这里手改文件**——改动请回到补丁脚本，否则下次重跑会被覆盖。

## 版权

原文版权归原作者与出版方所有；中文译本为个人学习笔记，仅供学习交流。
