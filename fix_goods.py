import csv, json, re

goods = []
with open('商品数据_2026-3-27.csv', encoding='utf-8-sig') as f:
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
            'id': row['商品编号'].strip(),
            'catId': cat_id,
            'emoji': row.get('商品图标', '📦').strip() or '📦',
            'name': row['商品名称'].strip(),
            'spec': row['规格描述'].strip(),
            'price': float(row['单价']) if row['单价'].strip() else 0,
            'unit': row['计量单位'].strip(),
            'stock': int(row['库存数量']) if row['库存数量'].strip() else 999,
            'tag': [t.strip() for t in row.get('商品标签', '').split(',') if t.strip()],
            'attrs': attrs,
            'specs': specs,
            'imageUrl': img
        }
        goods.append(g)

lines = ['const GOODS_DATA = [']
for i, g in enumerate(goods):
    comma = ',' if i < len(goods) - 1 else ''
    lines.append('  ' + json.dumps(g, ensure_ascii=False, separators=(',', ':')) + comma)
lines.append('];')
new_block = '\n'.join(lines)

with open('index.html', encoding='utf-8') as f:
    content = f.read()

new_content = re.sub(r'const GOODS_DATA = \[.*?\];', new_block, content, flags=re.DOTALL)

if new_content == content:
    print('ERROR: 未找到GOODS_DATA')
else:
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    check = '"catId":0' in new_content
    print('OK - catId字段正确:', check, '- 商品数量:', len(goods))
