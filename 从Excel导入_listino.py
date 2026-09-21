"""
从Excel模板直接导入商品数据
不经过CSV，避免数字被转成科学计数法
"""
import openpyxl, json, re, os, subprocess, sys, io, glob
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 查找本文件夹中的 Excel 文件（排除临时文件）
xlsx_files = glob.glob('*.xlsx')
xlsx_files = [f for f in xlsx_files if not f.startswith('~$')]

if not xlsx_files:
    print('❌ 未找到 Excel 文件！')
    input('按回车键退出...')
    sys.exit(1)

# 优先选择包含"导入"关键字的文件
import_files = [f for f in xlsx_files if '导入' in f]
if import_files:
    EXCEL_FILE = import_files[0]
else:
    EXCEL_FILE = xlsx_files[0]

print(f'📂 已选择: {EXCEL_FILE}')

try:
    # 不用read_only模式，这样可以访问单元格对象和格式信息
    wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
    ws = wb['商品数据']
except Exception as e:
    print(f'❌ 无法打开Excel文件: {e}')
    print('请确保文件没有被Excel打开着！')
    input('按回车键退出...')
    sys.exit(1)

# 读取所有行（不用values_only，以便获取A列单元格对象保留前导零）
goods = []
row_num = 0
for row in ws.iter_rows(min_row=2):  # 跳过标题行
    row_num += 1
    if row_num % 5000 == 0:
        print(f'  已读取 {row_num} 行...')
    
    # A=0(编号), B=1(分类), C=2(名称), D=3(规格), E=4(单价), F=5(单位), G=6(库存)
    # H=7(标签), I=8(图标), J=9(规格选项), K=10(属性), L=11(图片)
    id_cell = row[0]
    id_val = str(id_cell.value).strip() if id_cell.value is not None else ''
    
    # 去掉可能的浮点尾部（如 90.0 → 90）
    if '.' in id_val:
        id_val = id_val.rstrip('0').rstrip('.')
    
    # 跳过空行和模板示例行
    if not id_val or id_val == 'None' or '必填' in id_val or id_val.startswith('例：'):
        continue
    
    # 处理标签
    tags = []
    if row[7].value:
        tags = [t.strip() for t in str(row[7].value).split(',') if t.strip()]
    
    # 处理规格选项
    specs = []
    if row[9].value:
        specs = [s.strip() for s in str(row[9].value).split('|') if s.strip()]
    
    # 处理属性键值对
    attrs = {}
    if row[10].value:
        for pair in str(row[10].value).split('|'):
            if ':' in pair:
                k, v = pair.split(':', 1)
                attrs[k.strip()] = v.strip()
    
    # 处理图片URL
    img = str(row[11].value).strip() if row[11].value else ''
    img = img.replace('/images/', 'images/')
    
    # 处理分类ID
    try:
        cat_id = int(float(row[1].value)) if row[1].value else 0
    except:
        cat_id = 0
    
    # 处理价格
    try:
        price = float(row[4].value) if row[4].value else 0
    except:
        price = 0
    
    # 处理库存
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

# 写入 goods.json
lines = []
for i, g in enumerate(goods):
    comma = ',' if i < len(goods) - 1 else ''
    lines.append('  ' + json.dumps(g, ensure_ascii=False, separators=(',', ':')) + comma)
new_block = '[\n' + '\n'.join(lines) + '\n]'

with open('goods.json', 'w', encoding='utf-8') as f:
    f.write(new_block)

print(f'✅ 商品数据已写入 goods.json')

# =============================================
# 【关键修复】同时更新 listino.html 中的 GOODS_DATA
# =============================================
if os.path.exists('listino.html'):
    print('📝 正在更新 listino.html 中的 GOODS_DATA...')
    with open('listino.html', encoding='utf-8') as f:
        listino_content = f.read()
    
    # 生成新的 GOODS_DATA 块
    listino_lines = ['const GOODS_DATA = [']
    for i, g in enumerate(goods):
        comma = ',' if i < len(goods) - 1 else ''
        listino_lines.append('  ' + json.dumps(g, ensure_ascii=False, separators=(',', ':')) + comma)
    listino_lines.append('];')
    new_goods_block = '\n'.join(listino_lines)
    
    # 替换 listino.html 中的 GOODS_DATA
    if re.search(r'const GOODS_DATA = \[', listino_content):
        updated_content = re.sub(r'const GOODS_DATA = \[.*?\];', new_goods_block, listino_content, flags=re.DOTALL)
        with open('listino.html', 'w', encoding='utf-8') as f:
            f.write(updated_content)
        print('✅ listino.html 已更新')
    else:
        print('⚠️ listino.html 中未找到 GOODS_DATA，将跳过')

# 在 index.html 末尾添加时间戳注释，确保 git 每次都能检测到变化
timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
with open('index.html', encoding='utf-8') as f:
    html_content = f.read()
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_content + f'\n<!-- 更新时间: {timestamp} -->')
print(f'✅ index.html 时间戳已更新')

# Git 操作
now = datetime.now().strftime('%Y-%m-%d %H:%M')
commit_msg = f'更新商品数据 {now}（共{len(goods)}件）'

try:
    subprocess.run(['git', 'add', '-f', 'goods.json', 'index.html', 'listino.html'], check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', commit_msg], check=True, capture_output=True)
    print('📤 推送到GitHub...')
    subprocess.run(['git', 'push', 'origin', 'main'], check=True, capture_output=True)
    print(f'\n🎉 发布成功！约1-2分钟后线上同步。')
    print(f'   线上地址：https://bbqi199.github.io/magazzino/listino.html')
except subprocess.CalledProcessError as e:
    print(f'⚠️ git操作失败（可能没有改动）：{e}')

input('\n按回车键退出...')
