"""Check the installed wheel from a clean directory with no source checkout on sys.path."""

import json
import os
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path


def main():
    wheel = Path(sys.argv[1]).resolve()
    with zipfile.ZipFile(wheel) as bundle:
        names = bundle.namelist()
        assert not any(name.startswith(("archive/", "tests/")) for name in names)
        assert not any(name.endswith((".env", ".sqlite3")) for name in names)
        assert "jumping_spyder/templates/review.html" in names
        assert "jumping_spyder/templates/logo.png" in names
        assert "jumping_spyder/data/demo.json" in names
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        environment = root / "environment"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / "bin" / "python"
        executable = environment / "bin" / "jumping-spyder"
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
            check=True,
            cwd=root,
            env=env,
        )
        for args in (["--version"], ["demo"], ["evaluate"]):
            subprocess.run([str(executable), *args], check=True, cwd=root, env=env)
        subprocess.run(
            [str(python), "-m", "jumping_spyder", "--help"],
            check=True,
            cwd=root,
            env=env,
            stdout=subprocess.DEVNULL,
        )
        html = (root / "reports/demo/index.html").read_text()
        assert html.count('<article class="card"') == 8
        result = json.loads((root / "reports/evaluation.json").read_text())
        assert result["samples"] == 24
        print("Installed-wheel CLI, demo fixtures, evaluation, and HTML template verified.")


if __name__ == "__main__":
    main()
