# 🔧 Recriação do Ambiente Virtual (.venv)

**Data:** 2025-10-18
**Python:** 3.13.7
**Tamanho original:** ~500 MB

---

## 📋 Como Recriar o .venv

### Passo 1: Criar ambiente virtual

```powershell
py -3.13 -m venv .venv
```

### Passo 2: Ativar o ambiente

```powershell
.\.venv\Scripts\Activate.ps1
```

### Passo 3: Instalar dependências

```powershell
pip install --upgrade pip
pip install -r requirements-min.txt
```

**Tempo estimado:** 2-5 minutos (depende da internet)

---

## 📦 Dependências Instaladas (requirements-min.txt)

Total: **45 pacotes** (11 diretas + 34 transitivas)

### Diretas (requirements-min.in):
- httpx
- requests
- urllib3
- pypdf
- pdfminer.six
- pymupdf
- pillow
- pytesseract
- python-dotenv
- pyyaml
- supabase>=2.6.0
- ttkbootstrap

### Verificação de Instalação

```powershell
python -c "import pypdf, httpx, supabase, ttkbootstrap; print('✅ OK')"
```

---

## 🧪 Validação Pós-Instalação

```powershell
# Smoke test
python scripts\smoke_runtime.py

# Resultado esperado:
# ✅ imports: PASS (18 módulos)
# ✅ dependencies: PASS (9 pacotes)
# ✅ healthcheck: PASS
# ✅ pdf_support: PASS
```

---

## ⚠️ Notas Importantes

1. **Tesseract OCR** (opcional):
   - Download: https://github.com/UB-Mannheim/tesseract/wiki
   - Adicionar ao PATH do Windows
   - Necessário apenas para OCR de PDFs escaneados

2. **Git Pre-commit Hooks** (opcional):
   - Instalar: `pip install pre-commit`
   - Ativar: `pre-commit install`
   - Hooks: black, ruff, trailing-whitespace, end-of-file-fixer

3. **Ferramentas de Dev** (já arquivadas):
   - `scripts_dev.zip` → Scripts de análise/auditoria
   - `ajuda_completo.zip` → Documentação completa

---

## 🔄 Recriação Rápida (One-liner)

```powershell
py -3.13 -m venv .venv ; .\.venv\Scripts\Activate.ps1 ; pip install --upgrade pip ; pip install -r requirements-min.txt
```

---

**Gerado em:** 2025-10-18 após limpeza profunda V3
**Economia:** ~500 MB (removido temporariamente)
