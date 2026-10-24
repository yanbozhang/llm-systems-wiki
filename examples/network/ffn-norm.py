"""SwiGLU、RMSNorm及残差位置的标准库教学实现。"""
import math


def _linear(matrix, vector):
    if not matrix or any(len(row) != len(vector) for row in matrix):
        raise ValueError("矩阵使用[out,in]布局且须与输入匹配")
    return [sum(a * b for a, b in zip(row, vector)) for row in matrix]


def _sigmoid(x):
    return 1 / (1 + math.exp(-x)) if x >= 0 else math.exp(x) / (1 + math.exp(x))


def swiglu(x, gate_matrix, up_matrix, down_matrix):
    """单token无偏置SwiGLU；返回两分支、门控激活、输出与参数量。"""
    if not x or len(gate_matrix) != len(up_matrix) or len(down_matrix) != len(x):
        raise ValueError("分支宽度与输出宽度须匹配")
    gate, up = _linear(gate_matrix, x), _linear(up_matrix, x)
    hidden = [g * _sigmoid(g) * u for g, u in zip(gate, up)]
    output = _linear(down_matrix, hidden)
    return {"gate": gate, "up": up, "hidden": hidden, "output": output,
            "parameters": 3 * len(x) * len(gate), "hidden_elements": len(hidden)}


def norm_statistics(x, eps=1e-6):
    """计算单位增益的RMSNorm、LayerNorm及RMSNorm解析雅可比。"""
    if not x or not math.isfinite(eps) or eps < 0 or not all(math.isfinite(a) for a in x):
        raise ValueError("输入须有限非空且epsilon非负")
    n = len(x)
    mean = sum(x) / n
    square_mean = sum(a * a for a in x) / n
    variance = sum((a - mean) ** 2 for a in x) / n
    if square_mean + eps <= 0 or variance + eps <= 0:
        raise ValueError("归一化分母不能为零")
    scale = math.sqrt(square_mean + eps)
    rms = [a / scale for a in x]
    layer = [(a - mean) / math.sqrt(variance + eps) for a in x]
    jacobian = [[(1.0 if i == j else 0.0) / scale - x[i] * x[j] / (n * scale**3)
                 for j in range(n)] for i in range(n)]
    return {"mean": mean, "square_mean": square_mean, "variance": variance,
            "rmsnorm": rms, "layernorm": layer, "jacobian": jacobian}


def residual_paths(x, matrix, eps=1e-6):
    """以线性子层F(x)=Ax比较前归一化、后归一化输出与雅可比。"""
    n = len(x)
    if not n or len(matrix) != n or any(len(row) != n for row in matrix):
        raise ValueError("子层矩阵须为输入宽度的方阵")
    norm_x = norm_statistics(x, eps)
    pre = [a + b for a, b in zip(x, _linear(matrix, norm_x['rmsnorm']))]
    inner = [a + b for a, b in zip(x, _linear(matrix, x))]
    norm_inner = norm_statistics(inner, eps)
    identity_plus_a = [[float(i == j) + matrix[i][j] for j in range(n)] for i in range(n)]
    pre_jac = [[float(i == j) + sum(matrix[i][k] * norm_x['jacobian'][k][j] for k in range(n))
                for j in range(n)] for i in range(n)]
    post_jac = [[sum(norm_inner['jacobian'][i][k] * identity_plus_a[k][j] for k in range(n))
                 for j in range(n)] for i in range(n)]
    return {"pre": pre, "post": norm_inner['rmsnorm'], "pre_jacobian": pre_jac,
            "post_jacobian": post_jac}


def demo():
    """返回门控数值、统计量与零子层残差对照。"""
    identity = [[1.0, 0.0], [0.0, 1.0]]
    return {"swiglu": swiglu([1.0, -1.0], identity, identity, identity),
            "norm": norm_statistics([1.0, 3.0]),
            "residual": residual_paths([1.0, 3.0], [[0.0, 0.0], [0.0, 0.0]])}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
