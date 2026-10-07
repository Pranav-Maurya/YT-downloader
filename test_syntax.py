import py_compile
import sys

try:
    py_compile.compile('main.py', doraise=True)
    print("Syntax OK")
except py_compile.PyCompileError as e:
    print(f"Syntax error: {e}")
    sys.exit(1)
