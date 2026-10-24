"""AppAgent的元素身份、探索文档与部署定位教学；不连接Android设备。"""
from copy import deepcopy


def element_identity(attributes, parent=None, add_index=True):
    """用资源ID或类名尺寸、短描述、父元素与index构造教学UID。"""
    def base_id(attrs):
        x1, y1, x2, y2 = attrs['bounds']
        if x2 <= x1 or y2 <= y1:
            raise ValueError("边界框须有正宽高")
        resource = attrs.get('resource-id', '')
        name = resource.replace(':', '.').replace('/', '_') if resource else f"{attrs['class']}_{x2 - x1}_{y2 - y1}"
        description = attrs.get('content-desc', '')
        if description and len(description) < 20:
            name += '_' + description.replace('/', '_').replace(' ', '').replace(':', '_')
        return name
    uid = base_id(attributes)
    if parent is not None:
        uid = base_id(parent) + '_' + uid
    if add_index:
        uid += '_' + str(attributes['index'])
    return uid


def learn_action_document(store, blocked, uid, action, decision, description=''):
    """模拟自主探索的文档槽位更新及无用元素集合；不覆盖已有非空槽位。"""
    actions = ('tap', 'text', 'v_swipe', 'h_swipe', 'long_press')
    if action not in actions or decision not in ('INEFFECTIVE', 'BACK', 'CONTINUE', 'SUCCESS'):
        raise ValueError("动作或反思结果不受支持")
    result, excluded = deepcopy(store), set(blocked)
    if decision in ('INEFFECTIVE', 'BACK', 'CONTINUE'):
        excluded.add(uid)
    written = False
    if decision != 'INEFFECTIVE':
        if not description:
            raise ValueError("可记录的反思必须带动作效果文档")
        entry = result.setdefault(uid, {name: '' for name in actions})
        if not entry.get(action):
            entry[action] = description
            written = True
    return {'documents': result, 'blocked': sorted(excluded), 'written': written,
            'control': 'BACK' if decision == 'BACK' else 'CONTINUE'}


def deployment_context(elements, documents, selection, width, height, grid_shape=None):
    """检索当前元素文档，并把明确给定的元素或网格选择编译成点击点。"""
    if width <= 0 or height <= 0:
        raise ValueError("屏幕宽高须为正")
    docs = [{'tag': i + 1, 'uid': element['uid'], 'actions': deepcopy(documents[element['uid']])}
            for i, element in enumerate(elements) if element['uid'] in documents]
    tag = selection['area']
    if not isinstance(tag, int):
        raise ValueError("区域标签须为整数")
    if grid_shape is None:
        if not 1 <= tag <= len(elements):
            raise ValueError("当前元素标签越界")
        x1, y1, x2, y2 = elements[tag - 1]['box']
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError("元素框无效")
        point = [(x1 + x2) // 2, (y1 + y2) // 2]
    else:
        rows, cols = grid_shape
        if not isinstance(rows, int) or not isinstance(cols, int) or rows <= 0 or cols <= 0 or not 1 <= tag <= rows * cols:
            raise ValueError("网格和区域标签无效")
        offsets = {'center': (2, 2), 'top-left': (1, 1), 'top': (2, 1), 'top-right': (3, 1),
                   'left': (1, 2), 'right': (3, 2), 'bottom-left': (1, 3), 'bottom': (2, 3), 'bottom-right': (3, 3)}
        subarea = selection.get('subarea', 'center')
        if subarea not in offsets:
            raise ValueError("未知网格子区域")
        cell_w, cell_h = width // cols, height // rows
        if not cell_w or not cell_h:
            raise ValueError("网格单元过小")
        row, col = divmod(tag - 1, cols)
        dx, dy = offsets[subarea]
        point = [col * cell_w + cell_w * dx // 4, row * cell_h + cell_h * dy // 4]
        docs = []  # 该版本网格提示不拼接UI文档
    return {'visible_documentation': docs, 'action': {'kind': 'tap', 'point': point}}


def demo():
    """返回UID、无效/有效探索文档和网格标签的确定性示例。"""
    attrs = {'resource-id': 'demo:id/send', 'class': 'Button', 'bounds': [0, 0, 100, 40], 'index': 0}
    uid = element_identity(attrs)
    learned = learn_action_document({}, [], uid, 'tap', 'SUCCESS', '提交当前表单')
    return {'uid': uid, 'learned': learned,
            'element': deployment_context([{'uid': uid, 'box': [0, 0, 100, 40]}], learned['documents'], {'area': 1}, 300, 240),
            'grid': deployment_context([], {}, {'area': 5, 'subarea': 'top-left'}, 300, 240, (2, 3))}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
