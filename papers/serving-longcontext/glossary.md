# 术语表

英文（统一中文）：解释。以下定义服务于本论文，不代替正文的精确公式条件。

## Large Language Model (LLM)（大语言模型）

以大规模文本训练的语言模型。本文一个模型可支持多个智能体，模型集合与智能体集合不同。

## LLM agent（LLM 智能体）

由一个或多个 LLM 支撑的任务助手。本文按任务功能区分智能体，不与基础模型一一对应。

## Mobile edge network（移动边缘网络）

在接近移动用户的边缘服务器与集中式云之间安排模型和请求的网络。

## Edge server (ES)（边缘服务器）

具有有限显存和计算/能量预算的服务节点；云索引为 0。

## Model caching（模型缓存）

将模型权重保留在 GPU 显存；缓存决策 a 为二元变量。

## Inference offloading（推理卸载）

把部分推理请求交给云端。本文 b 的定义却是本地执行比例，云端比例为 1−b。

## Context window（上下文窗口）

模型一次可以处理、利用的词元范围上限。本文 w_m 表示其大小。

## Token（词元）

模型处理的文本基本单位，并不恒等于一个汉字或英文单词。

## Chain-of-Thought (CoT)（思维链）

通过中间推理步骤解决任务的提示/推理方式。

## Self-Consistency CoT (SC-CoT)（自洽思维链）

采样多条思维链，对其最终答案进行一致性聚合。多路径不自动代表独立正确。

## Ambiguity（歧义）

原文以概率量 ε 描述上下文/意图的不确定性；定义与假设的具体写法有冲突，需核对。

## Skewness（偏斜）

真实上下文与其他上下文的先验权重差异；均匀先验下原文令相关系数为 1。

## Age of Thought (AoT)（思维年龄）

本文自定义上下文指标 κ，累积有效贡献并减去消逝量，不是通常的时间年龄。

## Vanishing factor（消逝因子）

式（13）中被减去的 Δ；在其他项固定时增大它会降低 κ。

## Consensus factor（共识因子）

式（13）的 ζ，用于加权新生成思维贡献；与单纯路径数量不同。

## Markov decision process (MDP)（马尔可夫决策过程）

把调度表述为状态/观测、动作、转移和奖励；观测是否充分需另有条件。

## Actor（策略网络）

基于观测或适配表示提出动作的网络；本文动作还须经过可行性投影。

## Critic（价值网络）

估计当前状态长期回报，为优势估计提供基准。

## Test-time training (TTT)（测试时训练）

测试阶段用自监督损失更新内部学习器权重 W。本文用于调度策略表示。

## Test-time deep reinforcement learning (T2DRL)（测试时深度强化学习）

本文将 TTT 与 Actor–Critic/PPO 调度结合的方法。

## Proximal policy optimization (PPO)（近端策略优化）

通过限制策略更新幅度改进策略的强化学习方法；本文只提到裁剪目标，未完整列式。

## Generalized advantage estimation (GAE)（广义优势估计）

将时间差分残差按 γλ 加权，用于权衡优势估计的噪声与多步信息。

## Feasibility projection（可行性投影）

将原始网络动作整理为满足显存、执行与资源条件的动作；可行不等于最优。

## Key–value cache (KV cache)（KV 缓存）

推理时缓存注意力的键和值；它的显存需求与模型权重存储不同。

## Double Dutch auction (DDA)（双重荷兰式拍卖）

同步降低买方时钟、提高卖方时钟以发现接受价格的双边交易机制。

## Truthful DDA (t-DDA)（真实双重荷兰式拍卖）

第 V 节采用交易缩减清算和临界支付论证的机制，证明前提与缺口需同时阅读。

## Iterative double auction (IDA)（迭代式双向拍卖）

作为市场层比较基线的迭代报价/要价更新机制。

## Market clearing（市场出清）

确定成交数量、获胜参与者及最终收付价格。

## Dominant-strategy incentive compatibility (DSIC)（占优策略激励相容）

无论其他人的报告如何，如实报告对参与者都是最优策略之一。

## Individual rationality (IR)（个体理性）

如实参与者成交后的效用不为负，落败者效用为零。

## Budget balance（预算平衡）

强预算平衡要求收支完全相等；弱预算平衡只要求不产生赤字。

## Trade reduction（交易缩减）

Case B 舍弃边际可交易一笔，用边际落败报告确定赢家收付价格。

## Social welfare（社会福利）

参与者效用与拍卖人盈余之和；在准线性效用下等于成交真实价值减真实成本。

## Critical payment（临界支付）

赢家支付使自己刚好仍获胜的阈值；阈值须与自己的报告无关，并兼顾平票规则。

## Few-shot learning（少样本学习）

利用少量上下文示例处理任务；不能等同于永久修改模型参数。

## Zero-shot learning（零样本学习）

不提供当前任务示例时进行任务推理；式（14）的 κ=0 值与原文 α 基线需区分。

