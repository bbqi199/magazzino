"""非交互式发布脚本"""
import csv, json, re, os, glob, subprocess, sys, io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 找最新的CSV文件
csv_files = glob.glob('商品数据*.csv') + glob.glob('*.csv')
csv_files = [f for f in csv_files if '模板' not in f]

if not csv_files:
    print('❌ 找不到CSV文件！')
    sys.exit(1)

latest_csv = max(csv_files, key=os.path.getmtime)
print(f'✅ 找到CSV文件：{latest_csv}')

# 中意列名映射表
COLUMN_MAP = {
    '商品编号': 'Codice Prodotto',
    '所属分类ID': 'ID Categoria',
    '商品图标': 'Icona Prodotto',
    '商品名称': 'Nome Prodotto',
    '规格描述': 'Descrizione Specifiche',
    '单价': 'Prezzo Unitario',
    '计量单位': 'Unità di Misura',
    '库存数量': 'Quantità in Magazzino',
    '商品标签': 'Tag Prodotto',
    '属性键值对': 'Proprietà Chiave-Valore',
    '商品图片URL': 'URL Immagine Prodotto',
    '规格选项': 'Opzioni Specifiche',
}

def get_row_value(row, zh_col, default=''):
    """根据中文列名获取值，优先用中文，fallback到意大利语"""
    if zh_col in row and row[zh_col].strip():
        return row[zh_col]
    it_col = COLUMN_MAP.get(zh_col, '')
    if it_col and it_col in row and row[it_col].strip():
        return row[it_col]
    return default

# 读取CSV
goods = []
try:
    with open(latest_csv, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            spec_str = get_row_value(row, '规格选项', '').strip()
            specs = [s.strip() for s in spec_str.split('|') if s.strip()] if '|' in spec_str else ([spec_str] if spec_str else [])
            img = get_row_value(row, '商品图片URL', '').strip().replace('/images/', 'images/')
            attrs = {}
            kv = get_row_value(row, '属性键值对', '').strip()
            if kv:
                for pair in kv.split('|'):
                    if ':' in pair:
                        k, v = pair.split(':', 1)
                        attrs[k.strip()] = v.strip()
            try:
                cat_id = int(get_row_value(row, '所属分类ID', '0').strip())
            except:
                cat_id = 0

            g = {
                'id':       get_row_value(row, '商品编号').strip(),
                'catId':    cat_id,
                'emoji':    get_row_value(row, '商品图标', '📦').strip() or '📦',
                'name':     get_row_value(row, '商品名称').strip(),
                'spec':     get_row_value(row, '规格描述').strip(),
                'price':    float(get_row_value(row, '单价', '0')) if get_row_value(row, '单价').strip() else 0,
                'unit':     get_row_value(row, '计量单位').strip(),
                'stock':    int(get_row_value(row, '库存数量', '999')) if get_row_value(row, '库存数量').strip() else 999,
                'tag':      [t.strip() for t in get_row_value(row, '商品标签', '').split(',') if t.strip()],
                'attrs':    attrs,
                'specs':    specs,
                'imageUrl': img
            }
            goods.append(g)
except Exception as e:
    print(f'❌ 读取CSV出错：{e}')
    sys.exit(1)

print(f'✅ 读取商品数据：共 {len(goods)} 件商品')

# 写入 goods.json
# index.html 通过 fetch('goods.json') 动态加载商品数据，
# 因此数据应写入 goods.json，而非直接嵌入 HTML。
goods_json_str = json.dumps(goods, ensure_ascii=False, indent=None, separators=(',', ':'))
with open('goods.json', 'w', encoding='utf-8') as f:
    f.write(goods_json_str)
print(f'✅ 商品数据已写入 goods.json（共 {len(goods)} 件）')

# 在 index.html 末尾添加时间戳注释，确保 git 每次都能检测到变化并推送
timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
with open('index.html', encoding='utf-8') as f:
    content = f.read()
new_content = content + f'\n<!-- 更新时间: {timestamp} -->'
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(new_content)
print('✅ index.html 时间戳已更新')

# Git操作
now = datetime.now().strftime('%Y-%m-%d %H:%M')
commit_msg = f'更新商品数据 {now}（共{len(goods)}件）'

try:
    subprocess.run(['git', 'add', '-f', 'goods.json', 'index.html'], check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', commit_msg], check=True, capture_output=True)
    print('📤 推送到GitHub...')
    subprocess.run(['git', 'push', 'origin', 'main'], check=True, capture_output=True)
    print(f'\n🎉 发布成功！约1-2分钟后线上同步。')
    print(f'   线上地址：https://bbqi199.github.io/magazzino/')
except subprocess.CalledProcessError as e:
    print(f'❌ git操作失败：{e}')
    sys.exit(1)
