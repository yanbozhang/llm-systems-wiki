"""工具协议、业务参数和Skill加载的责任边界。"""


def validate_query(arguments: dict, allowed_cities: set[str]) -> tuple[bool, str]:
    """验证简化查询结构和业务词表；不实现完整JSON Schema。"""
    if type(arguments) is not dict or set(arguments) != {'city', 'days'}:
        return False, 'schema_fields'
    if type(arguments['city']) is not str or type(arguments['days']) is not int:
        return False, 'schema_types'
    if not 1 <= arguments['days'] <= 7:
        return False, 'schema_range'
    if arguments['city'] not in allowed_cities:
        return False, 'semantic_city'
    return True, 'accepted'


def classify_response(response: dict | None, expected_id: str) -> str:
    """区分超时、协议错误、工具错误、结果畸形与业务待验证。"""
    if response is None:
        return 'unknown'
    if response.get('jsonrpc') != '2.0' or response.get('id') != expected_id:
        return 'protocol_mismatch'
    if ('error' in response) == ('result' in response):
        return 'malformed'
    if 'error' in response:
        error = response['error']
        if not isinstance(error, dict) or type(error.get('code')) is not int:
            return 'malformed'
        return 'protocol_error'
    result = response['result']
    if not isinstance(result, dict) or type(result.get('isError', False)) is not bool:
        return 'malformed'
    if result.get('isError', False):
        return 'tool_error'
    data = result.get('structuredContent')
    if not isinstance(data, dict) or type(data.get('count')) is not int or data['count'] < 0:
        return 'output_schema_error'
    return 'verify_business'


def skill_load_plan(catalog: dict[str, int], bodies: dict[str, int],
                    active: set[str], resources: dict[str, tuple[str, int]],
                    requested: set[str], budget: int) -> dict:
    """规划元数据、激活正文和所需资源的token成本，不读取或运行文件。"""
    if type(budget) is not int or budget < 0:
        raise ValueError('预算须为非负整数')
    costs = list(catalog.values()) + list(bodies.values()) + [c for _, c in resources.values()]
    if any(type(c) is not int or c < 0 for c in costs):
        raise ValueError('成本必须是非负整数')
    if not active <= catalog.keys() or not active <= bodies.keys():
        raise ValueError('激活项缺少目录或正文')
    if not requested <= resources.keys():
        raise ValueError('请求了不存在的资源')
    if any(resources[r][0] not in active for r in requested):
        raise ValueError('资源所属Skill尚未激活')
    cost = sum(catalog.values()) + sum(bodies[s] for s in active)
    cost += sum(resources[r][1] for r in requested)
    return {'accepted': cost <= budget, 'tokens': cost,
            'bodies': sorted(active), 'resources': sorted(requested)}


def demo() -> dict:
    """给出类型陷阱、待验收结果与分层加载计划。"""
    return {'query': validate_query({'city': '北京', 'days': True}, {'北京'}),
            'response': classify_response({'jsonrpc': '2.0', 'id': 'r1',
                'result': {'structuredContent': {'count': 2}}}, 'r1'),
            'loading': skill_load_plan({'a': 10, 'b': 10}, {'a': 50, 'b': 80},
                                      {'a'}, {'ref': ('a', 30)}, {'ref'}, 100)}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
