# DevLog: INFRA-OBSERVABILIDADE-STORAGE-01 - Logging estruturado para Supabase Storage

**Data:** 2025-12-08  
**Autor:** Copilot + Human  
**Branch:** `qa/fixpack-04`  
**Contexto:** FASE INFRA-OBSERVABILIDADE-STORAGE-01 — Adicionar visibilidade sobre operações de Supabase/Storage

---

## 1. Contexto e Motivação

### 1.1 Problema Identificado

**Déficit de observabilidade:**
- Baixa visibilidade sobre tempos de resposta de Supabase/Storage
- Dificuldade em identificar gargalos (rede vs. aplicação)
- Logs inconsistentes entre módulos (`db_client`, `supabase_storage`, `uploads.service`)
- Sem rastreamento de erros por bucket/rota
- Troubleshooting difícil em produção

**Exemplo de log anterior:**
```python
# Em uploads/service.py
logger.info("Upload Storage: original=%r -> key=%s", entry.relative_path, entry.storage_path)

# Sem informações de:
# - duração da operação
# - tamanho do arquivo
# - resultado (sucesso/erro)
# - tipo de erro (timeout, 404, permission denied)
```

### 1.2 Objetivo da Fase

Criar um "envelope de observabilidade" em cima das operações de Supabase/Storage para:

✅ **Logar de forma consistente:**
- Qual operação (upload/download/delete/list)
- Qual bucket/remote_key
- Duração da operação (ms)
- Resultado (sucesso/erro + tipo de erro)
- Metadados relevantes (tamanho, count)

✅ **Facilitar troubleshooting:**
- Identificar operações lentas
- Rastrear erros por tipo
- Correlacionar falhas com buckets/rotas específicas

✅ **Manter compatibilidade:**
- Sem alteração de assinaturas públicas
- Sem mudança de regra de negócio
- Backward compatible

---

## 2. Mapeamento das Operações de Storage

### 2.1 Arquitetura Atual

**Camadas identificadas:**

```
┌─────────────────────────────────────────────────────────────┐
│ UI (uploads/auditoria/hub)                                 │
│   - Módulos de negócio que usam storage                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ src/modules/uploads/service.py                             │
│   - download_and_open_file()                               │
│   - upload_items_for_client()                              │
│   - delete_storage_object()                                │
│   - list_browser_items()                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ adapters/storage/supabase_storage.py                       │
│   - _upload(client, bucket, source, key)                   │
│   - _download(client, bucket, key, local_path)             │
│   - _delete(client, bucket, key)                           │
│   - _list(client, bucket, prefix)                          │
│   - SupabaseStorageAdapter (class)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ infra/supabase/db_client.py                                │
│   - get_supabase_client() (singleton)                      │
│   - health_check_once()                                    │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
              Supabase API
```

### 2.2 Operações Principais Identificadas

**Em `adapters/storage/supabase_storage.py`:**

1. **`_upload()`**
   - Chamada: `client.storage.from_(bucket).upload(key, data, file_options)`
   - Uso: Upload de arquivos (documentos de clientes, relatórios)
   - Metadados relevantes: tamanho do arquivo, content-type

2. **`_download()`**
   - Chamada: `client.storage.from_(bucket).download(key)`
   - Uso: Download para visualização, exportação
   - Metadados relevantes: tamanho baixado, local_path (se salvo)

3. **`_delete()`**
   - Chamada: `client.storage.from_(bucket).remove([key])`
   - Uso: Exclusão de documentos obsoletos
   - Metadados relevantes: sucesso/falha

4. **`_list()`**
   - Chamada: `client.storage.from_(bucket).list(path, options)`
   - Uso: Navegação de arquivos (browser)
   - Metadados relevantes: quantidade de itens retornados

**Em `src/modules/uploads/service.py`:**
- `download_and_open_file()`: já tinha logs básicos de download
- `upload_folder_to_supabase()`: já logava keys de upload
- `delete_storage_object()`: logs de warning/error

---

## 3. Padrão de Log Estruturado Definido

### 3.1 Formato de Log

**Logger dedicado:**
```python
logger = logging.getLogger("infra.supabase.storage")
```

**Convenção de mensagens:**

1. **Início da operação (INFO):**
   ```
   storage.op.start: op=<operation>, bucket=<bucket>, key=<key>, [metadata]
   ```

2. **Sucesso da operação (INFO):**
   ```
   storage.op.success: op=<operation>, bucket=<bucket>, key=<key>, duration_ms=<ms>, [metadata]
   ```

3. **Erro da operação (ERROR/WARNING):**
   ```
   storage.op.error: op=<operation>, bucket=<bucket>, key=<key>, duration_ms=<ms>, error=<type>
   ```

### 3.2 Metadados por Operação

| Operação | Start | Success | Error |
|----------|-------|---------|-------|
| **upload** | op, bucket, key, size | + duration_ms | + duration_ms, error |
| **download** | op, bucket, key | + size, duration_ms, local_path (se existir) | + duration_ms, error |
| **delete** | op, bucket, key | + duration_ms | + duration_ms, error |
| **list** | op, bucket, prefix | + count, duration_ms | + duration_ms, error |

### 3.3 Medição de Tempo

**Técnica:** `time.perf_counter()` para alta precisão

```python
start = time.perf_counter()
try:
    # operação
    ...
except Exception as exc:
    duration_ms = (time.perf_counter() - start) * 1000
    logger.error("storage.op.error: ..., duration_ms=%.2f", duration_ms)
    raise
else:
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("storage.op.success: ..., duration_ms=%.2f", duration_ms)
```

---

## 4. Implementação

### 4.1 Mudanças em `adapters/storage/supabase_storage.py`

**Imports adicionados:**
```python
import logging
import time
```

**Logger criado:**
```python
logger = logging.getLogger("infra.supabase.storage")
```

**Função `_upload()` instrumentada:**

**Antes:**
```python
def _upload(client, bucket, source, remote_key, content_type, *, upsert=True):
    key = _normalize_key(remote_key)
    file_options = {...}
    data = _read_data(source)
    response = client.storage.from_(bucket).upload(key, data, file_options)
    # ... parse response ...
    return key
```

**Depois:**
```python
def _upload(client, bucket, source, remote_key, content_type, *, upsert=True):
    key = _normalize_key(remote_key)
    file_options = {...}
    data = _read_data(source)
    data_size = len(data)

    start = time.perf_counter()
    logger.info(
        "storage.op.start: op=upload, bucket=%s, key=%s, size=%d",
        bucket, key, data_size,
    )

    try:
        response = client.storage.from_(bucket).upload(key, data, file_options)
        # ... parse response ...

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "storage.op.success: op=upload, bucket=%s, key=%s, size=%d, duration_ms=%.2f",
            bucket, key, data_size, duration_ms,
        )
        return result_path

    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "storage.op.error: op=upload, bucket=%s, key=%s, size=%d, duration_ms=%.2f, error=%s",
            bucket, key, data_size, duration_ms, type(exc).__name__,
            exc_info=True,
        )
        raise
```

**Funções instrumentadas:**
- ✅ `_upload()`: logs de start/success/error com tamanho e duração
- ✅ `_download()`: logs de start/success/error com tamanho, duração e local_path
- ✅ `_delete()`: logs de start/success/error com duração (warning para falha de API)
- ✅ `_list()`: logs de start/success/error com count e duração

### 4.2 Exemplo de Logs Gerados

**Upload bem-sucedido:**
```
INFO:infra.supabase.storage: storage.op.start: op=upload, bucket=rc-docs, key=docs/cliente123/contrato.pdf, size=245632
INFO:infra.supabase.storage: storage.op.success: op=upload, bucket=rc-docs, key=docs/cliente123/contrato.pdf, size=245632, duration_ms=1234.56
```

**Download bem-sucedido:**
```
INFO:infra.supabase.storage: storage.op.start: op=download, bucket=rc-docs, key=docs/cliente123/contrato.pdf
INFO:infra.supabase.storage: storage.op.success: op=download, bucket=rc-docs, key=docs/cliente123/contrato.pdf, size=245632, duration_ms=987.65, local_path=/tmp/rc_gestor_uploads/contrato.pdf
```

**Erro de download (404):**
```
INFO:infra.supabase.storage: storage.op.start: op=download, bucket=rc-docs, key=docs/cliente999/inexistente.pdf
ERROR:infra.supabase.storage: storage.op.error: op=download, bucket=rc-docs, key=docs/cliente999/inexistente.pdf, duration_ms=123.45, error=HTTPError
Traceback (most recent call last):
  ...
```

**List bem-sucedido:**
```
INFO:infra.supabase.storage: storage.op.start: op=list, bucket=rc-docs, prefix=docs/cliente123
INFO:infra.supabase.storage: storage.op.success: op=list, bucket=rc-docs, prefix=docs/cliente123, count=15, duration_ms=345.67
```

**Delete com falha de API:**
```
INFO:infra.supabase.storage: storage.op.start: op=delete, bucket=rc-docs, key=docs/arquivo.pdf
WARNING:infra.supabase.storage: storage.op.error: op=delete, bucket=rc-docs, key=docs/arquivo.pdf, duration_ms=234.56, error=RemoveFailed
```

### 4.3 Logs em `uploads/service.py`

**Estado atual:** Logs já existentes mantidos (sem alteração)

**Exemplo existente:**
```python
logger.info("Upload Storage: original=%r -> key=%s", entry.relative_path, entry.storage_path)
```

**Benefício:** Agora este log de nível de negócio é complementado pelos logs técnicos de storage:
```
# Nível de negócio (uploads/service.py)
INFO:src.modules.uploads.service: Upload Storage: original='contrato.pdf' -> key=docs/cliente123/contrato.pdf

# Nível técnico (adapters/storage/supabase_storage.py)
INFO:infra.supabase.storage: storage.op.start: op=upload, bucket=rc-docs, key=docs/cliente123/contrato.pdf, size=245632
INFO:infra.supabase.storage: storage.op.success: op=upload, bucket=rc-docs, key=docs/cliente123/contrato.pdf, size=245632, duration_ms=1234.56
```

---

## 5. Testes de Observabilidade

### 5.1 Novo Arquivo de Testes

**Criado:** `tests/unit/adapters/test_supabase_storage_observability.py` (382 linhas)

**Objetivo:** Validar que logs estruturados são gerados corretamente

### 5.2 Testes Implementados (12 testes)

**Grupo 1: Upload logging (2 testes)**
1. `test_upload_logs_start_and_success`: Valida logs de início e sucesso
2. `test_upload_logs_error_on_exception`: Valida log de erro

**Grupo 2: Download logging (3 testes)**
1. `test_download_logs_start_and_success_bytes`: Valida logs (modo bytes)
2. `test_download_logs_success_with_local_path`: Valida logs com path local
3. `test_download_logs_error_on_exception`: Valida log de erro

**Grupo 3: Delete logging (3 testes)**
1. `test_delete_logs_start_and_success`: Valida logs de sucesso
2. `test_delete_logs_warning_on_api_error`: Valida warning quando API retorna erro
3. `test_delete_logs_error_on_exception`: Valida log de exceção

**Grupo 4: List logging (2 testes)**
1. `test_list_logs_start_and_success`: Valida logs com count de itens
2. `test_list_logs_error_on_exception`: Valida log de erro

**Grupo 5: Validação de metadados (2 testes)**
1. `test_upload_includes_duration_in_logs`: Valida que duration_ms é número >= 0
2. `test_download_includes_size_in_logs`: Valida que size é correto

### 5.3 Técnica de Teste: `caplog` do pytest

**Exemplo:**
```python
def test_upload_logs_start_and_success(mock_client, temp_file, caplog):
    # Arrange
    mock_client.storage.from_().upload.return_value = {"data": {"path": "docs/test.pdf"}}

    # Act
    with caplog.at_level("INFO", logger="infra.supabase.storage"):
        result = supabase_storage._upload(mock_client, "rc-docs", temp_file, "docs/test.pdf", None)

    # Assert
    log_messages = [rec.message for rec in caplog.records]

    assert any("storage.op.start: op=upload" in msg for msg in log_messages)
    assert any("bucket=rc-docs" in msg for msg in log_messages)
    assert any("storage.op.success: op=upload" in msg for msg in log_messages)
    assert any("duration_ms=" in msg for msg in log_messages)
```

**Benefício:** Testes headless (sem dependência de configuração de logging real)

---

## 6. Validação

### 6.1 Testes de Observabilidade

```bash
pytest tests/unit/adapters/test_supabase_storage_observability.py -v --tb=short
```

**Resultado:**
```
12 passed in 3.54s ✅
```

### 6.2 Testes de Storage (Fase 02)

```bash
pytest tests/unit/adapters/test_supabase_storage_fase02.py -v --tb=short -q
```

**Resultado:**
```
51 passed in 7.98s ✅
```

### 6.3 Suite Completa de Adapters

```bash
pytest tests/unit/adapters -v --tb=short -q
```

**Resultado:**
```
103 passed in 15.43s ✅
```

**Detalhamento:**
- 51 testes de storage (fase 02)
- 12 testes de observabilidade (novos)
- 40 testes de outros adapters

### 6.4 Testes de Uploads

```bash
pytest tests/unit/modules/uploads -v --tb=short -q
```

**Resultado:**
```
216 passed, 4 skipped in 31.90s ✅
```

**Conclusão:** Nenhuma regressão detectada!

---

## 7. Impacto

### 7.1 Arquivos Criados

1. **`tests/unit/adapters/test_supabase_storage_observability.py`** (382 linhas)
   - 12 novos testes de observabilidade
   - Validação de logs estruturados

### 7.2 Arquivos Modificados

1. **`adapters/storage/supabase_storage.py`** (+82 linhas, ~120 linhas modificadas)
   - Import de `logging` e `time`
   - Logger `infra.supabase.storage`
   - Instrumentação de `_upload()`, `_download()`, `_delete()`, `_list()`
   - Try/except/else com logs de start/success/error

### 7.3 Benefícios Imediatos

✅ **Visibilidade de performance:**
- Identificar uploads/downloads lentos (> 5s)
- Detectar timeouts de rede
- Correlacionar latência com tamanho de arquivo

✅ **Troubleshooting facilitado:**
- Logs estruturados filtráveis por operação: `grep "op=download" app.log`
- Rastreamento de erros por bucket: `grep "bucket=rc-docs" | grep "error"`
- Stack trace completo de exceções (com `exc_info=True`)

✅ **Métricas para monitoramento futuro:**
- Taxa de sucesso/erro por operação
- P50/P95/P99 de duration_ms
- Volume de dados transferidos (sum de size)

✅ **Compatibilidade mantida:**
- Assinaturas de funções inalteradas
- Testes existentes passando (0 regressões)
- Backward compatible

---

## 8. Exemplos de Uso

### 8.1 Identificar operações lentas

**Comando:**
```bash
# Filtrar operações > 2s
grep "storage.op.success" app.log | awk -F'duration_ms=' '{print $2}' | awk '{if($1 > 2000) print}'
```

**Saída esperada:**
```
2345.67
3456.78
5678.90
```

### 8.2 Rastrear erros de download

**Comando:**
```bash
grep "storage.op.error: op=download" app.log
```

**Saída esperada:**
```
ERROR:infra.supabase.storage: storage.op.error: op=download, bucket=rc-docs, key=docs/missing.pdf, duration_ms=123.45, error=HTTPError
ERROR:infra.supabase.storage: storage.op.error: op=download, bucket=rc-docs, key=docs/timeout.pdf, duration_ms=30000.00, error=TimeoutError
```

### 8.3 Analisar volume de uploads por bucket

**Comando:**
```bash
# Somar size de uploads bem-sucedidos
grep "storage.op.success: op=upload" app.log | grep "bucket=rc-docs" | \
  awk -F'size=' '{print $2}' | awk -F',' '{sum+=$1} END {print sum/1024/1024 " MB"}'
```

### 8.4 Verificar taxa de sucesso/erro

**Python script:**
```python
import re

with open("app.log") as f:
    success = len([l for l in f if "storage.op.success: op=upload" in l])
    errors = len([l for l in f if "storage.op.error: op=upload" in l])

print(f"Sucesso: {success}, Erro: {errors}, Taxa: {success/(success+errors)*100:.2f}%")
```

---

## 9. Próximos Passos (Futuro)

### 9.1 Métricas Prometheus (Opcional)

**Oportunidade:** Expor métricas de storage via Prometheus

**Exemplo:**
```python
from prometheus_client import Counter, Histogram

storage_ops_total = Counter(
    "storage_operations_total",
    "Total storage operations",
    ["operation", "bucket", "status"],
)

storage_duration_seconds = Histogram(
    "storage_operation_duration_seconds",
    "Storage operation duration",
    ["operation", "bucket"],
)

# Em _upload()
with storage_duration_seconds.labels(op="upload", bucket=bucket).time():
    # ... operação ...
    storage_ops_total.labels(op="upload", bucket=bucket, status="success").inc()
```

### 9.2 Alertas Baseados em Logs

**Oportunidade:** Configurar alertas para condições anômalas

**Exemplos:**
- Alerta se taxa de erro > 10% em 5min
- Alerta se P95 de duration_ms > 5s
- Alerta se upload/download falha 3x seguidas

### 9.3 Dashboard de Observabilidade

**Oportunidade:** Criar dashboard Grafana/Kibana com:
- Gráfico de latência (P50/P95/P99) por operação
- Taxa de sucesso/erro ao longo do tempo
- Volume de dados transferidos (MB/GB por dia)
- Top 10 buckets/keys mais acessados

### 9.4 Structured Logging (JSON)

**Oportunidade:** Migrar para formato JSON estruturado

**Vantagem:** Parsing mais fácil, integração com ELK/Splunk

**Exemplo:**
```python
import structlog

logger = structlog.get_logger("infra.supabase.storage")

logger.info(
    "storage.op.success",
    operation="upload",
    bucket=bucket,
    key=key,
    size=data_size,
    duration_ms=duration_ms,
)
```

**Saída:**
```json
{
  "event": "storage.op.success",
  "operation": "upload",
  "bucket": "rc-docs",
  "key": "docs/file.pdf",
  "size": 245632,
  "duration_ms": 1234.56,
  "timestamp": "2025-12-08T15:30:45.123Z"
}
```

---

## 10. Notas Técnicas

### 10.1 Por que `time.perf_counter()`?

**Alternativas consideradas:**
- `time.time()`: Resolução de segundos (não suficiente para operações rápidas)
- `time.monotonic()`: Boa resolução, mas `perf_counter()` é mais preciso

**Decisão:** `time.perf_counter()` oferece:
- Alta precisão (nanosegundos no Windows, microsegundos no Linux)
- Monotônico (não afetado por ajustes de clock)
- Padrão para benchmarking em Python

### 10.2 Por que Logger Dedicado?

**Logger:** `infra.supabase.storage`

**Vantagens:**
- Isolamento: Fácil filtrar logs de storage (`grep "infra.supabase.storage"`)
- Configuração independente: Pode ajustar nível de log sem afetar outros módulos
- Hierarquia clara: `infra.*` para logs de infraestrutura

**Alternativa rejeitada:** Usar logger global (`logging.getLogger(__name__)`)
- Dificuldade em filtrar logs
- Mistura com logs de negócio

### 10.3 Por que `exc_info=True`?

**Decisão:** Sempre logar stack trace completo em erros

**Justificativa:**
- Troubleshooting: Stack trace essencial para entender causa raiz
- Produção: Logs são única fonte de informação quando erro ocorre
- Performance: Overhead negligível (apenas em caso de erro)

**Exemplo de saída:**
```
ERROR:infra.supabase.storage: storage.op.error: op=download, bucket=rc-docs, key=docs/file.pdf, duration_ms=123.45, error=HTTPError
Traceback (most recent call last):
  File "adapters/storage/supabase_storage.py", line 125, in _download
    data = client.storage.from_(bucket).download(key)
  File "site-packages/storage3/file_api.py", line 89, in download
    raise HTTPError(f"404: {key} not found")
HTTPError: 404: docs/file.pdf not found
```

### 10.4 Tratamento de Erros de API vs. Exceções

**Delete com erro de API:**
```python
response = client.storage.from_(bucket).remove([key])
if isinstance(response, dict) and response.get("error"):
    # API retornou erro estruturado (não exceção)
    logger.warning(
        "storage.op.error: op=delete, bucket=%s, key=%s, duration_ms=%.2f, error=RemoveFailed",
        bucket, key, duration_ms,
    )
    return False
```

**Exceção de rede:**
```python
except Exception as exc:
    # Exceção real (timeout, 404, etc)
    logger.error(
        "storage.op.error: op=delete, bucket=%s, key=%s, duration_ms=%.2f, error=%s",
        bucket, key, duration_ms, type(exc).__name__,
        exc_info=True,
    )
    raise
```

**Justificativa:**
- API errors: WARNING (operação controlada, não trava aplicação)
- Exceptions: ERROR (inesperado, precisa investigação)

---

## 11. Checklist de Conclusão

- [x] Mapear operações de storage (upload/download/delete/list)
- [x] Definir padrão de log estruturado
- [x] Criar logger dedicado (`infra.supabase.storage`)
- [x] Instrumentar `_upload()` com logs start/success/error
- [x] Instrumentar `_download()` com logs start/success/error
- [x] Instrumentar `_delete()` com logs start/success/error
- [x] Instrumentar `_list()` com logs start/success/error
- [x] Criar 12 testes de observabilidade
- [x] Validar com pytest (103 testes adapters ✅)
- [x] Validar com pytest (216 testes uploads ✅)
- [x] Verificar zero regressões
- [x] Criar este devlog

---

**FASE INFRA-OBSERVABILIDADE-STORAGE-01: CONCLUÍDA ✅**

**Resumo:**
- ✅ Logging estruturado implementado em 4 operações (upload/download/delete/list)
- ✅ 12 novos testes de observabilidade
- ✅ 319 testes passando (103 adapters + 216 uploads)
- ✅ Zero regressões
- ✅ Formato de log consistente (start/success/error)
- ✅ Métricas essenciais rastreadas (duração, tamanho, count, tipo de erro)
- ✅ Backward compatible (sem mudança de assinatura)
