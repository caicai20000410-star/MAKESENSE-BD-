#!/usr/bin/env python3
"""Local-only password prompt and checked extraction; no network requests."""
import getpass,hashlib,json,os,shutil,stat,sys,tempfile,zipfile
from pathlib import Path,PurePosixPath

BASE=Path(__file__).resolve().parent

def extract(archive,destination,password):
    with zipfile.ZipFile(archive) as z:
        infos=z.infolist()
        if not infos or len(infos)>10000 or sum(i.file_size for i in infos)>200_000_000:
            raise ValueError('安装包大小或文件数量无效')
        seen=set()
        for i in infos:
            p=PurePosixPath(i.filename)
            if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0]!='MAKESENSE-BD' or '\\' in i.filename or ':' in i.filename or stat.S_ISLNK(i.external_attr>>16) or i.filename in seen:
                raise ValueError('安装包路径无效')
            if not i.is_dir() and not i.flag_bits&1:raise ValueError('安装包包含未加密文件')
            seen.add(i.filename)
        for i in infos:
            target=destination.joinpath(*PurePosixPath(i.filename).parts)
            if i.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(i,pwd=password) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
            if i.external_attr>>16&0o111:target.chmod(0o755)

def main():
    archive=BASE/'MAKESENSE-BD.zip'
    expected=json.loads((BASE/'release.json').read_text(encoding='utf8'))['archiveSha256']
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:raise ValueError('安装包校验失败，请重新下载')
    destination=BASE/'MAKESENSE-BD'
    if destination.exists():raise ValueError('MAKESENSE-BD已存在；为保护已有工作台，请移到新的空目录再安装')
    if not sys.stdin.isatty():raise ValueError('请在本机交互终端运行安装器；不会在聊天中索取密码')
    print('解压密码由提供者线下告知，仅用于解压。新工作台默认仅个人可访问。')
    password=getpass.getpass('请输入解压密码（本机输入，不显示）：').encode('utf8')
    with tempfile.TemporaryDirectory(prefix='.workbench-install-',dir=BASE) as tmp:
        extract(archive,Path(tmp),password)
        os.rename(Path(tmp)/'MAKESENSE-BD',destination)
    print('解压完成。将以下安装说明交给Codex：\n'+str(destination/'INSTALL.md'))
    print('安装到使用者账号中的新私人Site；解压器未登录、部署或修改任何站点。')

if __name__=='__main__':
    try:main()
    except (Exception,KeyboardInterrupt) as e:
        print('未完成安装：'+('已取消' if isinstance(e,KeyboardInterrupt) else '密码不正确或压缩包损坏' if isinstance(e,(RuntimeError,zipfile.BadZipFile)) else str(e)),file=sys.stderr);sys.exit(1)
