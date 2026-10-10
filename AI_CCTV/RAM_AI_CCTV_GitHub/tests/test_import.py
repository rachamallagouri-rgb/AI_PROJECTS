from pathlib import Path
import py_compile

def test_main_script_compiles():
    script = Path(__file__).resolve().parents[1] / "src" / "ram_ai_cctv.py"
    py_compile.compile(str(script), doraise=True)
