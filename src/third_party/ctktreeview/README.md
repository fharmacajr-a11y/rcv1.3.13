# CTkTreeview (Vendorizado)

**Origem:** https://github.com/JohnDevlopment/CTkTreeview  
**Commit:** 31858b1fbfa503eedbb9379d01ac7ef8e6a555ea  
**Data de Vendor:** 19 de janeiro de 2026  
**Licença:** MIT (ver LICENSE)

## Motivo da Vendorização (MICROFASE 32)

CTkTreeview foi vendorizado para:
1. **Remover dependência `icecream`** (debug tool não apropriado para produção)
2. **Fixar versão reprodutível** (commit hash específico)
3. **Garantir zero deps externas** (apenas customtkinter + stdlib)

## Mudanças Aplicadas

- **treeview.py:** Removido `from icecream import ic` (linha 8)
- **Removidos arquivos não-runtime:** example.py, __main__.py

## Atualização

Para atualizar esta vendorização:
```bash
# 1. Ver commits novos no upstream
git ls-remote https://github.com/JohnDevlopment/CTkTreeview.git refs/heads/main

# 2. Copiar nova versão
pip install --target=.tmp_vendor "git+https://github.com/JohnDevlopment/CTkTreeview.git@<NEW_COMMIT>"
cp -r .tmp_vendor/CTkTreeview/* src/third_party/ctktreeview/

# 3. Remover icecream novamente (se ainda existir)
# 4. Testar: python -m compileall -q src/third_party/ctktreeview
# 5. Atualizar este README com novo commit hash
```

## Uso

```python
from src.third_party.ctktreeview import CTkTreeview

tree = CTkTreeview(parent, columns=["A", "B"], show="headings")
tree.insert("", "end", values=["foo", "bar"])
```
