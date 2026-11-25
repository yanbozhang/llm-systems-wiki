"""离线教学：持久变化、候选准入与版本推进；不执行自修改。"""
from copy import deepcopy
import math


def persistent_changes(before, after, used_keys):
    missing = object()
    return sorted(key for key in set(used_keys)
                  if key in after and before.get(key, missing) != after[key])


def accept_candidate(gain, retention, min_gain=0.0, min_retention=1.0, verifier_unchanged=True):
    if not all(math.isfinite(value) for value in (gain, retention, min_gain, min_retention)):
        raise ValueError("指标必须为有限数")
    if not 0 <= retention <= 1 or not 0 <= min_retention <= 1 or type(verifier_unchanged) is not bool:
        raise ValueError("保留率与验证器状态无效")
    return verifier_unchanged and gain >= min_gain and retention >= min_retention


def advance_version(current, candidate, accepted):
    if type(accepted) is not bool:
        raise ValueError("必须提供显式准入结果")
    return deepcopy(candidate if accepted else current)


def demo():
    current = {"skill": "v1"}
    candidate = {"skill": "v2"}
    accepted = accept_candidate(0.1, 1.0)
    return {"used_changes": persistent_changes(current, candidate, ["skill"]),
            "version": advance_version(current, candidate, accepted)}


if __name__ == "__main__":
    print(demo())
