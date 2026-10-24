"""验证教学CLI与导入边界；数学结果仍由各主题的独立契约测试负责。"""
import ast
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def _load_quietly(case, relative):
    path = Path(__file__).resolve().parents[1] / relative
    spec = importlib.util.spec_from_file_location('entrypoint_probe_' + path.stem.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    stdout, stderr, demo_calls = io.StringIO(), io.StringIO(), []
    previous_profile = sys.getprofile()

    def profile(frame, event, arg):
        if previous_profile is not None:
            previous_profile(frame, event, arg)
        if event == 'call' and frame.f_code.co_filename == str(path) and frame.f_code.co_name == 'demo':
            demo_calls.append(frame.f_code.co_name)

    try:
        sys.setprofile(profile)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            spec.loader.exec_module(module)
    finally:
        sys.setprofile(previous_profile)
    case.assertEqual(stdout.getvalue(), '', '导入不得向stdout写入演示结果')
    case.assertEqual(stderr.getvalue(), '', '导入不得向stderr写入')
    case.assertEqual(demo_calls, [], '导入不得执行demo，即使没有输出')
    return module, path


def assert_quiet_import(case, relative):
    _load_quietly(case, relative)


def assert_cli_matches_demo(case, relative):
    module, path = _load_quietly(case, relative)
    # 此处测试的是CLI与已验证demo的连接关系；不把此值作为数学性质的独立预期。
    expected = module.demo()
    with tempfile.TemporaryDirectory() as directory:
        result = subprocess.run([sys.executable, '-B', str(path)], cwd=directory,
                                env={'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
                                     'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
                                     'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONIOENCODING': 'utf-8'},
                                capture_output=True, text=True, encoding='utf-8', timeout=15)
        case.assertEqual(list(Path(directory).iterdir()), [], '教学CLI不应产生工作目录文件')
    case.assertEqual(result.returncode, 0, result.stderr)
    case.assertEqual(result.stderr, '')
    case.assertTrue(result.stdout.strip(), '直接运行应展示demo结果')
    try:
        actual = json.loads(result.stdout)
    except json.JSONDecodeError:
        actual = ast.literal_eval(result.stdout)
    else:
        # 既有5个Benchmark使用JSON，tuple在线上编码为array。
        expected = json.loads(json.dumps(expected, ensure_ascii=False))
    case.assertEqual(actual, expected, 'CLI完整输出应对应demo返回值')
