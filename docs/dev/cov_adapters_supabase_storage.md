# Cobertura: adapters/storage/supabase_storage.py

**Status**: ✅ Concluído  
**Data**: 2025-01-21  
**Responsável**: COV-ADAPTERS-001

---

## Resumo

Aumentada a cobertura de testes do módulo `adapters/storage/supabase_storage.py` de **~36,8%** para **78,9%**, superando a meta de ≥70%.

### Métricas de Cobertura

| Métrica | Valor |
|---------|-------|
| **Cobertura anterior** | ~36,8% |
| **Cobertura atual** | 78,9% |
| **Statements** | 111 total, 20 missed |
| **Branches** | 22 total, 6 parcialmente cobertas |
| **Testes criados** | 40 testes |
| **Arquivo de testes** | `tests/test_adapters_supabase_storage_fase37.py` |

---

## Cenários de Teste

### 1. Funções Utilitárias (11 testes)
Testa normalização de buckets, remoção de acentos, detecção de content-type e leitura de dados:

- `test_normalize_bucket_valido` - Bucket válido não é modificado
- `test_normalize_bucket_vazio` - String vazia retorna "rc-docs" (default)
- `test_normalize_bucket_none` - None retorna "rc-docs" (default)
- `test_strip_accents_simples` - Remove acentos simples ("café" → "cafe")
- `test_strip_accents_multiplos` - Remove múltiplos acentos
- `test_normalize_key_for_storage_remove_acentos` - Normaliza keys com acentos
- `test_normalize_key_for_storage_remove_barras` - Remove barras no início/fim
- `test_guess_content_type_customizado` - Usa content-type fornecido
- `test_guess_content_type_pdf` - Detecta application/pdf
- `test_read_data_bytes` - Retorna bytes diretamente
- `test_read_data_bytes_vazio` - Trata dados vazios

### 2. Operações Privadas (10 testes)
Testa funções `_upload`, `_download`, `_delete`, `_list` com normalização automática:

- `test_upload_sucesso` - Upload retorna path do arquivo
- `test_upload_sem_content_type` - Upload funciona sem content-type
- `test_download_sucesso` - Download retorna bytes do arquivo
- `test_delete_sucesso` - Delete remove arquivo e retorna True
- `test_list_sucesso` - List retorna lista de arquivos
- `test_list_pasta_vazia` - List retorna [] para pasta vazia
- `test_upload_normaliza_key` - Key com acentos é normalizado
- `test_download_normaliza_key` - Download normaliza key antes de buscar
- `test_delete_normaliza_key` - Delete normaliza key antes de remover
- `test_list_com_prefix` - List aceita prefix (pasta)

### 3. Classe SupabaseStorageAdapter (10 testes)
Testa métodos públicos do adapter e uso correto de buckets:

- `test_upload_file` - Upload via adapter
- `test_download_file` - Download via adapter
- `test_delete_file` - Delete via adapter
- `test_list_files` - List via adapter
- `test_adapter_usa_bucket_correto` - Usa bucket especificado no construtor
- `test_adapter_normaliza_bucket` - Normaliza nome do bucket
- `test_upload_file_normaliza_key` - Upload normaliza key automaticamente
- `test_download_file_bytes` - Download retorna bytes
- `test_list_files_sem_prefix` - List aceita prefix vazio
- `test_list_files_retorna_full_path` - List adiciona full_path aos resultados

### 4. Casos Extremos (9 testes)
Testa edge cases, validação de erros e comportamentos especiais:

- `test_normalize_bucket_com_espacos` - Remove espaços do bucket
- `test_strip_accents_sem_acentos` - Texto sem acentos permanece inalterado
- `test_normalize_key_for_storage_backslash` - Substitui backslashes por forward slashes
- `test_guess_content_type_desconhecido` - Retorna "application/octet-stream" para extensões desconhecidas
- `test_upload_key_com_barras_multiplas` - Normaliza keys com múltiplas barras
- `test_delete_retorna_false_em_erro` - Delete retorna False quando há erro
- `test_list_filtra_objetos_invalidos` - List filtra objetos não-dict da resposta
- `test_adapter_bucket_default` - Adapter usa "rc-docs" como bucket default
- `test_normalize_key_remove_barras_extremas` - Remove barras e acentos nas extremidades

---

## Comandos Executados

### 1. Teste isolado (validação inicial)
```powershell
python -m pytest tests/test_adapters_supabase_storage_fase37.py -v
```
**Resultado**: ✅ 40 passed in 0.29s

### 2. Cobertura do módulo específico
```powershell
python -m pytest --cov=adapters.storage.supabase_storage --cov-report=term-missing tests/test_adapters_supabase_storage_fase37.py -q
```
**Resultado**:
```
adapters\storage\supabase_storage.py     111     20     22      6  78.9%
```

**Linhas não cobertas**:
- 38->42, 60-62: Validações de erro no `_read_data` (Path inexistente)
- 84->86, 93, 95-100: Caminhos alternativos no `_download` com `local_path`
- 110, 177-178: Lógica interna de `_list` e `download_folder_zip`
- 192, 196, 200, 204: Funções de módulo (upload_file, download_file, delete_file, list_files)
- 216-217, 227: get_default_adapter e download_folder_zip (nível de módulo)

### 3. Suite completa (validação de regressão)
```powershell
python -m pytest --ignore=tests/test_auth_bootstrap_persisted_session.py --cov --cov-report=term-missing --cov-fail-under=25 -q
```
**Resultado**: ✅ Cobertura global: 43.28% (≥25%)  
**Impacto**: Nenhum teste quebrado pelos novos testes (falhas pré-existentes em outros módulos)

---

## Estratégia de Testes

### Isolamento de Dependências
- **Problema**: Circular import entre `adapters.storage.api` ↔ `src.modules.clientes.service`
- **Solução**: Fixture `setup_test_environment` (session-scoped) que:
  1. Mock `sys.modules` para `src`, `src.config`, `src.config.paths`, `infra.supabase_client`
  2. Importa o módulo real com mocks ativos
  3. Restaura módulos originais no teardown (evita poluição de outros testes)

### Mocking do Cliente Supabase
- `fake_supabase_client` fixture retorna `MagicMock` com estrutura:
  ```python
  client.storage.from_(bucket).upload/download/list/remove
  ```
- Simula respostas com estruturas similares às reais (dicts com "data", "error", etc.)

### Cobertura de Assinaturas
Todos os testes usam as assinaturas reais do módulo:
```python
_upload(client, bucket, source, remote_key, content_type, *, upsert=True)
_download(client, bucket, remote_key, local_path)
_delete(client, bucket, remote_key)
_list(client, bucket, prefix="")
upload_file(local_path, remote_key, content_type=None)
download_file(remote_key, local_path=None)
delete_file(remote_key)
list_files(prefix="")
```

---

## Impacto no Checklist

✅ **COV-ADAPTERS-001**: Concluído  
- Meta: ≥70% de cobertura  
- Alcançado: 78.9%  
- Arquivo: `tests/test_adapters_supabase_storage_fase37.py`  
- Documentação: `dev/cov_adapters_supabase_storage.md`

---

## Próximos Passos

Para atingir >90% de cobertura (opcional):
1. Adicionar testes para funções de módulo (`upload_file`, `download_file`, `delete_file`, `list_files` no nível raiz)
2. Testar `_download` com `local_path` não-None (salvamento em arquivo)
3. Testar `_read_data` com Path inexistente (erro de FileNotFoundError)
4. Testar `download_folder_zip` (função complexa de download de pasta zipada)

---

## Notas Técnicas

### Limitações do Teste
- `_read_data` com strings vazias tenta abrir Path('.'), causando PermissionError (comportamento real do módulo)
- `download_folder_zip` não testada (requer setup complexo com múltiplos arquivos)
- Funções de módulo (línea 192-227) não testadas diretamente (usam adapter interno)

### Lições Aprendidas
1. **sys.modules mocking deve ser session-scoped com cleanup** para evitar poluição de outros testes
2. **Assinaturas de funções devem ser validadas antes de escrever testes** (evita TypeError em massa)
3. **Mocks de cliente Supabase devem simular estrutura de respostas real** (dicts aninhados com "data")

---

**Autor**: GitHub Copilot  
**Revisão**: QA-003 ✅
