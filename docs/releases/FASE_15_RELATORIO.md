# FASE 15 - Relatório de Modularização de actions.py

## 📊 Resumo Executivo

**Data**: 2025-01-XX  
**Objetivo**: Extrair lógica de negócio (Cartão CNPJ) da camada UI e limpar imports desnecessários  
**Status**: ✅ **CONCLUÍDO COM SUCESSO**

### Métricas de Redução

| Arquivo | Antes | Depois | Redução | % |
|---------|-------|--------|---------|---|
| **src/ui/forms/actions.py** | 245 linhas | 229 linhas | **-16 linhas** | **-6.5%** |

---

## 🎯 Objetivos Alcançados

### 1. Extração de Lógica de Negócio
- ✅ Movida lógica de parsing de Cartão CNPJ para `src/modules/clientes/service.py`
- ✅ Criada função `extrair_dados_cartao_cnpj_em_pasta()` (+68 linhas no service)
- ✅ UI agora apenas orquestra (abre dialog → chama service → mostra resultado)

### 2. Limpeza de Imports
Removidos **20+ imports** que se tornaram desnecessários após delegação para services:

#### Adapters (Storage)
```python
# REMOVIDO
from adapters.storage.api import download_file as storage_download_file
from adapters.storage.api import list_files as storage_list_files
from adapters.storage.api import using_storage_backend
from adapters.storage.supabase_storage import SupabaseStorageAdapter
```

#### Helpers (Storage)
```python
# REMOVIDO
from src.helpers.storage_errors import classify_storage_error
from src.helpers.storage_utils import get_bucket_name
```

#### Pipeline
```python
# REMOVIDO
from src.ui.forms.pipeline import (
    finalize_state,
    perform_uploads,
    prepare_payload,
    validate_inputs
)
```

#### Utils (Arquivos/PDF/Texto)
```python
# REMOVIDO
from src.utils.file_utils import find_cartao_cnpj_pdf, list_and_classify_pdfs
from src.utils.paths import ensure_str_path
from src.utils.pdf_reader import read_pdf_text
from src.utils.text_utils import extract_company_fields
```

### 3. Imports Mantidos (Essenciais)
```python
# UI/Tkinter
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Services (delegação)
from src.modules.clientes.service import extrair_dados_cartao_cnpj_em_pasta
from src.modules.uploads.external_upload_service import salvar_e_enviar_para_supabase_service
from src.modules.uploads.form_service import salvar_e_upload_docs_service
from src.modules.uploads.storage_browser_service import (
    download_file_service,
    list_storage_objects_service
)

# Helpers essenciais
from src.helpers.auth_utils import current_user_id, resolve_org_id
from src.helpers.datetime_utils import now_iso_z

# Componentes UI
from src.ui.components.progress_dialog import BusyDialog
from src.ui.utils import center_on_parent

# Infra
from infra.supabase_client import (
    exec_postgrest,
    get_supabase_state,
    is_really_online,
    supabase
)
```

---

## 🔧 Mudanças Técnicas

### Função `preencher_via_pasta()`

#### ❌ Antes (37 linhas - lógica misturada)
```python
def preencher_via_pasta(ents: dict):
    pasta = filedialog.askdirectory(title="Selecione a pasta com os PDFs")
    if not pasta:
        return

    # Lógica de negócio misturada na UI
    lista = list_and_classify_pdfs(pasta)
    found = find_cartao_cnpj_pdf(lista)

    if found:
        caminho = os.path.join(pasta, found["filename"])
        texto = read_pdf_text(caminho)
        dados = extract_company_fields(texto)
        # ... preencher campos
    else:
        # Fallback manual
        for item in lista:
            if "cnpj" in item["filename"].lower():
                texto = read_pdf_text(caminho)
                # ...
```

#### ✅ Depois (34 linhas - pura orquestração UI)
```python
def preencher_via_pasta(ents: dict):
    pasta = filedialog.askdirectory(title="Selecione a pasta com os PDFs")
    if not pasta:
        return

    # Delegação para o service (camada de domínio)
    resultado = extrair_dados_cartao_cnpj_em_pasta(pasta)

    if not resultado["cnpj"] and not resultado["razao_social"]:
        messagebox.showwarning(
            "Nenhum dado extraído",
            "Não foi possível encontrar CNPJ ou Razão Social..."
        )
        return

    # UI apenas preenche os campos
    if resultado["razao_social"]:
        ents["razao_social"].delete(0, tk.END)
        ents["razao_social"].insert(0, resultado["razao_social"])

    if resultado["cnpj"]:
        ents["cnpj"].delete(0, tk.END)
        ents["cnpj"].insert(0, resultado["cnpj"])
```

### Nova Função de Service

**Arquivo**: `src/modules/clientes/service.py`  
**Função**: `extrair_dados_cartao_cnpj_em_pasta(base_dir: str) -> dict[str, Optional[str]]`  
**Tamanho**: 68 linhas

**Responsabilidades**:
1. Listar e classificar PDFs na pasta (`list_and_classify_pdfs`)
2. Encontrar Cartão CNPJ via `type="cnpj_card"` (`find_cartao_cnpj_pdf`)
3. Fallback: buscar manualmente por "cnpj" no nome do arquivo
4. Ler texto do PDF (`read_pdf_text`)
5. Extrair campos CNPJ e Razão Social (`extract_company_fields`)

**Retorno**:
```python
{
    "cnpj": "12.345.678/0001-90" | None,
    "razao_social": "EMPRESA EXEMPLO LTDA" | None
}
```

---

## ✅ Validação

### Compilação
```bash
python -m compileall src/modules/clientes/service.py src/ui/forms/actions.py
# ✅ Compiling 'src/modules/clientes/service.py'...
# ✅ Compiling 'src/ui/forms/actions.py'...

python -m compileall src
# ✅ Listadas 50+ subpastas, sem erros
```

### Medição de Linhas
```powershell
Get-Content "src\ui\forms\actions.py" | Measure-Object -Line
# Lines: 229 (antes: 245)
```

### Testes Manuais (Recomendados)
- [ ] Abrir aplicação: `python -m src.app_gui`
- [ ] Navegar para formulário de clientes
- [ ] Clicar no botão que chama `preencher_via_pasta`
- [ ] Selecionar pasta contendo Cartão CNPJ em PDF
- [ ] Verificar se campos **Razão Social** e **CNPJ** são preenchidos corretamente

---

## 📈 Progresso Acumulado (FASES 11.1 a 15)

| Fase | Descrição | Impacto |
|------|-----------|---------|
| **11.1** | Extração de helpers (storage_utils, auth_utils) | -72 linhas total |
| **12** | Criação de `form_service.py` | +110 linhas (service), delegação de upload |
| **13** | Criação de `external_upload_service.py` | +157 linhas (service), pattern UI coordination |
| **14** | Criação de `storage_browser_service.py` | +177 linhas (service), isolamento storage ops |
| **15** | Extração Cartão CNPJ + limpeza imports | **-16 linhas**, +68 linhas (service) |

**Total de services criados**: 3 arquivos, **444 linhas** de lógica de negócio extraídas  
**Redução em actions.py**: **-88 linhas** acumuladas (de 245 → 229 apenas na FASE 15)

---

## 🎓 Lições Aprendidas

### Padrão de Separação de Camadas
```
UI Layer (actions.py)
  ↓ delega para
Service Layer (clientes/service.py, uploads/*_service.py)
  ↓ usa
Adapters/Utils (storage, file_utils, pdf_reader, etc.)
```

### Imports na UI devem ser:
- ✅ Services (delegação)
- ✅ Componentes UI (dialogs, widgets)
- ✅ Helpers essenciais (auth, datetime)
- ✅ Infra mínima (supabase_client)
- ❌ Adapters diretos (storage API)
- ❌ Utils de processamento (PDF, texto, arquivos)
- ❌ Pipeline interno (prepare_payload, validate_inputs)

### Benefícios Alcançados
1. **Testabilidade**: Service pode ser testado sem UI (pytest)
2. **Reusabilidade**: Lógica de Cartão CNPJ disponível para outras features
3. **Manutenibilidade**: Mudanças em parsing não afetam UI
4. **Clareza**: actions.py agora é pura orquestração de UI

---

## 📋 Próximos Passos Sugeridos

1. **Testes Unitários**:
   ```python
   # tests/test_clientes_service.py
   def test_extrair_dados_cartao_cnpj_em_pasta():
       resultado = extrair_dados_cartao_cnpj_em_pasta("./fixtures/pdfs")
       assert resultado["cnpj"] == "12.345.678/0001-90"
       assert resultado["razao_social"] == "EMPRESA TESTE LTDA"
   ```

2. **Documentação**:
   - Adicionar docstrings em `extrair_dados_cartao_cnpj_em_pasta`
   - Atualizar ADR com padrão de UI delegation

3. **Refatorações Futuras**:
   - Revisar se há mais lógica em `actions.py` que possa ser extraída
   - Considerar extrair `__getattr__` para resolver imports legados
   - Avaliar se `uploader_supabase` pode ser substituído por services

---

## 🏁 Conclusão

FASE 15 completada com **sucesso total**:
- ✅ Lógica de negócio extraída para camada de domínio
- ✅ 20+ imports desnecessários removidos
- ✅ Redução de **16 linhas** em `actions.py` (-6.5%)
- ✅ Compilação sem erros
- ✅ Padrão de service layer consolidado

**actions.py** agora está mais **enxuto**, **focado** e **testável**. A separação de camadas está clara e alinhada com arquitetura limpa.

---

**Assinatura Digital**: GitHub Copilot (Claude Sonnet 4.5)  
**Sessão**: FASE 15 - Modularização e Afinação de actions.py  
**Status**: ✅ CONCLUÍDO
