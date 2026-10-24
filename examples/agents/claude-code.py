"""Claude Code公开SDK边界的教学模型；不模拟未公开客户端内部实现。"""


def response_window(events: list[dict]) -> dict:
    """收集至第一条result并包含它；响应完成不代表业务验收通过。"""
    collected = []
    for event in events:
        if not isinstance(event, dict) or 'type' not in event:
            raise ValueError('消息必须具有类型')
        collected.append(dict(event))
        if event['type'] == 'result':
            return {'messages': collected, 'response_complete': True,
                    'business_verified': None}
    return {'messages': collected, 'response_complete': False,
            'business_verified': None}


def hook_reply(request_id: str, callback_id: str, decisions: dict[str, str | None]) -> dict:
    """用注册的模拟回调决策构造控制响应，不执行脚本或真实hook。"""
    if not request_id or not callback_id:
        raise ValueError('控制请求与回调必须有身份')
    if callback_id not in decisions:
        return {'type': 'control_response', 'response': {
            'subtype': 'error', 'request_id': request_id, 'error': 'unknown callback'}}
    decision = decisions[callback_id]
    if decision not in {None, 'allow', 'deny'}:
        raise ValueError('教学模型只支持允许、拒绝和不表态')
    output = {} if decision is None else {'hookSpecificOutput': {
        'hookEventName': 'PreToolUse', 'permissionDecision': decision}}
    return {'type': 'control_response', 'response': {
        'subtype': 'success', 'request_id': request_id, 'response': output}}


def sdk_tool_route(name: str, arguments: dict, registry: dict[str, dict]) -> dict:
    """模拟SDK进程内工具的发现、输入检查和错误结果；工具逻辑仅回显整数。"""
    def error(message: str) -> dict:
        return {'isError': True, 'content': [{'type': 'text', 'text': message}]}
    if name not in registry:
        return error('unknown tool')
    if type(arguments) is not dict or set(arguments) != {'value'}:
        return error('invalid fields')
    if type(arguments['value']) is not int:
        return error('value must be an integer')
    if registry[name].get('fail', False):
        return error('simulated handler failure')
    return {'isError': False, 'content': [{'type': 'text', 'text': str(arguments['value'])}]}


def demo() -> dict:
    """区分控制响应成功、工具执行失败和业务尚未验证。"""
    return {'response': response_window([{'type': 'assistant'}, {'type': 'result'}, {'type': 'assistant'}]),
            'hook': hook_reply('r1', 'h1', {'h1': 'deny'}),
            'tool': sdk_tool_route('echo', {'value': True}, {'echo': {'fail': False}})}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
