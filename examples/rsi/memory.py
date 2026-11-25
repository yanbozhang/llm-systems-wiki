"""离线教学：经验适用性、改动预算与实际采用率。"""
import math


def eligible_experience(records, source_versions, task_family):
    return [dict(record) for record in records
            if record.get("status") == "verified"
            and record.get("source_id") in source_versions
            and record.get("source_version") == source_versions[record["source_id"]]
            and task_family in record.get("task_families", [])]


def bounded_edit(changed, total, max_fraction):
    if type(changed) is not int or type(total) is not int or not 0 <= changed <= total or total <= 0:
        raise ValueError("修改数量必须位于正的总量范围内")
    if not math.isfinite(max_fraction) or not 0 <= max_fraction <= 1:
        raise ValueError("修改比例上限必须位于零至一")
    return changed / total <= max_fraction


def adoption_rate(available, used):
    available, used = set(available), set(used)
    if not used <= available:
        raise ValueError("采用记录不能引用不存在的经验")
    return len(used) / len(available) if available else 0.0


def demo():
    records = [{"id": "check-types", "source_id": "run-1", "source_version": "v1",
                "status": "verified", "task_families": ["tables"]}]
    return {"eligible": eligible_experience(records, {"run-1": "v1"}, "tables"),
            "within_budget": bounded_edit(1, 10, 0.2),
            "adoption": adoption_rate(["check-types", "sort"], ["check-types"])}


if __name__ == "__main__":
    print(demo())
