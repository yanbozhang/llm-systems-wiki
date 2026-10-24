"""GUI教学机制：坐标空间、观测有效性和分阶段验证。"""
from math import floor, isfinite


def map_point(point: tuple[float, float], view: tuple[float, float, float, float],
              device: tuple[int, int, int, int]) -> tuple[int, int]:
    """把展示内容矩形内的点映射至对应设备裁剪矩形，排除展示留白。"""
    if len(point) != 2 or len(view) != 4 or len(device) != 4:
        raise ValueError('坐标维度不合法')
    if not all(isfinite(v) for v in (*point, *view, *device)):
        raise ValueError('坐标必须有限')
    x, y = point
    vx, vy, vw, vh = view
    dx, dy, dw, dh = device
    if vw <= 0 or vh <= 0 or dw <= 0 or dh <= 0:
        raise ValueError('矩形尺寸必须为正')
    if any(type(v) is not int or v < 0 for v in device):
        raise ValueError('设备矩形必须为非负整数')
    u, v = (x - vx) / vw, (y - vy) / vh
    if not 0 <= u <= 1 or not 0 <= v <= 1:
        raise ValueError('点落在展示内容矩形外')
    return dx + min(dw - 1, floor(u * dw)), dy + min(dh - 1, floor(v * dh))


def observation_gate(observed: dict, current: dict, now: float, max_age: float) -> str:
    """根据布局指纹、界面忙碌与观测年龄决定是否允许使用旧定位。"""
    if not all(isfinite(v) for v in (now, max_age, observed['captured_at'])):
        raise ValueError('时间必须有限')
    if max_age < 0 or now < observed['captured_at']:
        raise ValueError('时间顺序或有效期不合法')
    if type(current['busy']) is not bool:
        raise ValueError('忙碌标记必须为布尔值')
    if current['busy']:
        return 'wait'
    keys = ('layout_revision', 'width', 'height', 'scroll', 'overlay')
    if any(observed[k] != current[k] for k in keys):
        return 'relocalize'
    if now - observed['captured_at'] >= max_age:
        return 'reobserve'
    return 'act'


def verify_gui_action(point: tuple[float, float], box: tuple[float, float, float, float],
                      dispatched: bool, postcondition: bool | None) -> str:
    """在给定目标框下区分定位、驱动、业务失败与尚未观测。"""
    if len(point) != 2 or len(box) != 4:
        raise ValueError('坐标维度不合法')
    if not all(isfinite(v) for v in (*point, *box)):
        raise ValueError('坐标必须有限')
    if type(dispatched) is not bool or (postcondition is not None and type(postcondition) is not bool):
        raise ValueError('阶段结果类型不合法')
    x, y = point
    left, top, right, bottom = box
    if left >= right or top >= bottom:
        raise ValueError('目标框为空或倒置')
    if not (left <= x < right and top <= y < bottom):
        return 'grounding_error'
    if not dispatched:
        return 'driver_error'
    if postcondition is None:
        return 'unknown'
    return 'succeeded' if postcondition else 'business_mismatch'


def demo() -> dict:
    """返回缩放映射以及点击命中但业务结果未知的示例。"""
    return {'point': map_point((240, 270), (0, 0, 960, 540), (0, 0, 1920, 1080)),
            'verification': verify_gui_action((480, 540), (450, 500, 550, 600), True, None)}


if __name__ == "__main__":
    from pprint import pp

    pp(demo(), sort_dicts=False)
