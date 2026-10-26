---
id: transformer
module: network
status: published
page_version: 3
last_checked: 2026-10-24
depth: worked
practice_status: designed
claim_ids: [claim-transformer-v1, claim-transformer-causal-attention-v1, claim-transformer-head-layout-v1, claim-transformer-autoregressive-loop-v1]
---
# Transformer与自回归生成

Transformer 把“历史内容如何混合”和“下一个 token 如何选择”分成两个层次：注意力与 FFN 计算条件表示，词表投影与抽样规则从表示得到后续 token。原论文是编码器—解码器，本文用仅解码器计算展开三个可核算单元；保留训练并行、生成依赖的核心定义。它们是教学推导，完整训练和 GPU 性能实验均未执行。[Transformer 论文模型架构](https://arxiv.org/html/1706.03762v7#S3)

前置学习：[共同基础](../../docs/共同基础.md)。完整示例：[transformer.py](../../examples/network/transformer.py)。

## 学习目标

- 从单头的方差推导缩放因子，并用未来输入扰动检查因果性。
- 在 token、头、通道三种索引之间追踪同一个元素，解释合并为何不是求平均。
- 用条件概率分解解释 teacher forcing 与串行生成，区分模型分布和采样分布。

## 前置知识

需要矩阵乘法、条件概率、方差与 softmax。本文输入按行放 token，序列长度为 $T$ ，隐藏宽度为 $C$ ，头数为 $H$ ，每头键宽度 $d_k=C/H$ ； $B$ 是批量大小。源码的线性层权重通常存成 `[out,in]`，数学行向量式写作 $XW$ 时要作转置，不能仅凭打印出的形状判断乘法错误。

## 基本机制

token ID 经 embedding 和位置信息成为 $X\in\mathbb R^{B\times T\times C}$ 。每层得到 Q/K/V，用注意力跨位置混合，再由逐位置 FFN 变换特征，残差保留输入通路。最后的词表 logits $z_t$ 描述 $p(x_{t+1}\mid x_{\le t})$ ，并非 $x_t$ 的标签。该版本 nanoGPT 的 `GPT.forward` 在训练时投影全部位置；推理时只投影末位置。原 Transformer 的 Post-Norm 与这里的 Pre-Norm 不相同，不能把具体模型代码当作论文架构逐行复刻。[nanoGPT Block 与 GPT.forward](https://github.com/karpathy/nanoGPT/blob/3adf61e154c3fe3fca428ad6bc3818b27a3b8291/model.py#L94-L193)

## 推导或示例

### 知识点一：缩放、可见范围与稳定的因果注意力

**问题与机制。** 为什么点积要除以平方根，而且屏蔽未来必须发生在归一化之前？令 $q,k\in\mathbb R^{d_k}$ 的分量相互独立、均值为零且方差为一。则 $\mathrm{Var}(q_i k_i)=1$ ，交叉协方差为零，所以 $\mathrm{Var}(q^Tk)=d_k$ ；除以 $\sqrt{d_k}$ 后方差回到一。这个推导解释初始化尺度，并不声称训练后分量仍然独立。得分过大时 softmax 接近单点，雅可比 $\partial a_i/\partial s_j=a_i(\mathbf1_{i=j}-a_j)$ 的许多元素接近零。[Transformer 缩放点积与因果掩码](https://arxiv.org/html/1706.03762v7#S3.SS2)

定义 $s_{ij}=q_i^Tk_j/\sqrt{d_k}$ ， $M_{ij}=0$ （ $j\le i$ ）或 $-\infty$ （ $j\gt i$ ）。输出为

$$
a_{ij}=\frac{\exp(s_{ij}+M_{ij}-c_i)}{\sum_{r\le i}\exp(s_{ir}-c_i)},\quad
c_i=\max_{r\le i}s_{ir},\quad o_i=\sum_{j\le i}a_{ij}v_j.
$$

$c_i$ 是同一行的常数，会在分子分母约去；它防止指数上溢。教学实现直接截取可见键，等价于先加 $-\infty$ ，然后把未来权重补零。输入 Q/K 为 `[T,dk]`，V 为 `[T,dv]`；返回 `[T,T]` 权重与 `[T,dv]` 输出。

```python
def causal_attention(q, k, v):
    """输入同长二维 Q/K/V；返回因果权重矩阵与加权输出。"""
    n = len(q)
    if not n or len(k) != n or len(v) != n or not q[0] or not v[0]:
        raise ValueError("Q/K/V须同长非空")
    d, dv = len(q[0]), len(v[0])
    if any(len(row) != d for row in q + k) or any(len(row) != dv for row in v):
        raise ValueError("各行维度须一致")
    if any(not math.isfinite(x) for row in q + k + v for x in row):
        raise ValueError("输入须有限")
    weights, output = [], []
    for i, query in enumerate(q):
        visible = [sum(a * b for a, b in zip(query, key)) / math.sqrt(d)
                   for key in k[:i + 1]]
        row = _softmax(visible) + [0.0] * (n - i - 1)
        weights.append(row)
        output.append([sum(row[j] * v[j][c] for j in range(n)) for c in range(dv)])
    return {"weights": weights, "output": output}
```

逐步核算第二行：取 $d_k=4$ 、未缩放分数 `[2,0,1]`、V 的一个通道为 `[1,3,9]`。可见分数 `[1,0]` 的权重为 `[0.731059,0.268941]`，输出约 $1.537883$ ；第三项不参与分母。若先对三个得分 softmax 再把第三项置零，剩余权重和只有约 $0.692804$ ，输出也改变。这个反例能区分“数值看起来合理”和“分布定义正确”。

```mermaid
flowchart LR
    Q["查询行与历史键"] --> D["点积除以头宽平方根"]
    D --> M["截去未来键"]
    M --> S["减去可见最大值并归一化"]
    S --> Z["补零得到整行权重"]
    Z --> V["对值向量加权求和"]
```

**源码定位。** 该版本源码显示，`CausalSelfAttention.forward` 的普通路径依次缩放、`masked_fill`、softmax、dropout、乘 V；融合路径把 `is_causal=True` 交给 SDPA。[nanoGPT CausalSelfAttention.forward](https://github.com/karpathy/nanoGPT/blob/3adf61e154c3fe3fca428ad6bc3818b27a3b8291/model.py#L52-L75) 对照 [PyTorch SDPA 掩码与 dropout 约定](https://docs.pytorch.org/docs/2.14/generated/torch.nn.functional.scaled_dot_product_attention.html)，布尔 `True` 表示允许参与，评估时需显式传 `dropout_p=0`，不能沿用其他接口的屏蔽语义。

**条件与反例。** 示例是无 padding、方形自注意力、无 dropout 的有限输入；任一行全部屏蔽时分母为零，必须由调用方定义处置。缓存解码的 Q/K 长度不同，不能直接把本函数的下三角规则扩展成矩形规则。对未来 K/V 的扰动不应影响较早输出，但改动当前 query 本身当然会影响当前行。

### 知识点二：多头的索引变换与输出投影

**问题与机制。** 拆头不会凭空新增 token，也不是把同一个注意力结果平均 $H$ 次。输入先由学习得到的投影产生 $Q,K,V\in\mathbb R^{B\times T\times C}$ ，再重排为 `[B,H,T,dk]`。令通道索引 $c=h d_k+r$ ，则 $Q^\prime_{b,h,t,r}=Q_{b,t,c}$ 。每头独立得到 $O_h=A_hV_h$ ，最后

$$
O_{b,t,:}=\mathrm{Concat}(O_{b,0,t,:},\ldots,O_{b,H-1,t,:})W_O,
\qquad W_O\in\mathbb R^{C\times C}.
$$

每头有自己的相似度分布，因此 $H$ 个 `[T,T]` 矩阵不能合成一个固定平均权重来代替； $W_O$ 还会混合不同头的通道。投影、reshape、转置、连接四者各有职责。[Transformer 多头注意力](https://arxiv.org/html/1706.03762v7#S3.SS2.SSS2)

```python
def split_merge_heads(rows, heads):
    """把 [T,C] 拆为 [H,T,D] 再按原顺序合并；不做投影。"""
    if not rows or not rows[0] or not isinstance(heads, int) or heads <= 0:
        raise ValueError("输入非空且头数为正整数")
    width = len(rows[0])
    if width % heads or any(len(row) != width for row in rows):
        raise ValueError("宽度须一致且可被头数整除")
    d = width // heads
    split = [[list(row[h * d:(h + 1) * d]) for row in rows] for h in range(heads)]
    merged = [[x for h in range(heads) for x in split[h][t]] for t in range(len(rows))]
    return {"heads": split, "merged": merged, "shape": [heads, len(rows), d]}
```

函数只演示元素索引。输入 `[[0,1,2,3],[4,5,6,7]]`、 $H=2$ 时，第一头为 `[[0,1],[4,5]]`，第二头为 `[[2,3],[6,7]]`；还原后必须与输入逐元素一致。实际调用应分别把投影后的 Q/K/V 拆头，再调用各头的因果注意力，最后连接输出。代码返回 `shape=[2,2,2]` 只是这一小例；旧页的 $B=1,T=3,C=8,H=2$ 对应 `[1,2,3,4]`。

```mermaid
flowchart LR
    X["逐token投影后的通道"] --> R["按头切分连续通道"]
    R --> T["转为头在前的索引"]
    T --> A["每头独立计算注意力"]
    A --> C["按token连接全部头"]
    C --> W["输出投影混合通道"]
```

**源码定位。** 该版本 `view(...).transpose(1,2)` 将头移到前面；反向 `transpose(...).contiguous().view(...)` 恢复 token 布局。`contiguous` 处理内存布局，不能用一次错误的 reshape 替代转置。[nanoGPT 拆头、还原与输出投影](https://github.com/karpathy/nanoGPT/blob/3adf61e154c3fe3fca428ad6bc3818b27a3b8291/model.py#L55-L75) [PyTorch SDPA 张量形状约定](https://docs.pytorch.org/docs/2.14/generated/torch.nn.functional.scaled_dot_product_attention.html)

**条件与反例。** $C$ 必须被 $H$ 整除。函数拒绝宽度为三而头数为二的输入。它不含学习投影、输出投影或批维；它能验证索引往返，不能验证多头质量优势。把上例直接重排为两个连续块 `[[0,1],[2,3]]` 和 `[[4,5],[6,7]]` 会把 token 和头交换，虽然元素数量完全相同。

### 知识点三：训练并行、生成依赖与采样分布

**问题与机制。** 无循环神经网络不意味着普通自回归生成可以同时决定所有未来 token。链式法则为

$$
p_\theta(x_{1:T})=\prod_{t=1}^{T}p_\theta(x_t\mid x_{\lt t}),\qquad
\log p_\theta(x_{1:T})=\sum_t\log p_\theta(x_t\mid x_{\lt t}).
$$

teacher forcing 在训练时已知全部真实历史，可以一次带因果掩码的前向得到所有条件项；生成时 $x_t$ 尚未得到，下一项的输入要等当前抽样。下例将真实网络简化成“末 token→下一 token logits”的转移表，保留状态依赖，便于重放每一步。它不是用一阶马尔可夫链描述真实 Transformer 的全部记忆。[Transformer 自回归解码说明](https://arxiv.org/html/1706.03762v7#S3)

设温度 $\tau\gt 0$ ，保留集合 $K$ 由 top-k 阈值确定，则采样分布是 $q_i=\mathbf1_{i\in K}\exp(z_i/\tau)/\sum_{j\in K}\exp(z_j/\tau)$ 。 $\tau$ 不改变 logits 排序，却改变概率集中程度；top-k 删除支持集外的事件，不能把它的概率当作原模型似然。下面把随机数显式作为 `draws` 输入，按累积概率选 token。

```python
def generate_tokens(transition_logits, start, draws, temperature=1.0, top_k=None):
    """用末token转移表模拟自回归循环；draws给出每步零到一的抽样位置。"""
    size = len(transition_logits)
    if not size or any(len(row) != size for row in transition_logits):
        raise ValueError("转移表须为非空方阵")
    if not isinstance(start, int) or not 0 <= start < size:
        raise ValueError("起始token越界")
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("温度须为有限正数")
    if top_k is not None and (not isinstance(top_k, int) or not 1 <= top_k <= size):
        raise ValueError("top_k须在词表范围内")
    tokens, trace = [start], []
    for u in draws:
        if not 0 <= u < 1:
            raise ValueError("抽样位置须在[0,1)")
        logits = transition_logits[tokens[-1]]
        if not all(math.isfinite(x) for x in logits):
            raise ValueError("logits须有限")
        threshold = sorted(logits, reverse=True)[(top_k or size) - 1]
        keep = [i for i, score in enumerate(logits) if score >= threshold]
        probs = _softmax([logits[i] / temperature for i in keep])
        cumulative, chosen = 0.0, keep[-1]
        for i, p in zip(keep, probs):
            cumulative += p
            if u < cumulative:
                chosen = i
                break
        trace.append({"history": list(tokens), "candidates": keep, "probabilities": probs})
        tokens.append(chosen)
    return {"tokens": tokens, "trace": trace}
```

输入两行 logits `[0,ln3]` 与 `[ln4,0]`，初始 token 为0、两次 draw 均为0.5：第一步分布 `[0.25,0.75]` 选择1；第二步查第1行，分布 `[0.8,0.2]` 选择0，得到 `[0,1,0]`。若错误地复用初始行，第二步仍选1。这里序列的两步条件概率乘积为 $0.75\times0.8=0.6$ ，不是两个概率相加。

```mermaid
flowchart LR
    H["当前历史与末token"] --> L["计算本步logits"]
    L --> F["温度缩放与top-k筛选"]
    F --> P["归一化采样分布"]
    P --> U["用指定随机位置选择token"]
    U --> N["追加历史"]
    N --> H
```

**源码定位。** 该版本 `GPT.generate` 逐步裁剪输入、前向、温度缩放、阈值过滤、`multinomial`、追加。阈值保留并列项，候选数可能多于 k，示例也保留这一语义。[nanoGPT GPT.generate](https://github.com/karpathy/nanoGPT/blob/3adf61e154c3fe3fca428ad6bc3818b27a3b8291/model.py#L305-L330) 模型概率与一步一个 token 的语义对应 [Transformer 解码架构](https://arxiv.org/html/1706.03762v7#S3)。

**条件与反例。** 函数要求正温度及 `[0,1)` 的抽样值，不接受把温度零当作浮点除法的贪心解码。该版本 nanoGPT 的生成没有 KV 缓存，不能把循环中的最后位置投影优化等同于缓存历史层激活。真实模型还有 EOS、停止条件、重复约束、上下文截断与跨步缓存位置，教学表格均未实现。

## 适用条件与限制

这些计算针对稠密注意力的数学语义。显式权重矩阵包含 $BH T^2$ 个元素，但融合内核可能不物化整张矩阵；不能把教学 Python 列表内存当成 GPU 显存模型。SDPA 可能根据设备、dtype 和输入约束选不同后端，浮点规约顺序也可能不同；微小误差不等于架构变化。[PyTorch SDPA 实现选择与数值说明](https://docs.pytorch.org/docs/2.14/generated/torch.nn.functional.scaled_dot_product_attention.html)

## 实践任务

交付一份三 token 双头的中间表：Q/K/V 形状、每行合法范围、权重和、合并前后索引及两步采样历史。分别构造未来 token 扰动、非法头数、top-k 并列阈值三个反例。验证性质由常驻 UT 统一管理，本组未运行示例；完整模型训练、内核等价及性能比较仍为已设计。

## 掌握标准

能独立推导缩放方差；能说明 mask 后剩余权重必须重新归一化；能在一个具体索引上证明拆头和还原互逆；能用数值解释训练条件历史与生成采样历史。答案要点是“可见范围、元素对应、条件分布”三项同时成立，只有打印出最终 token 不能证明实现正确。

## 源码与后续阅读

本页源码引用固定到实际读取提交，来源指纹与读取范围由本组 fragment 登记。网络部分可继续阅读[位置编码与RoPE](位置编码与RoPE.md)、[MHA与MQA及GQA](MHA与MQA及GQA.md)；训练标签错位见[预训练目标与数据](预训练目标与数据.md)。本页没有独立复现论文的翻译质量，也没有据教学计算报告任何吞吐收益。

---

[返回模块](../modules/模型网络.md) · [知识点索引](../../docs/知识点索引.md) · [完整教学代码](../../examples/network/transformer.py) · [提出更正](https://github.com/yanbozhang/llm-systems-wiki/issues/new?template=knowledge.yml)

觉得这篇推导有帮助，可以在 [GitHub](https://github.com/yanbozhang/llm-systems-wiki) 点 Star 收藏更新；分享时欢迎链接到具体知识点，便于读者复核公式、代码与来源。
