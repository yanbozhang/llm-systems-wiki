"""文本重复候选与评测版本的教学审计，不能证明训练数据无污染。"""
import hashlib
import json
import unicodedata
from datetime import date


def normalized_fingerprint(text):
    """对自然语言文本做NFKC、casefold和空白合并后取指纹；空文本拒绝。"""
    if not isinstance(text, str):
        raise ValueError('文本必须是字符串')
    normalized = ' '.join(unicodedata.normalize('NFKC', text).casefold().split())
    if not normalized:
        raise ValueError('规范化文本不能为空')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def ngram_jaccard(left, right, n=2):
    """按空白分词的n-gram集合Jaccard；任一侧不足n词时返回None。"""
    if not isinstance(left, str) or not isinstance(right, str) or type(n) is not int or n <= 0:
        raise ValueError('需要字符串及正整数n')
    def grams(text):
        words = unicodedata.normalize('NFKC', text).casefold().split()
        return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}
    a, b = grams(left), grams(right)
    if not a or not b:
        return None
    return len(a & b) / len(a | b)


def release_membership(items, as_of):
    """返回快照日有效的ID；released含当日、removed不含当日，ID唯一。"""
    def iso(value):
        if not isinstance(value, str):
            raise ValueError('日期须为YYYY-MM-DD')
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError('日期须为YYYY-MM-DD')
        return parsed
    now = iso(as_of)
    if not isinstance(items, list):
        raise ValueError('条目须为列表')
    seen, active = set(), []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('条目须为对象')
        key = item.get('id')
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError('ID缺失或重复')
        seen.add(key)
        released = iso(item.get('released'))
        removed = iso(item['removed']) if item.get('removed') is not None else None
        if removed is not None and removed < released:
            raise ValueError('移除不能早于发布')
        if released <= now and (removed is None or now < removed):
            active.append(key)
    return sorted(active)


def demo():
    return {'same_normalized_text': normalized_fingerprint('Ａ  B') == normalized_fingerprint('a b'),
            'bigram_similarity': ngram_jaccard('a b c d', 'a b c e'),
            'snapshot': release_membership([
                {'id': 'a', 'released': '2026-01-01', 'removed': '2026-03-01'},
                {'id': 'b', 'released': '2026-02-01'}], '2026-03-01')}


if __name__ == '__main__':
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
