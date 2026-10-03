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

package pascal.taie.analysis.dataflow.analysis.constprop;

import pascal.taie.analysis.dataflow.analysis.AbstractDataflowAnalysis;
import pascal.taie.analysis.graph.cfg.CFG;
import pascal.taie.config.AnalysisConfig;
import pascal.taie.ir.IR;
import pascal.taie.ir.exp.*;
import pascal.taie.ir.stmt.DefinitionStmt;
import pascal.taie.ir.stmt.Stmt;
import pascal.taie.language.type.PrimitiveType;
import pascal.taie.language.type.Type;
import pascal.taie.util.AnalysisException;

public class ConstantPropagation extends
        AbstractDataflowAnalysis<Stmt, CPFact> {

    public static final String ID = "constprop";

    public ConstantPropagation(AnalysisConfig config) {
        super(config);
    }

    @Override
    public boolean isForward() {
        return true;
    }

    @Override
    public CPFact newBoundaryFact(CFG<Stmt> cfg) {
        // TODO - finish me
        CPFact cpFact = new CPFact();
        for (Var param : cfg.getIR().getParams()) {
            if (canHoldInt(param)) {                   // 只考虑可转换int类型的参数
                cpFact.update(param, Value.getNAC());  // 建立参数到格上值（NAC）的映射
            }
        }
        return cpFact;
    }


    @Override
    public CPFact newInitialFact() {
        // TODO - finish me
        return new CPFact();
    }

    @Override
    public void meetInto(CPFact fact, CPFact target) {
        // TODO - finish me
        for (Var var : fact.keySet()) {
            Value v1 = fact.get(var);
            Value v2 = target.get(var);
            target.update(var, meetValue(v1, v2));
        }
    }


    /**
     * Meets two Values.
     * 计算两个抽象值在格上的汇聚结果 (Meet, ⊓)。
     * 格的层级定义：Undef (Top) > Constant (Middle) > NAC (Bottom)
     */
    public Value meetValue(Value v1, Value v2) {
        // 1. 处理 NAC (Not A Constant) - 格的底元素 (Bottom)
        // 规则：NAC ⊓ any = NAC
        // 说明：只要任一路径上的值已经变为“非常量”，汇聚后的结果必然也是“非常量”。
        if (v1.isNAC() || v2.isNAC()) {
            return Value.getNAC();
        }
        // 2. 处理 Undef (Undefined) - 格的顶元素 (Top)
        // 规则：Undef ⊓ v = v
        // 说明：Undef 表示变量尚未初始化或路径不可达，不包含任何信息，因此汇聚结果取决于另一个值。
        else if (v1.isUndef()) {
            return v2;
        } else if (v2.isUndef()) {
            return v1;
        }
        // 3. 处理常量 (Constant) - 格的中间元素
        // 说明：此时 v1 和 v2 确认为常量，需要判断数值是否一致。
        else if (v1.isConstant() && v2.isConstant()) {
            // 情况 A：数值相同 (e.g., 5 ⊓ 5 = 5) -> 保留该常量
            if (v1.getConstant() == v2.getConstant()) {
                return v1;
            }
            // 情况 B：数值冲突 (e.g., 5 ⊓ 10 = NAC) -> 降级为 NAC
            else {
                return Value.getNAC();
            }
        }
        // 4. 防御性保底
        // 理论上之前的分支已覆盖所有情况，默认返回 NAC 保证安全。
        else {
            return Value.getNAC();
        }
    }

    @Override

    public boolean transferNode(Stmt stmt, CPFact in, CPFact out) {
        // TODO - finish me
        CPFact copy = in.copy();   // 复制in给copy，避免影响in。
        if (stmt instanceof DefinitionStmt) { // 只处理赋值语句
            if (stmt.getDef().isPresent()) {  // 如果左值存在
                LValue lValue = stmt.getDef().get();  // 获取左值
                if ((lValue instanceof Var) && canHoldInt((Var) lValue)) {  // 对于符合条件的左值
                    copy.update((Var) lValue, evaluate(((DefinitionStmt<?, ?>) stmt).getRValue(), copy));  // 计算右值表达式的值用来更新左值变量在格上的值
                }
            }
        }
        return out.copyFrom(copy);  // copy复制给out。copy和in相比，有更新，返回true；反之返回false
    }


    /**
     * @return true if the given variable can hold integer value, otherwise false.
     */
    public static boolean canHoldInt(Var var) {
        Type type = var.getType();
        if (type instanceof PrimitiveType) {
            switch ((PrimitiveType) type) {
                case BYTE:
                case SHORT:
                case INT:
                case CHAR:
                case BOOLEAN:
                    return true;
            }
        }
        return false;
    }


    /**
     * Evaluates the {@link Value} of given expression.
     *
     * @param exp the expression to be evaluated
     * @param in  IN fact of the statement
     * @return the resulting {@link Value}
     */
    public Value evaluate(Exp exp, CPFact in) {
        // 1. 基础情况：变量和字面量
        if (exp instanceof Var) {
            return in.get((Var) exp);
        }
        if (exp instanceof IntLiteral) {
            return Value.makeConstant(((IntLiteral) exp).getValue());
        }
        // 2. 二元表达式处理
        if (exp instanceof BinaryExp) {
            BinaryExp binExp = (BinaryExp) exp;
            Value v1 = in.get(binExp.getOperand1());
            Value v2 = in.get(binExp.getOperand2());
            if (exp instanceof ArithmeticExp) {
                ArithmeticExp.Op op = ((ArithmeticExp) exp).getOperator();
                if ((op == ArithmeticExp.Op.DIV || op == ArithmeticExp.Op.REM)) {
                    if (v2.isConstant() && v2.getConstant() == 0) {
                        return Value.getUndef();
                    }
                }
            }
            // --- 常规 NAC 传播 ---
            // 除零检查通过后，如果任一操作数是 NAC，结果为 NAC
            if (v1.isNAC() || v2.isNAC()) {
                return Value.getNAC();
            }
            // --- 常规 Undef 传播 ---
            // 如果任一操作数是 Undef，结果为 Undef
            if (v1.isUndef() || v2.isUndef()) {
                return Value.getUndef();
            }
            // --- 常量计算 ---
            // 到这里 v1, v2 必定都是 Constant
            int c1 = v1.getConstant();
            int c2 = v2.getConstant();
            // 根据表达式类型分发计算
            if (exp instanceof ArithmeticExp) {
                return calculateArithmetic(((ArithmeticExp) exp).getOperator(), c1, c2);
            } else if (exp instanceof ConditionExp) {
                return calculateCondition(((ConditionExp) exp).getOperator(), c1, c2);
            } else if (exp instanceof BitwiseExp) {
                return calculateBitwise(((BitwiseExp) exp).getOperator(), c1, c2);
            } else if (exp instanceof ShiftExp) {
                return calculateShift(((ShiftExp) exp).getOperator(), c1, c2);
            }
        }
        // 3. 兜底策略 (Tricky Point 2)
        // 对于不支持的表达式 (如 invoke, field load)，保守视为 NAC
        return Value.getNAC();
    }

    // --- 辅助计算方法 (利用 Switch 表达式简化) ---
    private Value calculateArithmetic(ArithmeticExp.Op op, int c1, int c2) {
        int res = switch (op) {
            case ADD -> c1 + c2;
            case SUB -> c1 - c2;
            case MUL -> c1 * c2;
            case DIV -> c1 / c2; // 0 的情况已在 evaluate 顶部处理，此处安全
            case REM -> c1 % c2;
        };
        return Value.makeConstant(res);
    }

    private Value calculateCondition(ConditionExp.Op op, int c1, int c2) {
        // PDF p.6: True -> 1, False -> 0
        boolean res = switch (op) {
            case EQ -> c1 == c2;
            case NE -> c1 != c2;
            case LT -> c1 < c2;
            case GT -> c1 > c2;
            case LE -> c1 <= c2;
            case GE -> c1 >= c2;
        };
        return Value.makeConstant(res ? 1 : 0);
    }

    private Value calculateBitwise(BitwiseExp.Op op, int c1, int c2) {
        int res = switch (op) {
            case OR -> c1 | c2;
            case AND -> c1 & c2;
            case XOR -> c1 ^ c2;
        };
        return Value.makeConstant(res);
    }

    private Value calculateShift(ShiftExp.Op op, int c1, int c2) {
        int res = switch (op) {
            case SHL -> c1 << c2;
            case SHR -> c1 >> c2;
            case USHR -> c1 >>> c2;
        };
        return Value.makeConstant(res);
    }
}