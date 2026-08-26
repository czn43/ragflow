# Changelog

## v1.1-fixed

- 修复 Windows / pytest 环境下本地包无法导入的问题。
- 新增 `pytest.ini`。
- 新增 `tests/conftest.py`，测试启动时保证项目根目录进入 `sys.path`。
- `setup_windows.bat` 改为直接调用 `.venv\Scripts\python.exe`，不再依赖激活环境后调用裸 `pytest.exe`。
- 新增 `run_tests.bat`。
- `run_100.bat` 增加虚拟环境、站点配置存在性检查以及错误码处理。
- README 增加 Windows 启动与导入报错排查说明。
- 清理 `.pytest_cache` / `__pycache__` 后重新打包。
## v1.2 Windows BAT compatibility fix

- Converted all `.bat` files to Windows CRLF line endings.
- Removed Chinese/non-ASCII output from `.bat` files to avoid Windows CMD codepage corruption.
- Kept direct `.venv\Scripts\python.exe` invocation for deterministic virtual environment usage.
- Fixes symptoms such as `python` being parsed as `ython`, `echo` as `cho`, and garbled Chinese output.

