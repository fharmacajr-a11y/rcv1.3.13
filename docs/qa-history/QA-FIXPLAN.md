# FixPack-01 (Zero-break)

Aplicar estes arquivos no **raiz do projeto**:
- `pyrightconfig.json` (atualizado)
- `typings/ttkbootstrap/__init__.pyi`
- `typings/supabase/__init__.pyi`

Depois rodar:
```
pyright --outputjson > pyright.json
ruff check . --output-format=json > ruff.json
flake8 . --format="%(path)s:%(row)d:%(col)d:%(code)s:%(text)s" > flake8.txt
```
