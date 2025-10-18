# Quick Guide - Dependências Mínimas

## 🚀 TL;DR

```powershell
# 1. Testar com deps mínimas (ambiente limpo)
.\scripts\test_minimal_deps.ps1

# 2. Executar o app
cd runtime
python app_gui.py

# 3. Validar funcionalidades (ver checklist abaixo)
```

---

## 📋 Checklist de Validação

```
[ ] Login com credenciais válidas
[ ] Navegação entre telas
[ ] Listagem de clientes
[ ] Upload de arquivo PDF
[ ] Visualização de PDF
[ ] Detecção de CNPJ (OCR)
[ ] Busca/filtros
[ ] Lixeira (soft delete)
[ ] Healthcheck de conectividade
[ ] Logout
```

---

## 📊 O Que Foi Feito?

### Análises Executadas
✅ Árvore de dependências (pipdeptree)  
✅ Dependências não usadas (deptry)  
✅ Código morto (vulture)  
✅ Vulnerabilidades (pip-audit)

### Arquivos Gerados
✅ `requirements-min.in` - 11 deps diretas (antes: 12)  
✅ `requirements-min.txt` - Lock com 47 pacotes  
✅ `ajuda/DEPS-ANALYSIS.md` - Análise completa  
✅ `scripts/test_minimal_deps.ps1` - Script de teste

### Mudanças
✅ Removido: `tzdata` (não usado - DEP002)  
✅ Documentado: `urllib3` (transitivo via requests)  
✅ Sem vulnerabilidades encontradas

---

## 📁 Relatórios Disponíveis

```
ajuda/
├── DEPS_TREE.json         # Árvore completa (JSON)
├── DEPS_TREE.txt          # Árvore legível
├── DEPTRY_REPORT.txt      # Issues de dependências
├── VULTURE_REPORT.txt     # Código morto
├── AUDIT_REPORT.json      # CVEs (original)
├── AUDIT_MIN_REPORT.json  # CVEs (mínimo)
├── DEPS-ANALYSIS.md       # ⭐ Análise completa
└── PROMPT-7-SUMMARY.md    # Resumo executivo
```

---

## 🎯 Resultados

| Métrica | Antes | Depois | Mudança |
|---------|-------|--------|---------|
| Deps diretas | 12 | 11 | -8% |
| CVEs | 0 | 0 | ✅ |
| Código morto | 3 | 3 | ⚠️ Minor |
| Deps transitivas | ~50 | ~47 | -6% |

---

## 🔧 Comandos Úteis

```powershell
# Ver deps instaladas
pip list

# Ver árvore de deps
pipdeptree

# Auditar vulnerabilidades
pip-audit

# Recompilar lock
pip-compile requirements-min.in -o requirements-min.txt

# Atualizar deps
pip-compile --upgrade requirements-min.in
```

---

## � Tesseract OCR (Opcional)

O aplicativo usa Tesseract para detecção de CNPJ em imagens/PDFs.

### Instalação no Windows

1. **Baixar instalador:**
   - [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
   - Versão recomendada: 5.x ou superior

2. **Instalar:**
   - Execute o instalador
   - Anote o caminho de instalação (ex: `C:\Program Files\Tesseract-OCR`)

3. **Configurar PATH (opção A):**
   ```powershell
   # Adicionar ao PATH do sistema
   $env:PATH += ";C:\Program Files\Tesseract-OCR"
   ```

4. **OU configurar no código (opção B):**
   ```python
   import pytesseract
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

### Verificar instalação

```powershell
# No terminal
tesseract --version

# OU via Python
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

### No aplicativo

Menu: **Ajuda → Diagnóstico...** mostra status do Tesseract:
- ✅ **OK** - Tesseract encontrado e funcional
- ⚠️ **Faltando** - Precisa instalar ou configurar PATH

**Referências:**
- [pytesseract PyPI](https://pypi.org/project/pytesseract/)
- [Tesseract GitHub](https://github.com/tesseract-ocr/tesseract)

---

## �📖 Documentação Completa

Leia: `ajuda/DEPS-ANALYSIS.md` para análise detalhada

---

**Gerado em:** 18/10/2025  
**Status:** ✅ Pronto para teste
