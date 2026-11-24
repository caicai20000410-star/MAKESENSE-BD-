#!/bin/sh
cd "$(dirname "$0")" || exit 1
python3 install.py
printf "按回车关闭…"
read answer
