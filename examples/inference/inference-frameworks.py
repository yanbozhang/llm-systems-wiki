"""推理性能实验的离线统计示例；不产生请求、不运行模型。"""
import math
import random


def arrival_schedule(count, rate, burstiness=1.0, seed=0):
    """用Gamma间隔构造到达时刻，首请求在0秒；不执行等待或网络请求。"""
    if type(count) is not int or count < 0:
        raise ValueError("请求数须为非负整数")
    if not math.isfinite(rate) or not math.isfinite(burstiness) or min(rate, burstiness) <= 0:
        raise ValueError("到达率和形状须为有限正数")
    rng = random.Random(seed)
    result, time = [], 0.0
    for i in range(count):
        if i:
            time += rng.gammavariate(burstiness, 1.0 / (rate * burstiness))
        result.append(time)
    return result


def qualified_metrics(rows, duration, ttft_limit, tpot_limit):
    """统计所有已发请求；quality_ok为外部判据，失败请求保留在达标率分母。"""
    if any(not math.isfinite(x) for x in (duration, ttft_limit, tpot_limit)) or duration <= 0 or min(ttft_limit, tpot_limit) < 0:
        raise ValueError("时间窗口须正，延迟阈值须非负")
    rows = list(rows)
    completed = good = output_tokens = 0
    for r in rows:
        if not r["success"]:
            continue
        ttft, latency, n = r["ttft"], r["latency"], r["output_tokens"]
        if not math.isfinite(ttft) or not math.isfinite(latency) or not 0 <= ttft <= latency or type(n) is not int or n < 1:
            raise ValueError("成功请求需有效计时及至少一个输出token")
        completed += 1
        output_tokens += n
        # 单token的TPOT阈值在本教学协议中不适用。
        tpot_ok = n == 1 or (latency - ttft) / (n - 1) <= tpot_limit
        good += bool(r["quality_ok"] and ttft <= ttft_limit and tpot_ok)
    return {"offered": len(rows), "completed": completed, "qualified": good,
            "attainment": good / len(rows) if rows else None,
            "completion_rate": completed / len(rows) if rows else None,
            "request_rps": completed / duration, "qualified_rps": good / duration,
            "output_tokens_per_s": output_tokens / duration}


def latency_summary(values, percentile=0.95):
    """返回有限非负样本的均值与最近秩分位数；空集返回None，不伪造零延迟。"""
    if not math.isfinite(percentile) or not 0 < percentile <= 1:
        raise ValueError("分位点须在 (0,1] 内")
    values = list(values)
    if any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("延迟须为有限非负数")
    if not values:
        return {"count": 0, "mean": None, "percentile": None}
    ordered = sorted(values)
    rank = math.ceil(percentile * len(ordered))
    return {"count": len(ordered), "mean": sum(ordered) / len(ordered),
            "percentile": ordered[rank - 1]}


def demo():
    """合成统计，不代表真实引擎结果。"""
    rows = [{"success": True, "quality_ok": True, "ttft": 0.2, "latency": 0.5, "output_tokens": 4},
            {"success": True, "quality_ok": False, "ttft": 0.1, "latency": 0.2, "output_tokens": 2},
            {"success": False}]
    return {"arrivals": arrival_schedule(4, 2.0, seed=7),
            "metrics": qualified_metrics(rows, 2.0, 0.5, 0.11),
            "tail": latency_summary([1, 1, 1, 1, 6])}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
