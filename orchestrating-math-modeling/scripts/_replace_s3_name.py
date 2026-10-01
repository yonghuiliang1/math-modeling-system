import os
import re

root = r'c:\Users\28402\Desktop\sxjm\orchestrating-math-modeling'
ref_dir = os.path.join(root, 'references')

md_files = []
for fname in sorted(os.listdir(ref_dir)):
    if fname.endswith('.md'):
        md_files.append(os.path.join(ref_dir, fname))
md_files.append(os.path.join(root, 'SKILL.md'))

total_changes = 0
changed_files = []

for fpath in md_files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content
    
    # 基础替换：步骤3-3运行结果 → S3运行结果
    content = content.replace('步骤3-3运行结果', 'S3运行结果')
    
    # 处理一些常见的章节引用（旧的章节号）
    # S3运行结果第4章关键数值表 → 结果摘要.md
    content = content.replace('S3运行结果第4章关键数值表', '结果摘要.md')
    content = content.replace('S3运行结果（第4章关键数值表', '结果摘要.md（')
    content = content.replace('S3运行结果 第4章关键数值表', '结果摘要.md')
    
    # S3运行结果第5章图表清单 → 图片/ 目录
    content = content.replace('S3运行结果第5章图表清单', '图片/ 目录')
    content = content.replace('S3运行结果（第5章图表清单', '图片/ 目录（')
    
    # S3运行结果第3章数据流说明 → 代码/目录中的数据加载逻辑
    content = content.replace('S3运行结果第3章数据流说明', '代码/数据/ 目录')
    
    # S3运行结果第6章代码注意事项 → 代码注释
    content = content.replace('S3运行结果第6章代码注意事项', '代码注释')
    
    # S3运行结果第8章 → 结果摘要.md
    content = content.replace('S3运行结果第8章', '结果摘要.md')
    
    # S3运行结果（表格/ + 图片/）第4章 → 结果摘要.md
    content = content.replace('S3运行结果（表格/ + 图片/）第4章结果数据', '结果摘要.md')
    content = content.replace('S3运行结果（表格/ + 图片/）第4章关键数值表', '结果摘要.md')
    
    # 旧文件路径
    content = content.replace('S3_步骤产物/步骤3-6_步骤3-3运行结果.md', 'S3_步骤产物/结果摘要.md')
    content = content.replace('`步骤3-3_运行结果_v*.md`', '`表格/` + `图片/`')
    content = content.replace('步骤3-3_运行结果_v*.md', '表格/ + 图片/')
    
    if content != original:
        diff_count = original.count('步骤3-3运行结果') - content.count('步骤3-3运行结果')
        total_changes += abs(diff_count) if diff_count else 1
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        changed_files.append(os.path.basename(fpath))

print(f'修改了 {len(changed_files)} 个文件')
for f in changed_files:
    print(f'  {f}')

# 检查残留
print('\n=== 残留检查 ===')
remaining = 0
for fpath in md_files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    count = content.count('步骤3-3运行结果')
    if count > 0:
        print(f'  {os.path.basename(fpath)}: {count}处')
        remaining += count
if remaining == 0:
    print('  ✅ "步骤3-3运行结果" 全部清零')

# 检查"S3运行结果"出现次数
total = 0
for fpath in md_files:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    total += content.count('S3运行结果')
print(f'\n"S3运行结果" 共出现 {total} 次')
