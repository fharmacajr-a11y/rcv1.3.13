# Análise Técnica — Infraestrutura Local de Subpastas/Pastas

**Versão**: v1.5.99  
**Data**: 2025-06-17  
**Escopo**: Determinar se a infraestrutura local de subpastas/pastas no disco é
funcionalmente necessária ou é legado passível de remoção.

---

## 1. INVENTÁRIO COMPLETO DE CALLERS

### 1.1 Funções do núcleo analisadas

| Função | Arquivo | Linhas |
|--------|---------|--------|
| `ensure_subpastas()` | `src/utils/file_utils/path_utils.py` | L106-145 |
| `ensure_subtree()` | `src/utils/file_utils/path_utils.py` | L70-103 |
| `ensure_dir()` | `src/utils/file_utils/path_utils.py` | L27-32 |
| `open_folder()` | `src/utils/file_utils/path_utils.py` | L44-60 |
| `safe_copy()` | `src/utils/file_utils/path_utils.py` | L34-42 |
| `write_marker()` | `src/utils/file_utils/bytes_utils.py` | L204-212 |
| `read_marker_id()` | `src/utils/file_utils/bytes_utils.py` | L214-238 |
| `load_subpastas_config()` | `src/utils/subpastas_config.py` | L48+ |
| `get_mandatory_subpastas()` | `src/utils/subpastas_config.py` | L39 |
| `join_prefix()` | `src/utils/subpastas_config.py` | L106 |
| `safe_base_from_fields()` | `src/core/app_utils.py` | L54-82 |
| `_pasta_do_cliente()` | `src/core/services/clientes_service.py` | L245-252 |
| `_migrar_pasta_se_preciso()` | `src/core/services/clientes_service.py` | L255-267 |
| `_ensure_live_folder_ready()` | `src/core/app_core.py` | L196-230 |
| `resolve_cliente_path()` | `src/core/services/path_resolver.py` | L121-160 |
| `sanitize_subfolder_name()` | `src/utils/subfolders.py` | L10+ |
| `list_storage_subfolders()` | `src/utils/subfolders.py` | L50+ |
| `SubpastaDialog` | `src/modules/clientes/forms/client_subfolder_prompt.py` | L34+ |
| `SubpastaDialog` (backup) | `src/ui/subpastas_dialog.py` | L24+ |

### 1.2 Mapa de chamadas (quem chama quem)

```
salvar_cliente()                    [clientes_service.py L271]
  └─ _pasta_do_cliente()            [clientes_service.py L245]
  │    ├─ safe_base_from_fields()   [app_utils.py L54]          ← PURA STRING
  │    ├─ os.path.join(DOCS_DIR, base)                          ← constrói caminho
  │    └─ if not CLOUD_ONLY:                                    ← GUARDA
  │         ├─ ensure_subpastas()   [path_utils.py L106]        ← NO-OP
  │         └─ write_marker()       [bytes_utils.py L204]       ← NO-OP
  └─ _migrar_pasta_se_preciso()     [clientes_service.py L255]
       ├─ ensure_subpastas()        ← internamente guarda CLOUD_ONLY
       ├─ os.path.isdir(old_path)   ← retorna False (pastas não existem)
       └─ shutil.copytree/copy2     ← nunca executado

_ensure_live_folder_ready()         [app_core.py L196]          ← DEAD CODE (0 callers)
  ├─ if NO_FS: return ""
  ├─ safe_base_from_fields()
  ├─ if not CLOUD_ONLY:
  │    ├─ ensure_subpastas()
  │    └─ write_marker()
  └─ load_subpastas_config()        [subpastas_config.py L48]

resolve_cliente_path()              [path_resolver.py L121]
  ├─ _find_by_marker(DOCS_DIR, pk)  ← os.listdir em /tmp/rc_void/docs (vazio)
  ├─ _find_by_marker(TRASH_DIR, pk) ← os.listdir em /tmp/rc_void/docs/_LIXEIRA
  ├─ _candidate_by_slug(pk)         ← safe_base_from_fields (string pura)
  └─ os.path.isdir(candidate)       ← retorna False

lixeira_service._ensure_mandatory_subfolders()  [lixeira_service.py L107]
  ├─ get_mandatory_subpastas()      ← ("SIFAP","ANVISA","FARMACIA_POPULAR","AUDITORIA")
  ├─ join_prefix()                  ← string utility
  └─ storage_upload_file(".keep")   ← SUPABASE STORAGE (não disco local!)

SubpastaDialog                      [client_subfolder_prompt.py L34]
  └─ sanitize_subfolder_name()      ← PURA STRING (sanitização)

SubpastaDialog (backup)             [subpastas_dialog.py L24]
  ├─ sanitize_subfolder_name()      ← PURA STRING
  └─ list_files() via SupabaseStorageAdapter  ← SUPABASE (não disco local!)
```

---

## 2. CLASSIFICAÇÃO DE CADA CALLER

### Legenda

| Classificação | Significado |
|---------------|-------------|
| **DEAD** | Código morto — 0 callers efetivos ou nunca executa |
| **VESTIGIAL** | Referenciado, mas o trecho é no-op por causa do `CLOUD_ONLY=True` default |
| **LIVE-CLOUD** | Ativo e opera sobre Supabase Storage (nuvem), não disco local |
| **LIVE-PURE** | Ativo, função pura (string/dados), sem I/O de disco |
| **SUPPORT** | Infraestrutura de suporte (re-exports, `__init__`, YAML) |

### Classificação detalhada

| # | Função/Módulo | Classificação | Justificativa |
|---|---------------|---------------|---------------|
| 1 | `_ensure_live_folder_ready()` | **DEAD** | Zero callers em todo o codebase. Dupla guarda `NO_FS` + `CLOUD_ONLY`. |
| 2 | `ensure_subpastas()` em `path_utils.py` | **VESTIGIAL** | Todo `os.makedirs` guarda `if not CLOUD_ONLY`. Com default True ⇒ no-op. |
| 3 | `ensure_subtree()` em `path_utils.py` | **VESTIGIAL** | Mesmo padrão: chamado por `ensure_subpastas`. No-op quando CLOUD_ONLY. |
| 4 | `ensure_dir()` em `path_utils.py` | **VESTIGIAL** | Guarda `if not CLOUD_ONLY`. No-op. |
| 5 | `open_folder()` em `path_utils.py` | **VESTIGIAL** | Guarda `if not CLOUD_ONLY`. O único uso era no fluxo externo já removido. |
| 6 | `safe_copy()` em `path_utils.py` | **VESTIGIAL** | Guarda `if not CLOUD_ONLY`. |
| 7 | `write_marker()` em `bytes_utils.py` | **VESTIGIAL** | `os.makedirs` guarda CLOUD_ONLY. Caller em `clientes_service` também guarda. |
| 8 | `read_marker_id()` em `bytes_utils.py` | **VESTIGIAL** | Lê `.rc_client_id` do disco; usado por `path_resolver/path_manager`. Retorna `None` porque os diretórios apontam para `/tmp/rc_void/docs` (vazio). |
| 9 | `load_subpastas_config()` | **SUPPORT** | Lê `subpastas.yml`. Chamada apenas por `ensure_subpastas` (vestigial) e `_ensure_live_folder_ready` (dead). |
| 10 | `get_mandatory_subpastas()` | **LIVE-CLOUD** | Retorna a tupla fixa. **Caller real**: `lixeira_service._ensure_mandatory_subfolders()` — opera no Supabase. |
| 11 | `join_prefix()` | **LIVE-CLOUD** | String utility. **Caller real**: `lixeira_service._ensure_mandatory_subfolders()`. |
| 12 | `safe_base_from_fields()` | **LIVE-PURE** | Função pura de string (constrói slug). Usada por `_pasta_do_cliente`, `path_resolver`, `path_manager`. |
| 13 | `_pasta_do_cliente()` | **VESTIGIAL** | Retorna string `pasta` (ref. local), mas FS ops são no-op. O campo `pasta` é retornado por `salvar_cliente()` mas **nunca é consumido** significativamente pelo caller (editor pega apenas `result[0]` = PK). |
| 14 | `_migrar_pasta_se_preciso()` | **VESTIGIAL** | `os.path.isdir(old_path)` retorna False — o `if` nunca entra. Todo o bloco de cópia é dead path. |
| 15 | `resolve_cliente_path()` | **VESTIGIAL** | Busca em `/tmp/rc_void/docs` (vazio). Retorna `ResolveResult` com `active=None, trash=None`. |
| 16 | `path_resolver.py` (módulo inteiro) | **VESTIGIAL** | Operações de disco em diretório vazio. Caller: `app_core.py` L164 (`resolve_unique_path`). |
| 17 | `path_manager.py` (módulo inteiro) | **VESTIGIAL** | Camada sobre `path_resolver`. Também opera sobre disco vazio. |
| 18 | `sanitize_subfolder_name()` | **LIVE-PURE** | Sanitização de string. Usada pelos dois SubpastaDialogs. Ativa. |
| 19 | `list_storage_subfolders()` | **LIVE-CLOUD** | Lista subpastas no Supabase Storage. |
| 20 | `SubpastaDialog` (client_subfolder_prompt) | **LIVE-CLOUD** | Diálogo de UI ativo, usado por `uploader_supabase.py`, `client_form_upload_helpers.py`. |
| 21 | `SubpastaDialog` (subpastas_dialog.py backup) | **VESTIGIAL** | Descrito como "backup" — zero callers diretos (nenhum import encontrado fora dele mesmo). |
| 22 | `subpastas.yml` | **SUPPORT** | Lido por `load_subpastas_config()`. O único caller ativo de `get_mandatory_subpastas` não usa o YAML — usa a tupla hardcoded. |
| 23 | `rc_hotfix_no_local_fs.py` | **SUPPORT** | Hotfix que força `RC_NO_LOCAL_FS=1`. Reforça a decisão de cloud-only. |
| 24 | `DOCS_DIR` | **VESTIGIAL** | Em CLOUD_ONLY aponta para `/tmp/rc_void/docs`. Referenciado por `clientes_service`, `path_resolver`, `path_manager`. |

---

## 3. PROPÓSITO REAL vs. INÉRCIA DE LEGADO

### 3.1 O que é REALMENTE necessário (LIVE)

Estas funções/dados servem o produto ATUAL (Supabase cloud):

| Componente | Propósito real |
|------------|----------------|
| `get_mandatory_subpastas()` | Define as 4 categorias obrigatórias (SIFAP, ANVISA, FARMACIA_POPULAR, AUDITORIA) usadas pelo `lixeira_service` ao restaurar clientes no Supabase. |
| `join_prefix()` | Utility de concatenação de prefixos usada pelo mesmo `lixeira_service`. |
| `sanitize_subfolder_name()` | Sanitização de nomes para subpastas de upload no Supabase. Usada pelos diálogos de UI. |
| `list_storage_subfolders()` | Lista subpastas no Supabase Storage (operação cloud). |
| `SubpastaDialog` (client_subfolder_prompt) | Diálogo UI ativo para selecionar subpasta em uploads Supabase. |
| `safe_base_from_fields()` | Constrói identificador determinístico de cliente (string pura). Poderia migrar. |

### 3.2 O que é INÉRCIA DE LEGADO (morto/vestigial)

| Componente | Por que é legado |
|------------|-----------------|
| `ensure_subpastas()` | Criava diretórios locais. Guarda `if not CLOUD_ONLY` ⇒ nunca executa. |
| `ensure_subtree()` | Helper recursivo de `ensure_subpastas`. Mesma situação. |
| `ensure_dir()` | Criava diretório local. No-op com CLOUD_ONLY. |
| `open_folder()` | Abria explorer local. No-op / fluxo externo já removido. |
| `safe_copy()` | Cópia de arquivos no disco. No-op. |
| `write_marker()` | Escrevia `.rc_client_id` no disco. No-op (caller guarda CLOUD_ONLY). |
| `read_marker_id()` | Lê marker do disco. Opera em dir vazio ⇒ sempre retorna `None`. |
| `_ensure_live_folder_ready()` | Zero callers. Dead code completo. |
| `_pasta_do_cliente()` | Retorna string de caminho local; ops de disco são no-op. O campo `pasta` retornado por `salvar_cliente()` **nunca é usado** pelo editor (apenas `result[0]` = PK é consumido). |
| `_migrar_pasta_se_preciso()` | `os.path.isdir` em path que não existe ⇒ nunca executa migração. |
| `resolve_cliente_path()` / `path_resolver.py` | Resolve paths em diretório vazio ⇒ sempre retorna `None`. |
| `path_manager.py` | Camada sobre resolver vestigial. |
| `load_subpastas_config()` | Lê `subpastas.yml`. Nenhum caller ativo depende dela — `get_mandatory_subpastas()` usa tupla hardcoded. |
| `subpastas.yml` | Configuração YAML. Consumida apenas por `load_subpastas_config` (vestigial). |
| `SubpastaDialog` (subpastas_dialog.py) | Versão "backup" sem callers diretos. |
| `DOCS_DIR` | Aponta para `/tmp/rc_void/docs` — diretório inerte. |

---

## 4. CONFRONTO COM A ARQUITETURA ATUAL

### Decisão arquitetural vigente

```
CLOUD_ONLY = env_bool("RC_NO_LOCAL_FS", True)   ← DEFAULT = True
```

O produto opera em modo **cloud-only por padrão**. O backend de arquivos é
**Supabase Storage**. A variável `RC_NO_LOCAL_FS` precisaria ser explicitamente
setada para `"0"` ou `"false"` para ativar o modo local.

### Infraestrutura local: o que realmente acontece em runtime

Quando `CLOUD_ONLY=True` (default):

1. `DOCS_DIR` → `/tmp/rc_void/docs` (diretório temporário inerte)
2. `ensure_subpastas()` → retorna `True` sem criar nada
3. `write_marker()` → caller guarda `if not CLOUD_ONLY` → nunca é chamado
4. `read_marker_id()` → busca em dir vazio → retorna `None`
5. `_migrar_pasta_se_preciso()` → `os.path.isdir(old_path)` = `False` → skipa
6. `resolve_cliente_path()` → varre dir vazio → `active=None, trash=None`
7. `salvar_cliente()` → retorna `(pk, pasta_string)` mas `pasta_string` é ignorado

**Conclusão**: A infraestrutura local inteira é **código inerte** — compilado mas
nunca executado em produção. É mantida apenas por inércia.

### As funções CLOUD-facing que usam o mesmo módulo

O `lixeira_service.py` importa `get_mandatory_subpastas` e `join_prefix` de
`subpastas_config.py`. Essas funções operam sobre strings e são usadas para criar
placeholders `.keep` no **Supabase Storage**, não no disco.

Estas funções podem ser relocadas ou mantidas no mesmo arquivo sem o resto do
baggage local.

---

## 5. RISCOS DE REMOÇÃO

### 5.1 Risco BAIXO — Remoção segura com mínimo cuidado

| Componente | Risco | Mitigação |
|------------|-------|-----------|
| `_ensure_live_folder_ready()` | **ZERO** | Dead code puro. Nenhum caller. |
| `ensure_subtree()` | **MÍNIMO** | Re-exportado em `__init__.py` mas sem callers externos. Remover do `__all__`. |
| `open_folder()` | **MÍNIMO** | O fluxo externo já foi removido. Sem callers ativos. |
| `safe_copy()` | **MÍNIMO** | Sem callers ativos (verificar se algum teste usa). |
| `SubpastaDialog` (subpastas_dialog.py) | **MÍNIMO** | Backup sem callers. Deletar arquivo inteiro. |
| `subpastas.yml` | **MÍNIMO** | Único consumidor ativo (`get_mandatory_subpastas`) usa tupla hardcoded, não o YAML. |
| `load_subpastas_config()` | **MÍNIMO** | Sem callers ativos. |

### 5.2 Risco MÉDIO — Requer ajuste coordenado

| Componente | Risco | Mitigação |
|------------|-------|-----------|
| `ensure_subpastas()` | **MÉDIO** | Chamado por `clientes_service` (guarded). Remover chamadas do service. Tests mocam esta função (`test_p1_regression.py`). |
| `write_marker()` / `read_marker_id()` | **MÉDIO** | `read_marker_id` é testado em `test_path_manager.py`. `write_marker` é usado pelo `clientes_service` (guarded). Ambos no `__init__.py` exports. |
| `_pasta_do_cliente()` | **MÉDIO** | Retorna `pasta` via `salvar_cliente()`. O editor usa `result[0]` (PK) — `result[1]` (pasta) **parece não ser consumido**, mas confirmar todos os callers. |
| `_migrar_pasta_se_preciso()` | **MÉDIO** | Chamado pelo `salvar_cliente()`. Já é no-op, mas precisa ser removido limpa e coordinate com os tests. |
| `resolve_cliente_path()` / `path_resolver.py` | **MÉDIO** | Re-exportado em `services/__init__.py`. Caller em `app_core.py` L164. |
| `path_manager.py` | **MÉDIO** | Testado em `test_path_manager.py` (funções locais como `ensure_subfolders`, `read_marker_id`, `write_marker_id`). |

### 5.3 Risco especial — Funções com DUPLA PERSONALIDADE

| Componente | Risco | Detalhe |
|------------|-------|---------|
| `subpastas_config.py` | **MÉDIO** | Contém funções LIVE (`get_mandatory_subpastas`, `join_prefix`) e funções DEAD (`load_subpastas_config`, `_flatten`, `_norm`). Não pode ser deletado inteiro. |
| `subfolders.py` | **NENHUM** | Todas as funções são LIVE (cloud ou pure). Manter intacto. |
| `safe_base_from_fields()` | **BAIXO** | Função pura (sem I/O). Usada por callers vestigiais e por `path_resolver` (vestigial). Mas é genérica o suficiente para manter como utility. |
| `DOCS_DIR` | **MÉDIO** | Importada por vários módulos. Remoção cascata. |

---

## 6. RECOMENDAÇÃO: **REMOVER PARCIALMENTE**

### Diagnóstico

A infraestrutura se divide em DOIS mundos:

1. **MUNDO LOCAL (disco)** — **MORTO**: `ensure_subpastas`, `ensure_subtree`, `ensure_dir`,
   `open_folder`, `safe_copy`, `write_marker`, `read_marker_id`, `_ensure_live_folder_ready`,
   `_pasta_do_cliente`, `_migrar_pasta_se_preciso`, `resolve_cliente_path`, `path_resolver.py`,
   `path_manager.py`, `load_subpastas_config`, `subpastas.yml`, `DOCS_DIR` (como path funcional),
   `SubpastaDialog` (backup).

2. **MUNDO CLOUD (Supabase)** — **VIVO**: `get_mandatory_subpastas`, `join_prefix`,
   `sanitize_subfolder_name`, `list_storage_subfolders`, `SubpastaDialog`
   (client_subfolder_prompt).

### Ação recomendada

**REMOVE PARTIALLY** — Remover toda infraestrutura local de disco (mundo 1), preservando
as funções cloud-facing (mundo 2).

### Preparação necessária antes da remoção

Antes de executar, validar:

- [ ] O resultado `pasta` de `salvar_cliente()` — confirmar que nenhum caller consome
      `result[1]`. Se confirmado, a assinatura pode ser simplificada para retornar
      apenas `int` (PK), ou manter a tupla com string vazia.
- [ ] `test_path_manager.py` — decidir: deletar (se testa apenas infra local) ou adaptar.
- [ ] `test_p1_regression.py` — remove mocks de `ensure_subpastas`/`write_marker`.
- [ ] Re-exportações em `file_utils/__init__.py` — limpar `__all__`.

---

## 7. PLANO DE EXECUÇÃO DA PRÓXIMA FASE

### ETAPA 1 — Limpar `subpastas_config.py`
- Deletar: `load_subpastas_config()`, `_flatten()`, `_norm()`, `MANDATORY_SUBPASTAS` docstring ref ao YAML.
- Manter: `get_mandatory_subpastas()`, `join_prefix()`, `MANDATORY_SUBPASTAS` tupla.
- Deletar: `subpastas.yml`.

### ETAPA 2 — Gutar `path_utils.py`
- Remover: `ensure_subpastas()`, `ensure_subtree()`, `ensure_dir()`, `open_folder()`, `safe_copy()`.
- Atualizar `__init__.py` e `__all__`.

### ETAPA 3 — Limpar `bytes_utils.py`
- Remover: `write_marker()`, `read_marker_id()`, `MARKER_NAME`, `migrate_legacy_marker()`,
  `get_marker_updated_at()`.
- Atualizar `__init__.py` e `__all__`.

### ETAPA 4 — Limpar `clientes_service.py`
- Remover: `_pasta_do_cliente()`, `_migrar_pasta_se_preciso()`.
- Simplificar `salvar_cliente()` — remover chamadas a essas funções.
- Remover imports: `DOCS_DIR`, `ensure_subpastas`, `write_marker`, `safe_base_from_fields`.
- Ajustar retorno: manter assinatura `tuple[int, str]` com `pasta=""` para
  compatibilidade ou mudar para `int` (mais limpo, mas requer ajustes em callers).

### ETAPA 5 — Remover dead code em `app_core.py`
- Deletar `_ensure_live_folder_ready()` inteira.
- Remover imports de `DOCS_DIR`, `ensure_subpastas`, `write_marker`, `load_subpastas_config`.

### ETAPA 6 — Remover/simplificar `path_resolver.py` e `path_manager.py`
- Avaliar se há uso cloud legítimo de `resolve_unique_path` via `app_core.py` L164.
  Se o caller já é vestigial ⇒ deletar ambos os módulos.
- Se houver callers vivos ⇒ simplificar para não depender de disco local.
- Atualizar `services/__init__.py`.

### ETAPA 7 — Deletar backup morto
- Deletar `src/ui/subpastas_dialog.py` (backup sem callers).

### ETAPA 8 — Limpar hotfix e paths
- Avaliar se `rc_hotfix_no_local_fs.py` ainda faz sentido após remoção.
- Simplificar `paths.py` — `DOCS_DIR` pode virar constante vazia ou ser removida.
- `ensure_directories()` → pode virar no-op permanente.

### ETAPA 9 — Ajustar testes
- `test_path_manager.py` — deletar ou reescrever.
- `test_p1_regression.py` — remover mocks de `ensure_subpastas`/`write_marker`.
- Rodar 949+ tests e validar 0 falhas.

### ETAPA 10 — Validação final
- `grep` confirmando ausência de referências residuais.
- Verificar que `lixeira_service.py` continua funcionando (testes de restore).
- Verificar que uploads Supabase continuam funcionando.

---

## APÊNDICE A — Evidência: `CLOUD_ONLY=True` como default

```python
# src/config/environment.py L51
def cloud_only_default() -> bool:
    return env_bool("RC_NO_LOCAL_FS", True)   # ← DEFAULT = True

# src/config/paths.py L21
CLOUD_ONLY: bool = cloud_only_default()

# src/config/paths.py L32-41
if CLOUD_ONLY:
    TMP_BASE = Path(tempfile.gettempdir()) / "rc_void"
    DOCS_DIR: Path = TMP_BASE / "docs"        # ← /tmp/rc_void/docs
```

## APÊNDICE B — Evidência: `_ensure_live_folder_ready` = dead code

```
grep "_ensure_live_folder_ready" src/** → 1 match (a definição, L196)
```

Zero callers em qualquer lugar do codebase.

## APÊNDICE C — Evidência: `pasta` retornada por `salvar_cliente()` não é consumida

```python
# src/modules/clientes/ui/views/_editor_data_mixin.py L544
result = clientes_service.salvar_cliente_a_partir_do_form(row, valores)
# ...
cliente_id_salvo = int(result[0])  # ← Usa APENAS result[0] (PK)
# result[1] (pasta) nunca é referenciado após esta linha
```

## APÊNDICE D — Resumo quantitativo

| Categoria | Qtd funções/módulos | Ação |
|-----------|---------------------|------|
| DEAD (0 callers) | 1 | Deletar |
| VESTIGIAL (no-op) | 14 | Remover |
| LIVE-CLOUD | 4 | Preservar |
| LIVE-PURE | 2 | Preservar (opcionalmente relocar) |
| SUPPORT (infra) | 3 | Limpar parcialmente |
| **Total analisados** | **24** | — |

**Estimativa de código removível**: ~600-800 linhas de produção + ~200 linhas de testes.
