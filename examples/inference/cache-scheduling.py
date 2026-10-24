"""分页映射、连续批处理与基数树分叉的最小教学模型。"""


def page_address(block_table, position, block_size):
    """把逻辑token位置映射到物理块和块内偏移；调用者保证位置已经有效。"""
    if type(position) is not int or position < 0 or type(block_size) is not int or block_size < 1:
        raise ValueError("位置须非负，块大小须为正整数")
    logical, offset = divmod(position, block_size)
    if logical >= len(block_table):
        raise IndexError("逻辑位置超出块表")
    physical = block_table[logical]
    if type(physical) is not int or physical < 0:
        raise ValueError("物理块ID须为非负整数")
    return {"logical_block": logical, "physical_block": physical, "offset": offset}


def continuous_step(requests, free_blocks, token_budget, block_size):
    """先释放结束请求，再按顺序分配token与独立KV块；不足时跳过，不自动抢占。"""
    if any(type(x) is not int for x in (free_blocks, token_budget, block_size)) or min(free_blocks, token_budget) < 0 or block_size < 1:
        raise ValueError("资源预算须非负，块大小须为正整数")
    rows = [dict(r) for r in requests]
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("请求ID必须唯一")
    for r in rows:
        if any(type(r[k]) is not int or r[k] < 0 for k in ("computed", "target", "blocks")):
            raise ValueError("请求计数须为非负整数")
        if r["computed"] > r["target"] or r["computed"] > r["blocks"] * block_size:
            raise ValueError("已计算位置必须有物理容量且不超目标")
    live = []
    for r in rows:
        if r.get("finished", False):
            free_blocks += r["blocks"]
        else:
            live.append(r)
    for r in live:
        take = min(r["target"] - r["computed"], token_budget)
        needed = max(0, (r["computed"] + take + block_size - 1) // block_size - r["blocks"])
        r["scheduled"] = 0
        if needed <= free_blocks:
            r["computed"] += take
            r["blocks"] += needed
            r["scheduled"] = take
            free_blocks -= needed
            token_budget -= take
    return {"requests": live, "free_blocks": free_blocks, "token_budget": token_budget}


def radix_split(edge_tokens, query_tokens, page_size=1, lock_ref=0):
    """返回压缩边的对齐公共前缀与两条后缀；共享前缀继承原路径锁数。"""
    if type(page_size) is not int or page_size < 1 or type(lock_ref) is not int or lock_ref < 0:
        raise ValueError("页大小须为正整数，锁数须非负")
    edge, query = list(edge_tokens), list(query_tokens)
    if any(type(t) is not int or t < 0 for t in edge + query):
        raise ValueError("token须为非负整数")
    n = 0
    for a, b in zip(edge, query):
        if a != b:
            break
        n += 1
    shared = n // page_size * page_size
    return {"matched_tokens": shared, "prefix": edge[:shared],
            "old_suffix": edge[shared:], "new_suffix": query[shared:],
            "prefix_lock_ref": lock_ref}


def demo():
    """构造释放后即可接纳新请求的一个迭代。"""
    rows = [{"id": "done", "computed": 4, "target": 4, "blocks": 1, "finished": True},
            {"id": "decode", "computed": 4, "target": 5, "blocks": 1},
            {"id": "prefill", "computed": 0, "target": 6, "blocks": 0}]
    return {"address": page_address([7, 1, 3], 9, 4),
            "step": continuous_step(rows, 1, 5, 4),
            "split": radix_split([1, 2, 3, 4], [1, 2, 9], 1, 1)}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
