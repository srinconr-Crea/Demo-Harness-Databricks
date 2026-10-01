"""Start an explicitly selected App and open its verified URL."""
import argparse
import json
import subprocess
import webbrowser
from urllib.parse import urlparse


def start(app_name: str, profile: str, *, run=subprocess.run, open_url=webbrowser.open) -> str:
    if not app_name.strip() or not profile.strip():
        raise ValueError('Indicar App y perfil Databricks')
    command = ['databricks', 'apps', 'start', app_name, '--profile', profile, '-o', 'json']
    try:
        run(command, check=True, capture_output=True, text=True)
        response = run(['databricks', 'apps', 'get', app_name, '--profile', profile, '-o', 'json'],
                       check=True, capture_output=True, text=True)
        app = json.loads(response.stdout)
        url = app.get('url', '')
        parsed = urlparse(url)
        if (app.get('name') != app_name or parsed.scheme != 'https' or not parsed.hostname
                or not parsed.hostname.endswith('.databricksapps.com') or parsed.username or parsed.password):
            raise ValueError('La App no devolvió una URL válida')
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, AttributeError, TypeError):
        raise ValueError('No se pudo iniciar o consultar la App seleccionada') from None
    if not open_url(url):
        raise ValueError('No se pudo abrir el navegador')
    return url


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app_name')
    parser.add_argument('profile')
    args = parser.parse_args()
    try:
        print(start(args.app_name, args.profile))
    except ValueError as error:
        parser.exit(1, f'{error}\n')
