"""Entry point of the separate, least-privileged Databricks test Job."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


def _sandbox_path(value: str, basename: str) -> Path:
    if re.fullmatch(
        rf"/Volumes/demo_harness_[A-Za-z0-9_]+/[A-Za-z0-9_]+/demo_harness_[A-Za-z0-9_]+/"
        rf"[a-f0-9]{{32}}/[a-f0-9]{{32}}/[0-9]+-[a-f0-9]{{16}}/{re.escape(basename)}",
        value,
    ) is None:
        raise ValueError("Ruta de artefacto sandbox inválida")
    return Path(value)


def run(input_path: str, result_path: str, archive_sha256: str, test_paths: list[str], bundle_target: str = '') -> dict:
    source = _sandbox_path(input_path, "input.zip")
    destination = _sandbox_path(result_path, "result.json")
    if source.parent != destination.parent or re.fullmatch(r"[a-f0-9]{64}", archive_sha256) is None:
        raise ValueError("Los artefactos de prueba no coinciden")
    if (not test_paths and not bundle_target) or any(
        not path or PurePosixPath(path).is_absolute() or "\\" in path
        or any(part in {"", ".", ".."} for part in path.split("/"))
        for path in test_paths
    ):
        raise ValueError("Objetivos de pruebas inválidos")
    if bundle_target and not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', bundle_target):
        raise ValueError('Target bundle inválido')
    archive = source.read_bytes()
    if hashlib.sha256(archive).hexdigest() != archive_sha256:
        raise ValueError("El archivo de pruebas no supera la verificación de integridad")
    with tempfile.TemporaryDirectory(prefix="demo-harness-sandbox-") as directory:
        root = Path(directory)
        with zipfile.ZipFile(source) as bundle:
            entries = bundle.infolist()
            if len(entries) > 2000 or sum(item.file_size for item in entries) > 50_000_000:
                raise ValueError("El paquete de pruebas excede los límites")
            for item in entries:
                path = PurePosixPath(item.filename)
                mode = (item.external_attr >> 16) & 0o170000
                if path.is_absolute() or "\\" in item.filename or any(part in {"", ".", ".."} for part in item.filename.split("/")) or path.parts[0] == ".git" or mode == 0o120000:
                    raise ValueError("El paquete de pruebas contiene una ruta o enlace inválido")
            bundle.extractall(root)
        for path in test_paths:
            if not (root / path).exists():
                raise ValueError("El objetivo de prueba configurado no existe")
        environment = {
            "PATH": os.defpath, "HOME": directory,
            "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        }
        commands = []
        if test_paths:
            commands.append([sys.executable, '-I', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--disable-warnings', '-o', 'pythonpath=.', *test_paths])
        if bundle_target:
            executable = shutil.which('databricks')
            if not executable:
                raise ValueError('CLI Databricks no disponible en el Job dedicado')
            commands.append([executable, 'bundle', 'validate', '--strict', '-t', bundle_target])
        outputs, passed = [], True
        failure_category, failure_code = None, None
        for command in commands:
            try:
                completed = subprocess.run(command, cwd=root, env=environment, capture_output=True,
                                           text=True, timeout=600, check=False)
                outputs.append((completed.stdout + '\n' + completed.stderr)[-6000:])
                passed &= completed.returncode == 0
                if completed.returncode != 0:
                    # Exit 1 is a completed test failure; collection/configuration is inconclusive.
                    category = 'implementation' if command[0] == sys.executable and completed.returncode == 1 and 'failed' in completed.stdout else 'infrastructure_evidence'
                    if failure_category != 'infrastructure_evidence':
                        failure_category = category
                        failure_code = 'pytest_failed' if category == 'implementation' else 'runner_inconclusive'
            except subprocess.TimeoutExpired:
                outputs.append('Las pruebas excedieron 600 segundos')
                passed = False
                failure_category, failure_code = 'infrastructure_evidence', 'sandbox_timeout'
        output = '\n'.join(outputs)[-6000:]
    result = {
        "run_id": source.parent.parent.parent.name,
        "attempt_id": source.parent.parent.name,
        "archive_sha256": archive_sha256,
        "passed": passed,
        "evidence": [output],
        'failure_category': failure_category, 'failure_code': failure_code,
    }
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, destination)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--result-path", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--test-paths", required=True)
    parser.add_argument('--bundle-target', default='')
    args = parser.parse_args()
    run(args.input_path, args.result_path, args.archive_sha256, json.loads(args.test_paths), args.bundle_target)


if __name__ == "__main__":
    main()
