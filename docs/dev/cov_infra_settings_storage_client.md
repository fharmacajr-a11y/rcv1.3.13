# COV-INFRA-001 – Aumento de Cobertura dos Módulos de Infraestrutura

**Data:** 23 de novembro de 2025  
**Branch:** `qa/fixpack-04`  
**Tarefa:** COV-INFRA-001 do checklist de tarefas priorizadas  

---

## Resumo

Implementados testes abrangentes para os módulos de infraestrutura `infra/settings.py` e `infra/supabase/storage_client.py`, elevando suas coberturas de ~0% e ~14% para **97.3%** e **87.1%** respectivamente. O trabalho envolveu a criação de 47 testes unitários distribuídos em 2 arquivos, cobrindo todas as APIs públicas, helpers internos, cenários de erro, e edge cases. Nenhuma alteração comportamental foi realizada - apenas testes foram adicionados.

**Ganho de cobertura:**
- `infra/settings.py`: **0% → 97.3%** (+97.3pp)
- `infra/supabase/storage_client.py`: **14% → 87.1%** (+73.1pp)
- **App Core total:** 38.64% → 43.44% (+4.8pp)

---

## Cenários Implementados

### Módulo `infra/settings.py` (19 testes)

**Arquivo:** `tests/test_infra_settings_fase35.py`

#### get_value()
- ✅ Retorna default quando arquivo não existe
- ✅ Lê valor do arquivo JSON
- ✅ Retorna default quando chave não existe
- ✅ Retorna None quando default não especificado
- ✅ Retorna dict vazio quando JSON inválido
- ✅ Retorna dict vazio quando JSON não é dict
- ✅ Fallback para default em arquivo corrompido

#### set_value()
- ✅ Persiste valor em disco (modo CLOUD_ONLY=False)
- ✅ Sobrescreve valor existente
- ✅ Remove chave quando value=None
- ✅ Cria diretório se não existir
- ✅ Modo memória (CLOUD_ONLY=True) não escreve em disco
- ✅ Erros de escrita não levantam exceções

#### update_values()
- ✅ Atualiza múltiplos campos
- ✅ Preserva campos existentes não atualizados
- ✅ Dict vazio não causa erro
- ✅ Parâmetro não-dict é ignorado
- ✅ Atualização em lote funciona corretamente

#### Cache
- ✅ Múltiplas leituras reutilizam cache
- ✅ Escritas atualizam cache

#### Threading
- ✅ Lock (RLock) presente para segurança concorrente

---

### Módulo `infra/supabase/storage_client.py` (28 testes)

**Arquivo:** `tests/test_infra_storage_client_fase36.py`

#### Helpers Internos
- ✅ `_downloads_dir()` retorna Downloads ou temp
- ✅ `_pick_name_from_cd()` extrai filename do Content-Disposition
- ✅ `_pick_name_from_cd()` extrai filename* UTF-8
- ✅ `_pick_name_from_cd()` retorna fallback quando vazio
- ✅ `_pick_name_from_cd()` retorna fallback quando inválido
- ✅ `_slugify()` converte texto para slug URL-safe
- ✅ `_slugify()` remove acentos
- ✅ `_slugify()` com string vazia
- ✅ `_sess()` retorna mesma instância (singleton)

#### baixar_pasta_zip()
- ✅ Download bem-sucedido de pasta como ZIP
- ✅ Validação de parâmetros obrigatórios (bucket, prefix)
- ✅ Erro HTTP 500 levanta RuntimeError
- ✅ Content-Type não-ZIP levanta RuntimeError
- ✅ Timeout de leitura levanta TimeoutError
- ✅ Timeout de conexão levanta TimeoutError
- ✅ RequestException levanta RuntimeError
- ✅ Cancelamento via threading.Event levanta DownloadCancelledError
- ✅ Progress callback é chamado durante download
- ✅ Evita sobrescrever arquivo existente (adiciona sufixo)
- ✅ Download truncado levanta IOError

#### build_client_prefix()
- ✅ Formato correto `{org_id}/{client_id}`
- ✅ client_id=None levanta ValueError
- ✅ client_id=0 levanta ValueError (falsy)

#### ensure_client_storage_prefix()
- ✅ Cria placeholder .keep no bucket
- ✅ Passa upsert como string "true"
- ✅ Erro no upload levanta exceção
- ✅ Limpa arquivo temporário após upload

#### Exception Classes
- ✅ DownloadCancelledError é Exception

---

## Comandos Executados

### 1. Executar testes dos novos módulos

```powershell
python -m pytest tests/test_infra_settings_fase35.py tests/test_infra_storage_client_fase36.py -v
```

**Resultado:**
```
========================== 47 passed in 2.19s ===========================
```

---

### 2. Medir cobertura específica dos módulos

```powershell
python -m pytest `
  --cov=infra.settings `
  --cov=infra.supabase.storage_client `
  --cov-report=term-missing `
  tests/test_infra_settings_fase35.py `
  tests/test_infra_storage_client_fase36.py -q
```

**Resultado:**
```
Name                               Stmts   Miss Branch BrPart  Cover   Missing
--------------------------------------------------------------------------------
infra\settings.py                     63      2     12      0  97.3%   93-94
infra\supabase\storage_client.py     152     22     34      2  87.1%   102-103, 110-111, 126-127, 141-142, 145-146, 150, 158-159, 162-166, 171-172, 264-265
--------------------------------------------------------------------------------
TOTAL                                215     24     46      2  90.0%
```

**Cobertura alcançada:**
- ✅ `infra/settings.py`: **97.3%** (meta: ≥50%) → **META ATINGIDA COM FOLGA**
- ✅ `infra/supabase/storage_client.py`: **87.1%** (meta: ≥50%) → **META ATINGIDA COM FOLGA**

**Linhas não cobertas:**
- `infra/settings.py` (93-94): Logging interno em erro de escrita (requires falha de I/O)
- `infra/supabase/storage_client.py`:
  - Linhas 102-103, 110-111, 126-127, etc.: Tratamento de erros específicos em edge functions e cancelamento
  - Linha 264-265: Logging interno (requires integração real com Supabase)

---

### 3. Validar suíte completa (sem regressões)

```powershell
python -m pytest --cov --cov-report=term --cov-fail-under=25 -q
```

**Resultado:**
```
TOTAL                                                    15886   8630   3500    321  43.4%
Required test coverage of 25% reached. Total coverage: 43.44%
```

**Status:**
- ✅ Todos os 1084+ testes passaram
- ✅ Nenhuma regressão detectada
- ✅ Threshold de 25% mantido
- ✅ App Core coverage: **38.64% → 43.44%** (+4.8pp)

---

## Impacto

### Arquivos Criados
1. `tests/test_infra_settings_fase35.py` (382 linhas, 19 testes)
2. `tests/test_infra_storage_client_fase36.py` (481 linhas, 28 testes)

### Arquivos Modificados
- ❌ Nenhum (somente testes foram adicionados)

### Métricas
- **Testes adicionados:** 47
- **Linhas de teste:** 863
- **Cobertura App Core:** +4.8pp (38.64% → 43.44%)
- **Tempo de execução:** ~2.2s (testes novos), ~100s (suíte completa)

---

## Correção de Documentação

**Problema identificado:** O checklist e documentação baseline referenciavam `infra/storage_client.py`, mas o arquivo real está em `infra/supabase/storage_client.py`.

**Ação tomada:** Testes criados para o arquivo correto. Checklist será atualizado com o caminho correto.

---

## Observações

1. **Padrão seguido:** TEST-001 + QA-003 (mesma abordagem de COV-SEC-001)
2. **Isolamento:** Todos os testes usam mocks/patches para evitar I/O real e dependências externas
3. **Fixtures:** Implementados 7 fixtures para gerenciar estado (temp files, cache cleanup, mocks)
4. **Compatibilidade:** Testes compatíveis com CLOUD_ONLY mode (settings.py)
5. **Sem circular imports:** Diferente de COV-DATA-001, estes módulos são leaf dependencies

---

## Checklist

- ✅ Testes criados e passando (47/47)
- ✅ Cobertura ≥50% alcançada para ambos módulos
- ✅ Suíte completa sem regressões
- ✅ Documentação criada (`dev/cov_infra_settings_storage_client.md`)
- 🔲 Checklist atualizado (próximo passo)

---

## Referências

- **Checklist:** `docs/dev/checklist_tarefas_priorizadas.md` (linha 1802)
- **Baseline:** `docs/dev/baseline_cobertura_app_core.md`
- **Padrão:** TEST-001, QA-003
- **Exemplo anterior:** `dev/cov_sec_crypto.md` (COV-SEC-001)
