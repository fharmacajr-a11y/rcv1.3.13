# FASE 22 - Relatório de Implementação de Testes para Upload Services

**Data**: 19 de novembro de 2025  
**Objetivo**: Implementar testes unitários para os services de upload criados anteriormente (storage_browser, external_upload, form)

---

## 1. Resumo Executivo

A FASE 22 expandiu a **cobertura de testes unitários** para os services de upload, implementando **21 novos testes** (12 storage_browser + 9 external_upload). Os 8 testes de `form_service` permaneceram `@pytest.mark.skip` devido ao **import circular não resolvido**, que será atacado na FASE 23.

### Métricas Finais
- **Total de Testes**: 54 (25 implementados na FASE 21 + 21 novos na FASE 22 + 8 skipped)
- **Testes Executados**: 46 passed
- **Testes Skipped**: 8 (form_service - bloqueados por import circular)
- **Taxa de Sucesso**: 100% (46/46 passed, 0 failed)
- **Tempo de Execução**: 2.08s

### Comparação com FASE 21
| Métrica | FASE 21 | FASE 22 | Δ |
|---------|---------|---------|---|
| Testes Implementados | 25 | 46 | +21 (+84%) |
| Testes Skipped | 29 | 8 | -21 (-72%) |
| Tempo de Execução | 2.05s | 2.08s | +0.03s |
| Arquivos Testados | 2 | 4 | +2 |

---

## 2. Testes Implementados

### 2.1 `tests/test_storage_browser_service.py` (12 testes implementados)

#### **TestListStorageObjectsService** (7 testes)

| # | Teste | Status | Objetivo |
|---|-------|--------|----------|
| 1 | `test_normalizes_bucket_name` | ✅ PASS | Verifica normalização de `bucket_name` (usa padrão via `get_bucket_name`) |
| 2 | `test_lists_files_via_adapter` | ✅ PASS | Mock de `storage_list_files` com 2 arquivos + 1 pasta |
| 3 | `test_processes_response_and_builds_objects_list` | ✅ PASS | Verifica que lista de objetos é montada corretamente |
| 4 | `test_classifies_folders_vs_files` | ✅ PASS | Valida `is_folder=True` (metadata=None) vs `is_folder=False` (metadata presente) |
| 5 | `test_handles_bucket_not_found_error` | ✅ PASS | Exceção "Bucket not found" → `error_type="bucket_not_found"` |
| 6 | `test_handles_generic_errors` | ✅ PASS | Exceção genérica → `error_type="generic"` |
| 7 | `test_returns_correct_result_structure` | ✅ PASS | Verifica estrutura do dict: `ok`, `objects`, `errors`, `message`, `error_type` |

**Padrão de Mock**:
```python
@patch("src.modules.uploads.storage_browser_service.storage_list_files")
@patch("src.modules.uploads.storage_browser_service.using_storage_backend")
@patch("src.modules.uploads.storage_browser_service.get_bucket_name")
def test_lists_files_via_adapter(self, mock_get_bucket, mock_using, mock_list_files):
    mock_get_bucket.return_value = "test-bucket"

    # Context manager mock
    mock_cm = MagicMock()
    mock_using.return_value = mock_cm
    mock_cm.__enter__.return_value = None
    mock_cm.__exit__.return_value = None

    # Mock de retorno com 3 objetos
    mock_list_files.return_value = iter([
        {"name": "file1.pdf", "metadata": {"size": 100}, "full_path": "org/client/file1.pdf"},
        {"name": "file2.pdf", "metadata": {"size": 200}, "full_path": "org/client/file2.pdf"},
        {"name": "subfolder", "metadata": None, "full_path": "org/client/subfolder"},
    ])

    ctx = {"bucket_name": "test-bucket", "prefix": "org/client"}
    result = list_storage_objects_service(ctx)

    assert result["ok"] is True
    assert len(result["objects"]) == 3
    assert result["objects"][2]["is_folder"] is True  # subfolder
```

#### **TestDownloadFileService** (5 testes)

| # | Teste | Status | Objetivo |
|---|-------|--------|----------|
| 1 | `test_downloads_file_via_adapter` | ✅ PASS | Mock de `storage_download_file` + verifica chamada |
| 2 | `test_validates_bucket_and_file_path` | ✅ PASS | Valida que `file_path` e `local_path` vazios retornam erro |
| 3 | `test_handles_download_errors` | ✅ PASS | Exceção em `storage_download_file` → `ok=False` |
| 4 | `test_returns_file_bytes` | ✅ PASS | Verifica que `local_path` é retornado no result |
| 5 | `test_returns_correct_result_structure` | ✅ PASS | Estrutura: `ok`, `errors`, `message`, `local_path` |

**Observação Crítica**:
- **Issue detectada**: Mock de `using_storage_backend` precisa ser context manager.
- **Solução**: Usar `mock_using.return_value = mock_cm` + `mock_cm.__enter__` / `mock_cm.__exit__`.
- **Sem isso**: Erro `AttributeError: __enter__`.

---

### 2.2 `tests/test_external_upload_service.py` (9 testes implementados)

| # | Teste | Status | Objetivo |
|---|-------|--------|----------|
| 1 | `test_validates_online_connection` | ✅ PASS | Mock `is_really_online() = False` → `ok=False`, `should_show_ui=True` |
| 2 | `test_validates_files_selected` | ✅ PASS | `files=[]` → `ui_message_type="info"`, "Nenhum arquivo selecionado" |
| 3 | `test_builds_upload_items_from_files` | ✅ PASS | Mock `build_items_from_files` retornando `[]` → "Nenhum PDF valido" |
| 4 | `test_extracts_cnpj_from_cliente` | ✅ PASS | Mock widget CNPJ → verifica que `cliente["cnpj"]` é passado para `upload_files_to_supabase` |
| 5 | `test_uploads_via_upload_files_to_supabase` | ✅ PASS | Mock retorna `(2, 0)` → `result["result"] == (2, 0)` |
| 6 | `test_returns_error_when_offline` | ✅ PASS | `is_really_online() = False` + `get_supabase_state = ("unstable", ...)` → "Conexão Instável" |
| 7 | `test_returns_upload_counts` | ✅ PASS | Verifica `result["result"] == (ok_count, failed_count)` |
| 8 | `test_sets_should_show_ui_flag` | ✅ PASS | Cenários com/sem arquivos + offline → `should_show_ui=True` |
| 9 | `test_sets_ui_message_type` | ✅ PASS | Sem arquivos → `"info"`, sem PDFs válidos → `"warning"` |

**Padrão de Mock (CNPJ)**:
```python
@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_extracts_cnpj_from_cliente(self, mock_upload, mock_build_items, mock_is_online):
    mock_is_online.return_value = True
    mock_build_items.return_value = [{"path": "file1.pdf"}]
    mock_upload.return_value = (1, 0)

    # Mock de widget CNPJ
    mock_widget = MagicMock()
    mock_widget.get.return_value = "12.345.678/0001-99"

    ctx = {
        "files": ["file1.pdf"],
        "self": MagicMock(),
        "ents": {"CNPJ": mock_widget},
        "row": None
    }
    result = salvar_e_enviar_para_supabase_service(ctx)

    # Verifica que upload foi chamado com CNPJ correto
    assert mock_upload.called
    call_args = mock_upload.call_args
    cliente = call_args[0][1]  # Segundo argumento
    assert cliente["cnpj"] == "12.345.678/0001-99"
```

**Cobertura de Flags UI**:
- ✅ `should_show_ui`: testado em 2 cenários (sem arquivos, offline)
- ✅ `ui_message_type`: testado com "info", "warning", "error"
- ✅ `ui_message_title` e `ui_message_body`: validados indiretamente via mensagens

---

### 2.3 `tests/test_form_service.py` (8 testes SKIPPED)

**Status**: 🔴 **BLOQUEADO - Import Circular Não Resolvido**

| # | Teste | Status | Motivo do Skip |
|---|-------|--------|----------------|
| 1 | `test_validates_inputs` | ⏭️ SKIP | Import circular não resolvido |
| 2 | `test_prepares_payload_correctly` | ⏭️ SKIP | Import circular não resolvido |
| 3 | `test_performs_uploads_successfully` | ⏭️ SKIP | Import circular não resolvido |
| 4 | `test_handles_upload_errors` | ⏭️ SKIP | Import circular não resolvido |
| 5 | `test_finalizes_state` | ⏭️ SKIP | Import circular não resolvido |
| 6 | `test_returns_correct_result_structure` | ⏭️ SKIP | Import circular não resolvido |
| 7 | `test_validates_arquivos_selecionados` | ⏭️ SKIP | Import circular não resolvido |
| 8 | `test_executes_full_pipeline` | ⏭️ SKIP | Import circular não resolvido |

**Problema Detectado**:
```
AttributeError: module 'src.modules.uploads' has no attribute 'form_service'
```

**Ciclo de Import**:
```
form_service.py
    → imports src.modules.clientes.forms.pipeline (validate_inputs, prepare_payload, etc.)
        → pipeline.py imports src.modules.clientes.forms.client_form
            → client_form.py imports src.ui.forms.actions
                → actions.py imports src.modules.uploads.form_service
                    → CIRCULAR DEPENDENCY DETECTED
```

**Tentativa de Solução (FASE 22)**:
1. **Import interno**: Movido `from src.modules.uploads.form_service import ...` para dentro do método de teste.
2. **Resultado**: Falhou com `AttributeError` porque `src.modules.uploads.__init__.py` não expõe `form_service`.

**Solução Definitiva (FASE 23)**:
- Quebrar ciclo de dependência em `actions.py`.
- Considerar **dependency injection** ou **lazy import** no código de produção (NÃO na FASE 22).
- Alternativa: Expor `form_service` em `src/modules/uploads/__init__.py` (mas não resolve o ciclo).

---

## 3. Resultado de Execução (pytest)

### 3.1 Comando
```bash
pytest tests/test_session_service.py tests/test_pdf_preview_utils.py tests/test_form_service.py tests/test_external_upload_service.py tests/test_storage_browser_service.py -v --tb=short
```

### 3.2 Output Final
```
====================== test session starts =======================
platform win32 -- Python 3.13.7, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\Pichau\Desktop\v1.2.16 ok - Copia\tests
configfile: pytest.ini
plugins: anyio-4.11.0, cov-7.0.0
collected 54 items

tests\test_session_service.py ...........                   [ 20%]
tests\test_pdf_preview_utils.py ..............              [ 46%]
tests\test_form_service.py ssssssss                         [ 61%]
tests\test_external_upload_service.py .........             [ 77%]
tests\test_storage_browser_service.py ............          [100%]

================= 46 passed, 8 skipped in 2.08s =================
```

### 3.3 Análise de Resultados
- **46 testes executados**: 100% aprovados ✅
- **8 testes skipped**: form_service (bloqueados por import circular) ⏭️
- **0 falhas**: Implementação robusta
- **Tempo**: 2.08s (performance excelente para 46 testes)

---

## 4. Mocks Utilizados

### 4.1 Padrões de Mock Estabelecidos

#### **Context Manager (using_storage_backend)**
```python
mock_cm = MagicMock()
mock_using.return_value = mock_cm
mock_cm.__enter__.return_value = None
mock_cm.__exit__.return_value = None
```

#### **Adapter Storage**
```python
@patch("src.modules.uploads.storage_browser_service.storage_list_files")
@patch("src.modules.uploads.storage_browser_service.storage_download_file")
@patch("src.modules.uploads.storage_browser_service.using_storage_backend")
@patch("src.modules.uploads.storage_browser_service.get_bucket_name")
```

#### **Supabase Online Check**
```python
@patch("src.modules.uploads.external_upload_service.is_really_online")
@patch("src.modules.uploads.external_upload_service.get_supabase_state")
def test_validates_online_connection(self, mock_get_state, mock_is_online):
    mock_is_online.return_value = False
    mock_get_state.return_value = ("offline", "No network connection")
```

#### **Upload Functions**
```python
@patch("src.modules.uploads.external_upload_service.build_items_from_files")
@patch("src.modules.uploads.external_upload_service.upload_files_to_supabase")
def test_uploads_via_upload_files_to_supabase(self, mock_upload, mock_build_items):
    mock_build_items.return_value = [{"path": "file1.pdf"}]
    mock_upload.return_value = (1, 0)  # ok_count, failed_count
```

### 4.2 Bibliotecas Mockadas
| Dependência | Módulo | Razão do Mock |
|-------------|--------|---------------|
| `storage_list_files` | `adapters.storage.api` | Evitar chamadas reais ao Storage |
| `storage_download_file` | `adapters.storage.api` | Evitar IO de arquivos |
| `using_storage_backend` | `adapters.storage.api` | Context manager do adapter |
| `get_bucket_name` | `src.helpers.storage_utils` | Normalização de bucket |
| `is_really_online` | `infra.supabase_client` | Estado de conexão |
| `build_items_from_files` | `uploader_supabase` | Construção de items de upload |
| `upload_files_to_supabase` | `uploader_supabase` | Upload real ao Supabase |

---

## 5. Problemas Encontrados e Soluções

### 5.1 Problema: Context Manager Mock Incorreto
**Erro Original**:
```
AttributeError: 'MagicMock' object has no attribute '__enter__'
```

**Causa**: `using_storage_backend` é um context manager (`with` statement).

**Código Original (Incorreto)**:
```python
mock_using.__enter__ = MagicMock(side_effect=Exception("Bucket not found"))
mock_using.__exit__ = MagicMock()
```

**Solução**:
```python
mock_cm = MagicMock()
mock_using.return_value = mock_cm
mock_cm.__enter__.return_value = None
mock_cm.__exit__.return_value = None

# Para simular exceção:
mock_list_files.side_effect = Exception("Bucket not found")
```

**Lição Aprendida**: Mock de context managers requer `.return_value.__enter__` / `.return_value.__exit__`.

---

### 5.2 Problema: Mensagem de Validação com Acento
**Erro Original**:
```
AssertionError: assert 'obrigatórios' in 'Parâmetros inválidos para download'
```

**Causa**: Mensagem real usa "inválidos", não "obrigatórios" (código de produção inconsistente).

**Código de Produção** (`download_file_service`):
```python
if not file_path or not local_path:
    result["errors"].append("file_path e local_path são obrigatórios")
    result["message"] = "Parâmetros inválidos para download"  # ← "inválidos"
```

**Solução**: Ajustar teste para buscar por "inválidos":
```python
assert "inválidos" in result["message"]
```

**Observação**: Não alteramos código de produção (regra #1 da FASE 22).

---

### 5.3 Problema: Import Circular em form_service
**Erro**:
```
AttributeError: module 'src.modules.uploads' has no attribute 'form_service'
```

**Ciclo Detectado**:
```
form_service.py → pipeline → client_form → actions → form_service (LOOP)
```

**Tentativas de Solução (FASE 22)**:
1. ❌ Import no topo do teste
2. ❌ Import dentro do método de teste
3. ❌ Lazy import com `importlib`

**Solução Adotada**:
- Marcar todos os 8 testes como `@pytest.mark.skip(reason="Import circular não resolvido - implementar na FASE 23")`.
- **NÃO alterar código de produção** (regra #1).

**Próximo Passo (FASE 23)**:
- Refatorar `actions.py` para **não importar** `form_service` diretamente.
- Alternativas:
  1. **Dependency Injection**: Passar `salvar_e_upload_docs_service` como parâmetro.
  2. **Lazy Import**: Importar `form_service` dentro da função que o usa.
  3. **Inversão de Dependência**: Mover lógica de `actions.py` para `form_service.py`.

---

## 6. Alterações em Código de Produção

**Resposta**: ❌ **NENHUMA**

Conforme **REGRA #1 da FASE 22**:
> NÃO alterar textos de mensagem, logs ou estrutura de retorno dos services.

- ✅ Todos os testes se adaptaram ao código existente.
- ✅ Nenhuma refatoração foi feita.
- ✅ Import circular foi **documentado**, não corrigido.

---

## 7. Cobertura de Services Atual

### 7.1 Services Testados (FASES 21 + 22)
- ✅ `SessionCache` (src/modules/main_window/session_service.py) - 11 testes
- ✅ `LRUCache` (src/modules/pdf_preview/utils.py) - 9 testes
- ✅ `pixmap_to_photoimage` (src/modules/pdf_preview/utils.py) - 5 testes
- ✅ `list_storage_objects_service` (src/modules/uploads/storage_browser_service.py) - 7 testes
- ✅ `download_file_service` (src/modules/uploads/storage_browser_service.py) - 5 testes
- ✅ `salvar_e_enviar_para_supabase_service` (src/modules/uploads/external_upload_service.py) - 9 testes

### 7.2 Services Parcialmente Testados (Bloqueados)
- 🔴 `salvar_e_upload_docs_service` (src/modules/uploads/form_service.py) - 8 testes skipped

### 7.3 Services Não Testados (Backlog)
- ⏳ `src/modules/pdf_preview/service.py`
- ⏳ `src/modules/clientes/service.py`
- ⏳ `src/modules/lixeira/service.py`
- ⏳ `src/modules/notas/service.py`
- ⏳ `src/modules/auditoria/service.py`
- ⏳ (15+ services restantes)

---

## 8. Comparação com FASES Anteriores

| Fase | Foco | Linhas Reduzidas | Testes Criados | Testes Implementados | Skipped |
|------|------|------------------|----------------|----------------------|---------|
| FASE 19 | Modularizar PDF preview | -129 (14.7%) | 0 | 0 | 0 |
| FASE 20 | Modularizar main_window | -26 (3.8%) | 0 | 0 | 0 |
| FASE 21 | Criar testes base | 0 | 54 | 25 | 29 |
| **FASE 22** | **Implementar testes upload** | **0** | **0 novos** | **46 (+21)** | **8 (-21)** |

**Progresso de Testes**:
```
FASE 21: [====25 impl====][===========29 skip===========]
FASE 22: [===============46 impl===============][==8 skip==]
```

**Insight**: FASE 22 reduziu skipped em **72%** (29 → 8), aumentando implementados em **84%** (25 → 46).

---

## 9. Próximos Passos (FASE 23)

### 9.1 Prioridade Alta: Resolver Import Circular
**Objetivo**: Implementar os 8 testes de `form_service` que estão bloqueados.

**Estratégia**:
1. **Análise de Dependências**:
   - Mapear ciclo completo: `form_service` → `pipeline` → `client_form` → `actions` → `form_service`.
   - Identificar qual import é o "mais fraco" para quebrar.

2. **Refatoração Proposta**:
   - **Opção A (Lazy Import)**: Em `actions.py`, mover import para dentro da função:
     ```python
     def salvar_e_upload_docs(...):
         from src.modules.uploads.form_service import salvar_e_upload_docs_service
         return salvar_e_upload_docs_service(ctx)
     ```
   - **Opção B (Dependency Injection)**: Passar `salvar_e_upload_docs_service` como parâmetro.
   - **Opção C (Inversão)**: Mover lógica de `actions.py` para `form_service.py`.

3. **Validação**:
   - Rodar testes de `form_service` após refatoração.
   - Garantir que nenhum comportamento foi alterado (diff comportamental).

### 9.2 Aumentar Cobertura
- [ ] Integrar `pytest-cov` para métricas de cobertura
- [ ] Meta: 80% de cobertura para services core
- [ ] Adicionar testes para:
  - `src/modules/clientes/service.py`
  - `src/modules/lixeira/service.py`
  - `src/modules/notas/service.py`

### 9.3 Testes de Integração
- [ ] Criar testes de integração (não apenas unitários) para:
  - Fluxo completo de upload (form_service → uploader_supabase → Storage)
  - Fluxo de download (storage_browser_service → adapters → filesystem)

---

## 10. Conclusão

A FASE 22 **expandiu significativamente** a cobertura de testes unitários para os services de upload:

- ✅ **21 novos testes implementados** (storage_browser + external_upload)
- ✅ **100% de aprovação** nos testes executados (46 passed, 0 failed)
- ⏭️ **8 testes skipped** (form_service - bloqueado por import circular)
- ✅ **Padrões de mock** estabelecidos para context managers e adapters
- ✅ **Nenhuma alteração** em código de produção (regra #1 respeitada)

**Impacto**:
- **Confiabilidade**: Testes garantem que storage_browser e external_upload funcionam conforme esperado.
- **Regressão**: Mudanças futuras podem ser validadas automaticamente.
- **Documentação**: Testes servem como documentação executável do comportamento dos services.

**Bloqueios Identificados**:
- 🔴 **Import circular** em `form_service` impede teste de 8 casos.
- ⚠️ **FASE 23** focará exclusivamente em resolver esse ciclo de dependência.

**Métricas de Qualidade**:
- Taxa de testes implementados: **85% (46/54)**
- Taxa de testes skipped: **15% (8/54)**
- Tempo médio por teste: **0.045s** (2.08s / 46 testes)

**Próxima Etapa**: FASE 23 - Resolver import circular e implementar testes de `form_service`.

---

**Autor**: GitHub Copilot  
**Modelo**: Claude Sonnet 4.5  
**Data de Criação**: 19 de novembro de 2025
