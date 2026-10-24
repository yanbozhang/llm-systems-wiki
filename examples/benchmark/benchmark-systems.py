"""推理性能基准的统计和证据分层教学；不运行LoadGen或提交评测结果。"""
import math


def loadgen_latency_profile(samples, percentile=0.99):
    """模拟所读LoadGen的零基floor(n*p)分位数及整纳秒TPOT，要求输出至少2token。"""
    rows = list(samples)
    if not math.isfinite(percentile) or not 0 <= percentile < 1:
        raise ValueError("该分位数定义要求0 <= p < 1")
    ttft, tpot = [], []
    for row in rows:
        first, total, tokens = row["ttft_ns"], row["latency_ns"], row["tokens"]
        if any(type(v) is not int for v in (first, total, tokens)) or not 0 <= first <= total or tokens <= 1:
            raise ValueError("要求有序整纳秒延迟及至少2个输出token")
        ttft.append(first)
        tpot.append((total - first) // (tokens - 1))
    def summarize(values):
        if not values:
            return {"mean_ns": None, "percentile_ns": None}
        ordered = sorted(values)
        return {"mean_ns": sum(values) // len(values),
                "percentile_ns": ordered[int(len(values) * percentile)]}
    return {"count": len(rows), "ttft": summarize(ttft), "tpot": summarize(tpot),
            "tpot_per_request_ns": tpot}


def slo_overlap(ttft_ok, tpot_ok, duration_s):
    """逐请求计算两个延迟条件的联合达标与Fréchet界；未完成请求应显式标False。"""
    first, later = dict(ttft_ok), dict(tpot_ok)
    if first.keys() != later.keys() or any(type(v) is not bool for v in list(first.values()) + list(later.values())):
        raise ValueError("两条件须覆盖同一请求ID并使用布尔标签")
    if not math.isfinite(duration_s) or duration_s <= 0:
        raise ValueError("观测窗口秒数须为有限正数")
    n = len(first)
    a, b = sum(first.values()), sum(later.values())
    both = sum(first[rid] and later[rid] for rid in first)
    return {"offered": n, "both_pass": both,
            "ttft_rate": a / n if n else None, "tpot_rate": b / n if n else None,
            "joint_rate": both / n if n else None,
            "lower_bound": max(0, a + b - n) / n if n else None,
            "upper_bound": min(a, b) / n if n else None,
            "latency_goodput_rps": both / duration_s}


def submission_layers(loadgen_checks, submission_checks):
    """汇总有限教学检查项的三态结果；缺失不算通过，结果不构成MLPerf认证。"""
    required_loadgen = ("min_duration", "min_queries", "min_samples", "latency", "early_stopping")
    required_submission = ("accuracy", "seed_and_settings", "no_log_errors", "compliance", "system_and_measurements", "division_and_model")
    def summarize(provided, required):
        if any(v is not None and type(v) is not bool for v in provided.values()):
            raise ValueError("检查值仅允许True、False或None")
        failed = [k for k in required if provided.get(k) is False]
        missing = [k for k in required if provided.get(k) is None]
        return {"status": "failed" if failed else "incomplete" if missing else "passed",
                "failed": failed, "missing": missing}
    performance = summarize(loadgen_checks, required_loadgen)
    submission = summarize(submission_checks, required_submission)
    return {"loadgen_layer": performance, "submission_layer": submission,
            "all_recorded_checks_passed": performance["status"] == submission["status"] == "passed"}


def demo():
    """使用整数纳秒、两个不重叠失败集合以及缺准确率证据的算例。"""
    samples = [{"ttft_ns": x, "latency_ns": x + 30, "tokens": 4} for x in (10, 20, 30, 100)]
    return {"latency": loadgen_latency_profile(samples, 0.5),
            "joint": slo_overlap({"a": True, "b": True, "c": False}, {"a": True, "b": False, "c": True}, 1),
            "layers": submission_layers(dict.fromkeys(("min_duration", "min_queries", "min_samples", "latency", "early_stopping"), True), {})}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
