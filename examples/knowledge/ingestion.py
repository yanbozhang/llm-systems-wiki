"""来源版本与派生索引更新的纯函数教学计划；不抓取、不写数据库。"""
import hashlib
import json


def source_fingerprint(source_id, text, parser_version):
    """分别保存原文本、保守规范化文本、解析身份；规范化不代表语义等价。"""
    if not all(isinstance(x, str) for x in (source_id, text, parser_version)) or not source_id or not parser_version:
        raise ValueError("来源与解析器版本须非空，正文须为字符串")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    digest = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
    text_hash = digest(normalized)
    identity = json.dumps([source_id, parser_version, text_hash], ensure_ascii=False, separators=(",", ":"))
    return {"raw_text_sha256": digest(text), "normalized_text_sha256": text_hash,
            "index_identity": digest(identity), "parser_version": parser_version}


def classify_versions(previous, current, unavailable=(), complete_snapshot=False):
    """按稳定ID与指纹比较版本；暂不可读不视作删除，只有完整快照允许推断删除。"""
    old, new, unavailable = dict(previous), dict(current), set(unavailable)
    if unavailable & new.keys():
        raise ValueError("同一来源不能同时成功读取与不可读")
    common = old.keys() & new.keys()
    missing = old.keys() - new.keys() - unavailable
    return {"added": sorted(new.keys() - old.keys()),
            "changed": sorted(k for k in common if old[k] != new[k]),
            "unchanged": sorted(k for k in common if old[k] == new[k]),
            "removed": sorted(missing) if complete_snapshot else [],
            "unobserved": [] if complete_snapshot else sorted(missing),
            "unavailable": sorted(unavailable)}


def reconcile_support(supports, removed_chunks):
    """删除片段后按剩余直接来源规划保留、重建或删除；不自动改写知识正文。"""
    removed = set(removed_chunks)
    result = {"unchanged": [], "rebuild": [], "delete": [], "surviving_supports": {}}
    for item, chunk_ids in supports.items():
        before = set(chunk_ids)
        if not before:
            raise ValueError("教学对象必须至少有一个已验证来源")
        after = before - removed
        result["surviving_supports"][item] = sorted(after)
        status = "unchanged" if before == after else "rebuild" if after else "delete"
        result[status].append(item)
    for name in ("unchanged", "rebuild", "delete"):
        result[name].sort()
    return result


def demo():
    """模拟换行变化、正文更正、临时不可读和共享实体的来源撤回。"""
    return {"fingerprint": source_fingerprint("source-A", "a\r\nb", "parser-v1"),
            "delta": classify_versions({"A": "old", "B": "same"}, {"A": "new"}, {"B"}, True),
            "support": reconcile_support({"entity": {"a", "b"}, "relation": {"a"}, "other": {"c"}}, {"a"})}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
