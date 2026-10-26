#!/usr/bin/env python3
"""Password-prompted extraction of the encrypted workbench distribution."""
import getpass
import hashlib
import importlib.util
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import venv

ROOT = Path(__file__).resolve().parent
ARCHIVE = 'MAKESENSE-BD.7z'


def ensure_runtime():
    if sys.version_info < (3, 11):
        raise RuntimeError('请先通过 Codex 安装 Python 3.11 或更新版本。')
    if importlib.util.find_spec('py7zr'):
        return
    runtime = ROOT / '.installer-runtime'
    if not runtime.exists():
        venv.EnvBuilder(with_pip=True).create(runtime)
    python = runtime / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    subprocess.run([str(python), '-m', 'pip', 'install', 'py7zr==1.1.4'], check=True)
    raise SystemExit(subprocess.call([str(python), str(Path(__file__).resolve())]))


def expected_hash():
    for line in (ROOT / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        digest, name = line.split(maxsplit=1)
        if name.lstrip('*') == ARCHIVE and len(digest) == 64:
            return digest
    raise RuntimeError('缺少安装包校验信息，请重新下载完整发布目录。')


def obtain_archive():
    path = ROOT / ARCHIVE
    if not path.exists():
        request = urllib.request.Request(
            'https://raw.githubusercontent.com/caicai20000410-star/MAKESENSE-BD-/main/' + ARCHIVE,
            headers={'User-Agent': 'MAKESENSE-BD-installer'},
        )
        temporary = path.with_suffix('.download')
        try:
            with urllib.request.urlopen(request, timeout=120) as source, temporary.open('wb') as output:
                shutil.copyfileobj(source, output)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected_hash():
                raise RuntimeError('下载校验失败，请重新下载同一版本的完整发布目录。')
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash():
        raise RuntimeError('安装包校验失败，请重新下载完整发布目录。')
    return path


def extract_archive(archive, password, destination):
    import py7zr
    destination = Path(destination)
    if destination.exists():
        raise RuntimeError('MAKESENSE-BD 目录已存在。请在新的目录安装，以保留现有数据。')
    with tempfile.TemporaryDirectory(prefix='.workbench-extract-', dir=destination.parent) as staging:
        with py7zr.SevenZipFile(archive, 'r', password=password) as source:
            names = source.getnames()
            for name in names:
                path = PurePosixPath(name)
                if '\\' in name or path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != 'MAKESENSE-BD':
                    raise RuntimeError('安装包路径无效，请重新下载。')
            source.extractall(path=staging)
        extracted = Path(staging) / 'MAKESENSE-BD'
        if not (extracted / 'INSTALL.md').is_file():
            raise RuntimeError('安装包缺少安装说明。')
        if any(p.is_symlink() for p in extracted.rglob('*')):
            raise RuntimeError('安装包包含不支持的符号链接。')
        if destination.exists():
            raise RuntimeError('安装目录已被创建，已停止以保留原文件。')
        extracted.rename(destination)
    return destination


def main():
    ensure_runtime()
    archive = obtain_archive()
    # Ask in the local terminal; never write the password to files or command arguments.
    password = getpass.getpass('请输入解压密码：')
    try:
        destination = extract_archive(archive, password, ROOT / 'MAKESENSE-BD')
    except Exception:
        print('解压未完成：请核对密码及安装包；现有工作台没有被覆盖。', file=sys.stderr)
        return 1
    finally:
        password = None
    print('解压完成。请让 Codex 读取以下文件，继续依赖安装与私人双系统搭建：')
    print(destination / 'INSTALL.md')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
