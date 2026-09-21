"""
发布更新_listino.py
功能：读取Excel → 写入 goods.json → 更新 listino.html 时间戳 → 强制推送到GitHub
注意：listino.html 通过 fetch('goods.json') 动态加载数据，无需内嵌 GOODS_DATA
用法：双击运行，或在命令行执行 python 发布更新_listino.py
"""
import json, os, glob, subprocess, sys, io, shutil
from datetime import datetime

# ---- 自动定位 git.exe（PATH → WorkBuddy 便携版 → 常见安装位置）----
def find_git():
    p = shutil.which('git')
    if p:
        return p
    cands = [os.path.expandvars(r'%USERPROFILE%\binaries_placeholder'),
             r'C://Program Files\Git\cmd\git.exe',
             r'C://Program Files (x86)\Git\cmd\git.exe',
             os.path.expandvars(r'%LOCALAPPDATA%\Programs\Git\cmd\git.exe')]
    cands[0] = os.path.expandvars(r'%USERPROFILE%') + r'\.workbuddy\binaries\PortableGit\**\cmd\git.exe'
    for pat in cands:
        if '*' in pat:
            h = sorted(glob.glob(pat, recursive=True), reverse=True)
            if h:
                return h[0]
        elif os.path.exists(pat):
            return pat
    return None
GIT = find_git()
if GIT is None:
    print('❌ 找不到 git.exe！')
    sys.exit(1)


# 修复Windows控制台中文输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ===== 第一步：找本文件夹中包含"导入"关键字的Excel文件 =====
xlsx_files = glob.glob('*.xlsx')
xlsx_files = [f for f in xlsx_files if not f.startswith('~$')]

if not xlsx_files:
    print('❌ 未找到 Excel 文件！')
    input('按回车键退出...')
    sys.exit(1)

import_files = [f for f in xlsx_files if '导入' in f]
if import_files:
    EXCEL_FILE = import_files[0]
else:
    EXCEL_FILE = xlsx_files[0]

print(f'📂 已选择: {EXCEL_FILE}')

# ===== 第二步：读取Excel，转换商品数据 =====
try:
    import openpyxl
except ImportError:
    print('❌ 需要 openpyxl 库，请运行: pip install openpyxl')
    input('按回车键退出...')
    sys.exit(1)

try:
    wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
    ws = wb['商品数据']

    goods = []
    row_num = 0
    for row in ws.iter_rows(min_row=2):
        row_num += 1

        id_cell = row[0]
        id_val = str(id_cell.value).strip() if id_cell.value is not None else ''

        if '.' in id_val:
            id_val = id_val.rstrip('0').rstrip('.')

        if not id_val or id_val == 'None' or '必填' in id_val or id_val.startswith('例：'):
            continue

        tags = []
        if row[7].value:
            tags = [t.strip() for t in str(row[7].value).split(',') if t.strip()]

        specs = []
        if row[9].value:
            specs = [s.strip() for s in str(row[9].value).split('|') if s.strip()]

        attrs = {}
        if row[10].value:
            for pair in str(row[10].value).split('|'):
                if ':' in pair:
                    k, v = pair.split(':', 1)
                    attrs[k.strip()] = v.strip()

        img = str(row[11].value).strip() if row[11].value else ''
        img = img.replace('/images/', 'images/')

        try:
            cat_id = int(float(row[1].value)) if row[1].value else 0
        except:
            cat_id = 0

        try:
            price = float(row[4].value) if row[4].value else 0
        except:
            price = 0

        try:
            stock = int(float(row[6].value)) if row[6].value else 999
        except:
            stock = 999

        g = {
            'id':       id_val,
            'catId':    cat_id,
            'emoji':    str(row[8].value).strip() if row[8].value else '📦',
            'name':     str(row[2].value).strip() if row[2].value else '',
            'spec':     str(row[3].value).strip() if row[3].value else '',
            'price':    price,
            'unit':     str(row[5].value).strip() if row[5].value else '',
            'stock':    stock,
            'tag':      tags,
            'attrs':    attrs,
            'specs':    specs,
            'imageUrl': img
        }
        goods.append(g)

    wb.close()
    print(f'✅ 读取完成：共 {len(goods)} 件商品')

except Exception as e:
    print(f'❌ 读取Excel出错：{e}')
    input('按回车键退出...')
    sys.exit(1)

# ===== 第三步：写入 goods.json =====
goods_json_str = json.dumps(goods, ensure_ascii=False, indent=None, separators=(',', ':'))

with open('goods.json', 'w', encoding='utf-8') as f:
    f.write(goods_json_str)

print(f'✅ 商品数据已写入 goods.json（共 {len(goods)} 件）')

# ===== 第四步：更新 listino.html 时间戳（确保 git 检测到变化）=====
LISTINO_FILE = 'listino.html'
timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

with open(LISTINO_FILE, encoding='utf-8') as f:
    content = f.read()

# 去掉旧的时间戳注释，再追加新的
import re
content = re.sub(r'<!-- 更新时间: .*? -->', '', content)
content = content.rstrip('\n') + f'\n<!-- 更新时间: {timestamp} -->'

with open(LISTINO_FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'✅ {LISTINO_FILE} 时间戳已更新')

# ===== 第五步：git add、commit、push（强制发布，无论有无更新）=====
now = datetime.now().strftime('%Y-%m-%d %H:%M')
commit_msg = f'更新商品数据 {now}（共{len(goods)}件）'

try:
    subprocess.run([GIT, 'add', '-f', 'goods.json', LISTINO_FILE], check=True)
    subprocess.run([GIT, 'commit', '--allow-empty', '-m', commit_msg], check=True)
    print('📤 推送到GitHub...')
    subprocess.run([GIT, 'push', 'origin', 'main'], check=True)
    print(f'\n🎉 发布成功！约1-2分钟后线上同步。')
    print(f'   线上地址：https://bbqi199.github.io/magazzino/listino.html')
except subprocess.CalledProcessError as e:
    print(f'❌ git操作失败：{e}')

input('\n按回车键退出...')
