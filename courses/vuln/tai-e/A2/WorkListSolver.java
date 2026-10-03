/*
 * Tai-e: A Static Analysis Framework for Java
 *
 * Copyright (C) 2022 Tian Tan <tiantan@nju.edu.cn>
 * Copyright (C) 2022 Yue Li <yueli@nju.edu.cn>
 *
 * This file is part of Tai-e.
 *
 * Tai-e is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License
 * as published by the Free Software Foundation, either version 3
 * of the License, or (at your option) any later version.
 *
 * Tai-e is distributed in the hope that it will be useful,but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
 * Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with Tai-e. If not, see <https://www.gnu.org/licenses/>.
 */

package pascal.taie.analysis.dataflow.solver;

import pascal.taie.analysis.dataflow.analysis.DataflowAnalysis;
import pascal.taie.analysis.dataflow.fact.DataflowResult;
import pascal.taie.analysis.graph.cfg.CFG;

import java.util.ArrayDeque;

class WorkListSolver<Node, Fact> extends Solver<Node, Fact> {

    WorkListSolver(DataflowAnalysis<Node, Fact> analysis) {
        super(analysis);
    }

    @Override
    protected void doSolveForward(CFG<Node> cfg, DataflowResult<Node, Fact> result) {
        // 1. 初始化 Worklist 和去重集合
        // ArrayDeque 作为 FIFO 队列
        ArrayDeque<Node> worklist = new ArrayDeque<>();
        // Set 用于快速判断节点是否已在队列中 (O(1) 复杂度)
        java.util.Set<Node> inQueue = new java.util.HashSet<>();

        // 将所有节点加入队列
        for (Node node : cfg.getNodes()) {
            worklist.addLast(node);
            inQueue.add(node);
        }

        // 2. 循环处理直到队列为空
        while (!worklist.isEmpty()) {
            Node node = worklist.pollFirst(); // 弹出队头
            inQueue.remove(node);             // 从去重集合移除

            // --- A. 计算 IN 集合 (Meet) ---
            // 关键修正：必须创建一个新的初始 Fact (Top) 作为基底
            Fact newIn = analysis.newInitialFact();

            for (Node pred : cfg.getPredsOf(node)) {
                // 将前驱的 OUT 合并到 newIn 中
                // In[node] = Meet(Out[pred1], Out[pred2], ...)
                analysis.meetInto(result.getOutFact(pred), newIn);
            }

            // 更新当前节点存储的 IN 状态
            result.setInFact(node, newIn);

            // --- B. 计算 OUT 集合 (Transfer) ---
            Fact out = result.getOutFact(node);

            // 执行传递函数
            // transferNode 会根据 newIn 更新 out，并返回 out 是否发生了变化
            boolean changed = analysis.transferNode(node, newIn, out);

            // --- C. 变化传播 ---
            if (changed) {
                // 只有当 OUT 变了，才需要通知后继节点重新计算
                for (Node succ : cfg.getSuccsOf(node)) {
                    // 优化：如果后继节点已经在队列里了，就不用重复加了
                    if (inQueue.add(succ)) { // add 返回 true 表示 Set 中原先没有该元素
                        worklist.addLast(succ);
                    }
                }
            }
        }
    }

        @Override
    protected void doSolveBackward(CFG<Node> cfg, DataflowResult<Node, Fact> result) {
        throw new UnsupportedOperationException();
    }
}
