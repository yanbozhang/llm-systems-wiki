"""AutoGen轮询团队、状态化终止及静止存档的纯数据教学。"""
from copy import deepcopy


def select_round_robin(participants: list[str], next_index: int) -> tuple[str, int]:
    """选择单个发言者并推进游标，不调用模型或调度真实agent。"""
    if not participants or len(set(participants)) != len(participants):
        raise ValueError('参与者必须非空且不重复')
    if any(type(name) is not str or not name for name in participants):
        raise ValueError('参与者名称必须是非空字符串')
    if type(next_index) is not int or not 0 <= next_index < len(participants):
        raise ValueError('游标超出参与者范围')
    return participants[next_index], (next_index + 1) % len(participants)


def termination_step(state: tuple[int, bool], delta: list[dict], limit: int,
                     marker: str, source: str, mode: str = 'or',
                     include_events: bool = False) -> tuple[tuple[int, bool], bool]:
    """组合消息数和指定来源的文本终止，输入仅为新消息；满足的子条件保持锁存。"""
    count, hit = state
    if type(count) is not int or count < 0 or type(hit) is not bool:
        raise ValueError('终止状态不合法')
    if type(limit) is not int or limit <= 0 or not marker or mode not in {'or', 'and'}:
        raise ValueError('终止配置不合法')
    if type(include_events) is not bool:
        raise ValueError('事件开关须为布尔值')
    combine = any if mode == 'or' else all
    if combine((count >= limit, hit)):
        raise ValueError('已终止条件必须先重置')
    for item in delta:
        if item['kind'] not in {'chat', 'event'} or type(item['text']) is not str:
            raise ValueError('消息格式不合法')
    if count < limit:
        count += sum(include_events or item['kind'] == 'chat' for item in delta)
    if not hit:
        hit = any(item['source'] == source and marker in item['text'] for item in delta)
    return (count, hit), combine((count >= limit, hit))


def snapshot_team(agent_states: dict[str, dict], manager_name: str,
                  manager_state: dict, running: bool) -> dict:
    """只在团队静止时复制参与者和管理器状态；比上游save_state提示更严格。"""
    if type(running) is not bool or running:
        raise ValueError('须在停止后获取教学一致快照')
    if not agent_states or not manager_name or manager_name in agent_states:
        raise ValueError('参与者或管理器身份冲突')
    required = {'message_thread', 'current_turn', 'next_speaker_index'}
    if not required <= manager_state.keys():
        raise ValueError('管理器恢复字段不完整')
    states = deepcopy(agent_states)
    states[manager_name] = deepcopy(manager_state)
    return {'agent_states': states}


def demo() -> dict:
    """展示游标推进和限定来源的文本停止。"""
    delta = [{'kind': 'chat', 'source': 'critic', 'text': 'APPROVE'}]
    return {'speaker': select_round_robin(['writer', 'critic'], 0),
            'termination': termination_step((0, False), delta, 4, 'APPROVE', 'critic')}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
