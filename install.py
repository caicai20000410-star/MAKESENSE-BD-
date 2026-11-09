#!/usr/bin/env python3
"""Prompt for the distribution password and extract safely on the user's machine."""
import getpass
import hashlib
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / 'MAKESENSE-BD.zip'
DESTINATION = ROOT / 'MAKESENSE-BD'

def expected_hash():
    for line in (ROOT / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        digest, name = line.split(maxsplit=1)
        if name == ARCHIVE.name and len(digest) == 64:
            return digest
    raise RuntimeError('缺少安装包校验信息，请重新下载完整发布目录。')

def extract_archive(archive, password, destination):
    if destination.exists():
        raise RuntimeError('MAKESENSE-BD 目录已存在。请在新目录安装，以保留现有文件。')
    with tempfile.TemporaryDirectory(prefix='.workbench-extract-', dir=destination.parent) as staging:
        staging_path = Path(staging)
        with zipfile.ZipFile(archive) as source:
            files = [entry for entry in source.infolist() if not entry.is_dir()]
            if not files or any(not entry.flag_bits & 1 for entry in files):
                raise RuntimeError('安装包未完整加密。')
            for entry in source.infolist():
                path = PurePosixPath(entry.filename)
                if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != 'MAKESENSE-BD' or '\\' in entry.filename:
                    raise RuntimeError('安装包路径无效。')
                mode = entry.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise RuntimeError('安装包包含不支持的符号链接。')
            source.extractall(staging_path, pwd=password.encode('utf-8'))
        extracted = staging_path / 'MAKESENSE-BD'
        if not (extracted / 'INSTALL.md').is_file() or not (extracted / 'apps/meta/package.json').is_file():
            raise RuntimeError('安装包内容不完整。')
        if destination.exists():
            raise RuntimeError('安装目录已被创建；已停止以保留原文件。')
        extracted.rename(destination)
    return destination

def main():
    if sys.version_info < (3, 11):
        raise RuntimeError('请先安装 Python 3.11 或更新版本。')
    if not ARCHIVE.is_file():
        raise RuntimeError('缺少 MAKESENSE-BD.zip，请下载完整仓库。')
    if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() != expected_hash():
        raise RuntimeError('安装包校验失败，请重新下载完整仓库。')
    password = getpass.getpass('请输入解压密码：')
    try:
        destination = extract_archive(ARCHIVE, password, DESTINATION)
    finally:
        password = None
    print('解压完成。请让 Codex 读取并执行：')
    print(destination / 'INSTALL.md')

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('安装未完成：' + str(error), file=sys.stderr)
        raise SystemExit(1)
