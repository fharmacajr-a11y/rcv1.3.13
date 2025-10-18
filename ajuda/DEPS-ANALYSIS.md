# Análise de Dependências - RC-Gestor v1.0.33

## 📊 Visão Geral

Análise completa das dependências do projeto para otimização e segurança.

**Data da análise:** 18 de outubro de 2025  
**Branch:** integrate/v1.0.29

---

## 🔍 Ferramentas Utilizadas

| Ferramenta | Versão | Propósito |
|------------|--------|-----------|
| `pip-tools` | latest | Gerenciar locks reproduzíveis |
| `pipdeptree` | latest | Visualizar árvore de dependências |
| `deptry` | 0.23.1 | Detectar deps não usadas/faltantes |
| `vulture` | latest | Encontrar código potencialmente morto |
| `pip-audit` | 2.9.0 | Auditar vulnerabilidades conhecidas |

---

## 📈 Resultados da Análise

### 1. Deptry (Dependências Problemáticas)

**Comando:**
```powershell
deptry . | Tee-Object -FilePath ajuda\DEPTRY_REPORT.txt
```

**Issues Encontrados: 3**

#### DEP002 - Dependência não usada
```
requirements.in: DEP002 'tzdata' defined as a dependency but not used in the codebase
```
**Ação:** ✅ Removido de `requirements-min.in`

#### DEP003 - Dependência transitiva
```
infra\net_session.py:14:1: DEP003 'urllib3' imported but it is a transitive dependency
runtime\infra\net_session.py:14:1: DEP003 'urllib3' imported but it is a transitive dependency
```
**Ação:** ✅ urllib3 será instalado automaticamente via `requests` (transitivo)

**Nota:** urllib3 é importado explicitamente em `infra/net_session.py` para configuração de retry, mas como é transitivo de requests, não precisa estar em requirements.

---

### 2. Vulture (Código Morto)

**Comando:**
```powershell
vulture app_gui.py application gui ui core infra utils adapters shared
```

**Issues Encontrados: 3**

```python
application\keybindings.py:7: unused variable 'ev' (100% confidence)
shared\logging\audit.py:24: unused variable 'action' (100% confidence)
shared\logging\audit.py:25: unused variable 'details' (100% confidence)
```

**Observações:**
- Código morto mínimo (apenas 3 ocorrências)
- Variáveis não usadas em assinaturas de função
- Não afeta o runtime
- Pode ser limpo em refatoração futura

---

### 3. Pip-audit (Vulnerabilidades)

**Comando:**
```powershell
pip-audit -r requirements.txt -f json -o ajuda\AUDIT_REPORT.json
pip-audit -r requirements-min.txt -f json -o ajuda\AUDIT_MIN_REPORT.json
```

**Resultado:** ✅ **No known vulnerabilities found**

Tanto o `requirements.txt` atual quanto o `requirements-min.txt` estão **livres de CVEs conhecidos**.

---

### 4. Árvore de Dependências

**Arquivo:** `ajuda/DEPS_TREE.txt` e `ajuda/DEPS_TREE.json`

**Top-level packages no ambiente atual:**

```plaintext
alembic==1.13.2
bcrypt==5.0.0
black==25.9.0
deptry==0.23.1
fastapi==0.114.2
graphviz==0.21
h2==4.3.0
passlib==1.7.4
pdfminer.six==20250506
pip-audit==2.9.0
pip-tools==8.0.0
pipdeptree==2.24.1
pillow==11.3.0
pypdf==6.1.1
pypdf2==3.0.1
pymupdf==1.26.5
pytesseract==0.3.13
python-dotenv==1.1.1
pyyaml==6.0.3
requests==2.32.5
supabase==2.22.0
ttkbootstrap==1.14.7
tzdata==2025.2
urllib3==2.5.0
vulture==2.15
```

---

## 📦 Dependências Mínimas

### Comparação: requirements.in vs requirements-min.in

| Dependência | requirements.in | requirements-min.in | Motivo |
|-------------|-----------------|---------------------|--------|
| httpx | ✅ | ✅ | Essencial (Supabase) |
| requests | ✅ | ✅ | Essencial (HTTP) |
| pypdf | ✅ | ✅ | PDF processing |
| pdfminer.six | ✅ | ✅ | PDF processing |
| pymupdf | ✅ | ✅ | PDF processing |
| PyPDF2 | ✅ | ✅ | Legado (compatibilidade) |
| pillow | ✅ | ✅ | Image processing |
| pytesseract | ✅ | ✅ | OCR |
| python-dotenv | ✅ | ✅ | Configuração (.env) |
| pyyaml | ✅ | ✅ | Configuração (YAML) |
| supabase | ✅ >=2.6.0 | ✅ >=2.6.0 | Backend |
| ttkbootstrap | ✅ | ✅ | GUI toolkit |
| **tzdata** | ✅ | ❌ | **Não usado (DEP002)** |
| urllib3 | ❌ (implícito) | ❌ (transitivo) | Via requests |

### Redução

- **Dependências diretas:** 12 (antes) → 11 (depois)
- **Redução:** ~8% nas dependências diretas
- **Dependências totais (com transitivas):** Mantém-se similar pois urllib3 já estava sendo instalado

---

## 📋 Arquivos Gerados

### Relatórios de Análise (pasta `ajuda/`)

1. **`DEPS_TREE.json`** - Árvore completa em JSON
2. **`DEPS_TREE.txt`** - Árvore legível em texto
3. **`DEPTRY_REPORT.txt`** - Análise de dependências problemáticas
4. **`VULTURE_REPORT.txt`** - Código potencialmente morto
5. **`AUDIT_REPORT.json`** - Auditoria de vulnerabilidades (original)
6. **`AUDIT_MIN_REPORT.json`** - Auditoria de vulnerabilidades (mínimo)

### Novos Requirements

7. **`requirements-min.in`** - Dependências mínimas (top-level)
8. **`requirements-min.txt`** - Lock mínimo (gerado por pip-compile)

---

## 🧪 Próximos Passos para Validação

### 1. Criar ambiente limpo de teste

```powershell
# Criar venv limpo
py -3.13 -m venv .venv-min

# Ativar
.\.venv-min\Scripts\Activate.ps1

# Instalar dependências mínimas
pip install -r requirements-min.txt
```

### 2. Testar no runtime/

```powershell
cd runtime
python app_gui.py
```

**Checklist de testes:**
- [ ] Login com credenciais válidas
- [ ] Navegação entre telas
- [ ] Listagem de clientes
- [ ] Upload de arquivo PDF
- [ ] Visualização de PDF
- [ ] Detecção de CNPJ (OCR)
- [ ] Busca/filtros
- [ ] Lixeira (soft delete)
- [ ] Healthcheck de conectividade
- [ ] Logout

### 3. Comparação de tamanho

```powershell
# Tamanho do ambiente completo
Get-ChildItem .venv -Recurse | Measure-Object -Property Length -Sum

# Tamanho do ambiente mínimo
Get-ChildItem .venv-min -Recurse | Measure-Object -Property Length -Sum
```

---

## 🎯 Recomendações

### Imediatas

1. ✅ **Usar `requirements-min.txt` para runtime**
   - Validar em ambiente limpo
   - Confirmar que todas as funcionalidades funcionam

2. ⚠️ **Tratar imports transitivos**
   - Documentar que urllib3 é transitivo de requests
   - Adicionar comentário em `infra/net_session.py` explicando

3. 🧹 **Limpeza de código (opcional)**
   - Remover variáveis não usadas identificadas pelo vulture
   - Refatorar assinaturas de função

### Futuras (para build com PyInstaller)

1. **Hooks para imports dinâmicos**
   - Se aparecer ModuleNotFoundError no .exe, adicionar em `hiddenimports` no `.spec`
   - Exemplo: `hiddenimports=['urllib3', 'PIL', ...]`

2. **Minimizar data files**
   - Revisar `datas=[]` no `.spec`
   - Incluir apenas assets/configs necessários

3. **Análise de tamanho do .exe**
   - Usar `pyinstaller --log-level=DEBUG` para ver o que entra
   - Considerar `--exclude-module` para libs grandes não usadas

---

## 📚 Referências

- [Pip-tools](https://pip-tools.readthedocs.io/) - Gerenciamento de dependências
- [Pipdeptree](https://pypi.org/project/pipdeptree/) - Visualização de árvore
- [Deptry](https://deptry.com/) - Análise de dependências
- [Vulture](https://pypi.org/project/vulture/) - Detecção de código morto
- [Pip-audit](https://pypi.org/project/pip-audit/) - Auditoria de segurança
- [PyInstaller Hooks](https://pyinstaller.org/en/stable/hooks.html) - Para build futuro

---

## ✅ Conclusão

**Status:** ✅ Análise concluída com sucesso

**Resultado:**
- ✅ Sem vulnerabilidades conhecidas
- ✅ Dependências mínimas identificadas e documentadas
- ✅ Apenas 3 ocorrências de código potencialmente morto
- ✅ Lock mínimo gerado e pronto para testes

**Próximo passo:** Validar `requirements-min.txt` em ambiente limpo com todos os testes de funcionalidade.
