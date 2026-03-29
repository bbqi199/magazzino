"""
STARCOMET LISTINO 一键发布脚本
功能：自动找最新CSV → 同步商品数据到listino.html → 推送到GitHub
用法：双击运行，或在命令行执行 python 发布更新_listino.py

图片说明：
  - 优先读取 images2/ 目录（新商品专用）
  - 找不到时自动回退到 images/ 目录（复用已有图片）
"""
import csv, json, re, os, glob, subprocess, sys, io
from datetime import datetime

# 修复Windows控制台中文输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ===== 第一步：找最新的CSV文件（排除原订货程序的CSV） =====
# 优先找 listino 专用CSV，再找其他CSV
csv_files = glob.glob('listino*.csv') + glob.glob('LISTINO*.csv') + glob.glob('starcomet*.csv')
if not csv_files:
    # 找所有CSV，排除模板和原订货程序的CSV（商品数据*.csv）
    all_csv = glob.glob('*.csv')
    csv_files = [f for f in all_csv if '模板' not in f and '商品数据' not in f]

if not csv_files:
    print('❌ 找不到CSV文件！')
    print('   请将CSV文件命名为 listino_商品.csv 或其他非"商品数据"开头的文件名')
    input('按回车键退出...')
    sys.exit(1)

# 按修改时间取最新的
latest_csv = max(csv_files, key=os.path.getmtime)
print(f'✅ 找到CSV文件：{latest_csv}')

# ===== 第二步：读取CSV，转换商品数据 =====
goods = []
try:
    with open(latest_csv, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            spec_str = row.get('规格选项', '').strip()
            specs = [s.strip() for s in spec_str.split('|') if s.strip()] if '|' in spec_str else ([spec_str] if spec_str else [])
            img = row.get('商品图片URL', '').strip().replace('/images/', 'images/')
            attrs = {}
            kv = row.get('属性键值对', '').strip()
            if kv:
                for pair in kv.split('|'):
                    if ':' in pair:
                        k, v = pair.split(':', 1)
                        attrs[k.strip()] = v.strip()
            try:
                cat_id = int(row['所属分类ID'].strip())
            except:
                cat_id = 0

            g = {
                'id':       row['商品编号'].strip(),
                'catId':    cat_id,
                'emoji':    row.get('商品图标', '📦').strip() or '📦',
                'name':     row['商品名称'].strip(),
                'spec':     row['规格描述'].strip(),
                'price':    float(row['单价']) if row['单价'].strip() else 0,
                'unit':     row['计量单位'].strip(),
                'stock':    int(row['库存数量']) if row['库存数量'].strip() else 999,
                'tag':      [t.strip() for t in row.get('商品标签', '').split(',') if t.strip()],
                'attrs':    attrs,
                'specs':    specs,
                'imageUrl': img
            }
            goods.append(g)
except Exception as e:
    print(f'❌ 读取CSV出错：{e}')
    input('按回车键退出...')
    sys.exit(1)

print(f'✅ 读取商品数据：共 {len(goods)} 件商品')

# ===== 第三步：写入 listino.html =====
lines = ['const GOODS_DATA = [']
for i, g in enumerate(goods):
    comma = ',' if i < len(goods) - 1 else ''
    lines.append('  ' + json.dumps(g, ensure_ascii=False, separators=(',', ':')) + comma)
lines.append('];')
new_block = '\n'.join(lines)

with open('listino.html', encoding='utf-8') as f:
    content = f.read()

# 先确认 GOODS_DATA 标记存在
if not re.search(r'const GOODS_DATA = \[', content):
    print('❌ 写入失败：listino.html 中未找到 GOODS_DATA！')
    print('   请先运行 make_listino.py 重新生成 listino.html')
    input('按回车键退出...')
    sys.exit(1)

new_content = re.sub(r'const GOODS_DATA = \[.*?\];', new_block, content, flags=re.DOTALL)

if new_content == content:
    print(f'✅ 商品数据无变化（listino.html 已是最新，共 {len(goods)} 件），跳过写入')
else:
    with open('listino.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('✅ 商品数据已写入 listino.html')

# ===== 第四步：git push =====
now = datetime.now().strftime('%Y-%m-%d %H:%M')
commit_msg = f'LISTINO 更新商品数据 {now}（共{len(goods)}件）'

try:
    subprocess.run(['git', 'add', 'listino.html'], check=True)
    # 检查是否有实际变更需要提交
    result = subprocess.run(['git', 'diff', '--cached', '--quiet'], capture_output=True)
    if result.returncode == 0:
        print(f'\n✅ 数据无变化，无需发布（listino.html 已是最新）')
        print(f'   线上地址：https://bbqi199.github.io/magazzino/listino.html')
    else:
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        subprocess.run(['git', 'push'], check=True)
        print(f'\n🎉 发布成功！约1-2分钟后线上同步。')
        print(f'   线上地址：https://bbqi199.github.io/magazzino/listino.html')
except subprocess.CalledProcessError as e:
    print(f'❌ git操作失败：{e}')

input('\n按回车键退出...')
