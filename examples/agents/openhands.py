"""OpenHands事件分支、消息投影与动作观察关联教学；不执行工具或模型。"""
from copy import deepcopy


def conversation_path(events, head_id):
    """沿显式parent_id回溯活动分支；教学中None代表根，不模拟旧日志回退。"""
    rows = list(events)
    index = {e["id"]: e for e in rows}
    if len(index) != len(rows):
        raise ValueError("事件ID必须唯一")
    chain, seen = [], set()
    current = head_id
    while current is not None:
        if current in seen:
            raise ValueError("事件父链有环")
        if current not in index:
            raise KeyError(current)
        seen.add(current)
        event = index[current]
        chain.append(deepcopy(event))
        current = event.get("parent_id")
    return list(reversed(chain))


def project_action_batches(events):
    """仅将连续且同llm_response_id的动作合并成一个assistant工具调用消息。"""
    rows, messages = list(events), []
    i = 0
    while i < len(rows):
        event = rows[i]
        if event["kind"] != "action":
            messages.append(deepcopy(event))
            i += 1
            continue
        batch, j = [event], i + 1
        while j < len(rows) and rows[j]["kind"] == "action" and rows[j]["llm_response_id"] == event["llm_response_id"]:
            batch.append(rows[j])
            j += 1
        if any(e.get("text", "") for e in batch[1:]):
            raise ValueError("同响应批次只有首动作携带共享文本")
        call_ids = [e["tool_call_id"] for e in batch]
        if len(set(call_ids)) != len(call_ids):
            raise ValueError("同批工具调用ID不得重复")
        messages.append({"role": "assistant", "text": event.get("text", ""),
                         "action_ids": [e["id"] for e in batch], "tool_call_ids": call_ids})
        i = j
    return messages


def observation_links(actions, observations):
    """验证普通ObservationEvent三项关联，返回仍待结果的动作；配对不等于业务成功。"""
    rows = list(actions)
    index = {a["id"]: a for a in rows}
    if len(index) != len(rows) or len({a["tool_call_id"] for a in rows}) != len(rows):
        raise ValueError("动作ID和调用ID必须唯一")
    observed = set()
    for obs in observations:
        action_id = obs["action_id"]
        if action_id not in index:
            raise ValueError("观察引用不存在的动作")
        action = index[action_id]
        if obs["tool_call_id"] != action["tool_call_id"] or obs["tool_name"] != action["tool_name"]:
            raise ValueError("观察与动作的工具或调用ID不一致")
        if action_id in observed:
            raise ValueError("教学轨迹每个动作只允许一个最终观察")
        observed.add(action_id)
    return {"observed": sorted(observed), "pending": sorted(index.keys() - observed)}


def demo():
    """合成双分支与两个工具动作，仅返回数据。"""
    events = [{"id": "root", "parent_id": None}, {"id": "a", "parent_id": "root"},
              {"id": "old", "parent_id": "a"}, {"id": "new", "parent_id": "a"}]
    actions = [{"id": "x", "kind": "action", "llm_response_id": "r", "tool_call_id": "cx", "tool_name": "read", "text": "检查文件"},
               {"id": "y", "kind": "action", "llm_response_id": "r", "tool_call_id": "cy", "tool_name": "inspect", "text": ""}]
    return {"branch": conversation_path(events, "new"), "messages": project_action_batches(actions),
            "links": observation_links(actions, [{"action_id": "y", "tool_call_id": "cy", "tool_name": "inspect"}])}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
