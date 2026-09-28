import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_octacore_mesh_fusion.py", "-q"],
    check=False,
)
if result.returncode != 0:
    raise SystemExit(result.returncode)
