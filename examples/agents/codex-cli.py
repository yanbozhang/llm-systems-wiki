"""Codex CLI组件边界的标准库教学模型；不启动产品或外部进程。"""


def launch_plan(mode: str, root_overrides: list[tuple[str, str]],
                sub_overrides: list[tuple[str, str]], remote: bool = False) -> dict:
    """模拟入口分派和覆盖项顺序；不实现完整配置解析器。"""
    if mode not in {'interactive', 'exec'}:
        raise ValueError('教学模型仅支持interactive和exec')
    if type(remote) is not bool:
        raise ValueError('remote必须是布尔值')
    if mode == 'exec' and remote:
        raise ValueError('该源码版本exec入口拒绝根级remote模式')
    path = ['cli_main', 'run_interactive_tui'] if mode == 'interactive' else [
        'cli_main', 'run_main', 'run_exec_session', 'InProcessAppServerClient', 'turn/start']
    return {'path': path, 'overrides': [*root_overrides, *sub_overrides]}


def route_call(item: dict, registry: dict[str, tuple[str, str]],
               approved: bool = False, strict_review: bool = False) -> dict | None:
    """演示载荷规范化、注册表查找与执行前准入，不调用真实工具。"""
    kinds = {'function_call': 'function', 'custom_tool_call': 'custom'}
    kind = kinds.get(item.get('type'))
    if kind is None:
        return None
    if not item.get('call_id') or not item.get('name'):
        raise ValueError('工具调用缺少身份')
    name = item['name']
    if name not in registry:
        return {'status': 'respond_to_model', 'call_id': item['call_id']}
    expected_kind, requirement = registry[name]
    if kind != expected_kind:
        return {'status': 'fatal_payload', 'call_id': item['call_id']}
    if requirement not in {'skip', 'needs_approval', 'forbidden'}:
        raise ValueError('教学策略不合法')
    if type(approved) is not bool or type(strict_review) is not bool:
        raise ValueError('批准标记必须为布尔值')
    if requirement == 'forbidden':
        status = 'rejected'
    elif (requirement == 'needs_approval' or strict_review) and not approved:
        status = 'await_approval'
    else:
        status = 'ready_for_runtime'
    return {'status': status, 'call_id': item['call_id'], 'kind': kind}


def capture_output(chunks: list[bytes], byte_cap: int, delta_cap: int,
                   terminal: str) -> dict:
    """模拟持续消费、独立输出限制和终态记录；仅保存前缀是教学选择。"""
    if any(type(x) is not int or x < 0 for x in (byte_cap, delta_cap)):
        raise ValueError('上限必须为非负整数')
    if terminal not in {'running', 'exited', 'timed_out', 'cancelled'}:
        raise ValueError('未知终态')
    if any(type(chunk) is not bytes for chunk in chunks):
        raise ValueError('输出块必须是bytes')
    retained = bytearray()
    consumed = emitted = 0
    for chunk in chunks:
        consumed += len(chunk)
        if chunk and emitted < delta_cap:
            emitted += 1
        retained.extend(chunk[:max(0, byte_cap - len(retained))])
    return {'retained': bytes(retained), 'consumed_bytes': consumed,
            'emitted_deltas': emitted, 'truncated': consumed > byte_cap,
            'terminal': terminal}


def demo() -> dict:
    """返回入口计划及输出受限但命令已退出的模拟记录。"""
    return {'launch': launch_plan('exec', [('model', 'example-model')], []),
            'capture': capture_output([b'abc', b'def'], 4, 1, 'exited')}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
