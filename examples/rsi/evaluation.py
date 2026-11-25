"""离线教学：任务隔离、能力保留与全成本核算。"""
import math


def disjoint_splits(training, validation, testing):
    groups = [set(training), set(validation), set(testing)]
    return not (groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2])


def capability_changes(before, after):
    before, after = set(before), set(after)
    return {"gained": sorted(after - before), "lost": sorted(before - after),
            "retention": len(before & after) / len(before) if before else None}


def net_efficiency(gain, costs):
    values = list(costs)
    if not math.isfinite(gain) or not values or not all(math.isfinite(cost) and cost >= 0 for cost in values):
        raise ValueError("增益必须有限，成本必须非负且不可缺失")
    total = sum(values)
    if not math.isfinite(total) or total <= 0:
        raise ValueError("全部改进成本之和必须为正")
    return gain / total


def demo():
    return {"isolated": disjoint_splits(["family-a"], ["family-b"], ["family-c"]),
            "capabilities": capability_changes(["a", "b"], ["b", "c"]),
            "efficiency": net_efficiency(0.1, [2, 3, 1, 4])}


if __name__ == "__main__":
    print(demo())
