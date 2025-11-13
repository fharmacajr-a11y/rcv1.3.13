import json
from collections import Counter, defaultdict

# Análise Ruff
print("=" * 80)
print("ANÁLISE RUFF.JSON")
print("=" * 80)

with open('ruff.json', encoding='utf-16') as f:
    ruff_data = json.load(f)

print(f"\nTotal issues Ruff: {len(ruff_data)}\n")

# Agrupar por código
ruff_by_code = Counter(d['code'] for d in ruff_data)
print("Issues por código:")
for code, count in ruff_by_code.most_common():
    print(f"  {code}: {count}x")

# Agrupar por arquivo
ruff_by_file = defaultdict(list)
for issue in ruff_data:
    filename = issue['filename'].replace('\\', '/').split('/')[-1]
    filepath = issue['filename'].replace('\\', '/')
    ruff_by_file[filepath].append({
        'code': issue['code'],
        'line': issue['location']['row'],
        'message': issue['message']
    })

print("\n" + "=" * 80)
print("CLASSIFICAÇÃO POR GRUPO")
print("=" * 80)

grupo_a = []  # tests/, scripts/
grupo_b = []  # app seguro
grupo_c = []  # sensível

for filepath, issues in ruff_by_file.items():
    is_test = 'tests/' in filepath or 'test_' in filepath
    is_script = 'scripts/' in filepath
    
    if is_test or is_script:
        grupo_a.append((filepath, issues))
    else:
        # Verificar se é F841 óbvio
        all_f841 = all(i['code'] == 'F841' for i in issues)
        if all_f841 and len(issues) <= 2:
            grupo_b.append((filepath, issues))
        else:
            grupo_c.append((filepath, issues))

print(f"\n📁 GRUPO A (tests/scripts): {len(grupo_a)} arquivos")
for path, issues in grupo_a:
    print(f"  {path.split('/')[-1]}: {len(issues)} issues")
    for iss in issues[:3]:
        print(f"    L{iss['line']}: {iss['code']} - {iss['message'][:60]}")

print(f"\n📁 GRUPO B (app seguro): {len(grupo_b)} arquivos")
for path, issues in grupo_b:
    print(f"  {path.split('/')[-1]}: {len(issues)} issues")
    for iss in issues:
        print(f"    L{iss['line']}: {iss['code']} - {iss['message'][:60]}")

print(f"\n⚠️  GRUPO C (sensível/não tocar): {len(grupo_c)} arquivos")
for path, issues in grupo_c:
    print(f"  {path.split('/')[-1]}: {len(issues)} issues")

# Análise Flake8
print("\n" + "=" * 80)
print("ANÁLISE FLAKE8.TXT")
print("=" * 80)

with open('flake8.txt', encoding='utf-16') as f:
    flake8_lines = [line.strip() for line in f.readlines() if line.strip()]

print(f"\nTotal issues Flake8: {len(flake8_lines)}\n")

# Amostra
print("Primeiras 10 issues:")
for line in flake8_lines[:10]:
    print(f"  {line[:100]}")
