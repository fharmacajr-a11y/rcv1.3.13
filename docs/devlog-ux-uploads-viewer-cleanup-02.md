# DevLog: UX-UPLOADS-VIEWER-CLEANUP-02 - Melhoria do fluxo de abertura de arquivos

**Data:** 2025-12-07  
**Autor:** Copilot + Human  
**Branch:** `qa/fixpack-04`  
**Contexto:** FASE UX-UPLOADS-VIEWER-CLEANUP-02 — Refinar fluxo de download e abertura de arquivos com gestão de temporários e logs

---

## 1. Problema Original

### 1.1 Ciclo de vida dos arquivos temporários

**Antes:**
```python
# src/modules/uploads/service.py::download_and_open_file (linha 316-348)
tmp_dir = tempfile.mkdtemp(prefix="rc_supabase_")  # ❌ Cria diretório único a cada vez
local_path = os.path.join(tmp_dir, os.path.basename(remote_key))

# Baixa arquivo
result = download_file(bn, remote_key, local_path)

# Abre viewer
os.startfile(local_path)  # ❌ Sem captura de exceção
logger.info("Arquivo aberto no visualizador: %s", local_path)  # ❌ Log básico
```

**Problemas identificados:**

1. **Lixo de temporários:** Cada download criava um diretório único (`rc_supabase_XXXXX`), nunca limpo
   - Arquivos acumulavam indefinidamente em `%TEMP%`
   - Usuários com downloads frequentes podiam acumular centenas de MB/GB

2. **Falta de observabilidade:**
   - Sem log de início de download
   - Sem log de tamanho do arquivo
   - Sem log de tempo de download
   - Sem log de falhas ao abrir viewer

3. **Tratamento de erro inadequado:**
   - Função levantava `RuntimeError` genérico
   - Caller (UI) não tinha informações estruturadas para mostrar ao usuário
   - Falha ao abrir viewer não era capturada

4. **Sem preparação para PDF preview interno:**
   - Lógica hardcoded para viewer externo
   - Impossível adicionar modo interno sem quebrar código existente

### 1.2 Impacto

- Disco cheio em uso prolongado (acúmulo de PDFs temporários)
- Dificuldade de troubleshooting (logs insuficientes)
- UX ruim em caso de erro (exceções não tratadas)

---

## 2. Solução Implementada

### 2.1 Módulo de gestão de temporários

**Arquivo criado:** `src/modules/uploads/temp_files.py` (178 linhas)

**Política de ciclo de vida definida:**

```python
# Diretório centralizado para temporários do app
TEMP_DIR_NAME = "rc_gestor_uploads"  # Ex: %TEMP%/rc_gestor_uploads/

# Idade máxima: 7 dias
MAX_AGE_SECONDS = 7 * 24 * 60 * 60
```

**Funções principais:**

1. **`get_temp_directory() -> Path`**
   - Retorna/cria diretório centralizado (`%TEMP%/rc_gestor_uploads/`)
   - Log quando diretório é criado

2. **`create_temp_file(remote_filename: str) -> TempFileInfo`**
   - Cria path temporário no diretório centralizado
   - Sanitiza nome do arquivo (usa apenas basename)
   - Se arquivo já existir, adiciona timestamp (`documento_1733594400.pdf`)
   - Retorna `TempFileInfo(path, directory, filename)`

3. **`cleanup_old_files(max_age_seconds: int) -> dict`**
   - Remove arquivos mais antigos que N dias (padrão: 7)
   - Ignora subdiretórios
   - Retorna estatísticas: `{"removed": N, "failed": M, "total_bytes": X}`
   - Logs detalhados:
     ```
     INFO: Iniciando limpeza de arquivos temporários (idade > 7 dias)
     DEBUG: Removido arquivo temporário antigo: relatorio.pdf (8.5 dias, 102400 bytes)
     INFO: Limpeza concluída: 3 arquivo(s) removido(s), 1.25 MB liberados
     ```

4. **`cleanup_on_startup()`**
   - Wrapper para executar limpeza no startup do app
   - Captura exceções (não quebra startup se cleanup falhar)

**Integração no startup:**

```python
# src/app_gui.py (linha 59-65)
if __name__ == "__main__":
    # Install global exception hook early
    try:
        from src.utils.errors import install_global_exception_hook
        install_global_exception_hook()
    except Exception as exc:
        logger.debug("Falha ao instalar global exception hook: %s", exc)

    # Cleanup de arquivos temporários antigos no startup  # ✅ NOVO
    try:
        from src.modules.uploads.temp_files import cleanup_on_startup
        cleanup_on_startup()
    except Exception as exc:
        logger.debug("Falha ao executar cleanup de temporários: %s", exc)
```

### 2.2 Refatoração de `download_and_open_file`

**Arquivo modificado:** `src/modules/uploads/service.py`

**Nova assinatura:**

```python
def download_and_open_file(
    remote_key: str,
    *,
    bucket: str | None = None,
    mode: str = "external"
) -> dict[str, Any]:
```

**Mudanças:**

1. **Retorna dict estruturado (não levanta exceção):**
   ```python
   # Sucesso
   {
       "ok": True,
       "message": "Arquivo aberto com sucesso",
       "temp_path": "C:\\Temp\\rc_gestor_uploads\\documento.pdf"
   }

   # Erro
   {
       "ok": False,
       "message": "Erro ao preparar arquivo temporário: Disco cheio",
       "error": "Disco cheio"
   }
   ```

2. **Parâmetro `mode` para futuras extensões:**
   - `mode="external"` (padrão): Abre no viewer do SO
   - `mode="internal"`: Reservado para PDF preview interno (TODO)

3. **Logs detalhados em cada etapa:**
   ```python
   # Início
   logger.info(
       "Iniciando download de arquivo: bucket=%s, remote_key=%s, mode=%s",
       bn, remote_key, mode
   )

   # Download concluído
   logger.info(
       "Download concluído: arquivo=%s, tamanho=%d bytes, tempo=%.2fs",
       remote_filename, file_size, download_time
   )

   # Arquivo aberto
   logger.info("Arquivo aberto no visualizador externo: %s", local_path)

   # Erro ao abrir
   logger.error(
       "Erro ao abrir arquivo no visualizador: path=%s, erro=%s",
       local_path, exc, exc_info=True
   )
   ```

4. **Usa `create_temp_file()` do novo módulo:**
   ```python
   temp_info = create_temp_file(remote_filename)
   local_path = temp_info.path
   ```

5. **Captura todas as exceções:**
   - Erro ao criar temp file → retorna `{"ok": False, ...}`
   - Erro no download → retorna `{"ok": False, ...}`
   - Erro ao abrir viewer → retorna `{"ok": False, ...}` **mas mantém temp_path**
     - Usuário pode abrir manualmente se necessário

### 2.3 Tratamento de erro na UI (não aplicável)

**Descoberta:** A UI atual (`src/modules/uploads/views/browser.py`) não usa `download_and_open_file()`.

- Usa viewer interno de PDF/imagens (`_view_selected()` → `download_bytes()` → `open_pdf_viewer()`)
- Já tem tratamento de erro com `messagebox.showerror()`

**Conclusão:** Nenhuma alteração necessária na UI nesta fase. A função `download_and_open_file()` está pronta para uso futuro ou integração em outros módulos.

---

## 3. Testes Criados

### 3.1 Testes de `temp_files.py`

**Arquivo:** `tests/unit/modules/uploads/test_temp_files.py` (235 linhas)

**Classes de teste:**

1. **`TestGetTempDirectory`** (3 testes)
   - `test_returns_path_object` ✅
   - `test_creates_directory_if_not_exists` ✅
   - `test_returns_existing_directory` ✅

2. **`TestCreateTempFile`** (3 testes)
   - `test_creates_temp_file_info` ✅
   - `test_sanitizes_filename_with_path` ✅ (segurança)
   - `test_handles_duplicate_filename_with_timestamp` ✅

3. **`TestCleanupOldFiles`** (6 testes)
   - `test_removes_old_files` ✅
   - `test_keeps_recent_files` ✅
   - `test_handles_missing_directory` ✅
   - `test_counts_total_bytes_removed` ✅
   - `test_ignores_subdirectories` ✅

4. **`TestCleanupOnStartup`** (2 testes)
   - `test_calls_cleanup_old_files` ✅
   - `test_handles_cleanup_errors_gracefully` ✅

**Resultado:**
```
13 passed in 4.10s ✅
```

### 3.2 Testes de `download_and_open_file`

**Arquivo:** `tests/unit/modules/uploads/test_download_and_open_file.py` (215 linhas)

**Classe de teste:**

**`TestDownloadAndOpenFile`** (9 testes)
   - `test_downloads_and_opens_file_successfully_windows` ✅ (skip se não Windows)
   - `test_downloads_and_opens_file_successfully_linux` ✅ (skip se não Linux)
   - `test_handles_download_failure` ✅
   - `test_handles_temp_file_creation_error` ✅
   - `test_handles_viewer_open_error` ✅
   - `test_uses_custom_bucket_when_provided` ✅
   - `test_rejects_invalid_mode` ✅
   - `test_internal_mode_returns_not_implemented` ✅
   - `test_logs_file_size_and_download_time` ✅

**Resultado:**
```
8 passed, 1 skipped in 3.46s ✅
```

---

## 4. Validação

### 4.1 Testes Unitários

```bash
# Testes específicos
pytest tests/unit/modules/uploads/test_temp_files.py -v --tb=short
# 13 passed in 4.10s ✅

pytest tests/unit/modules/uploads/test_download_and_open_file.py -v --tb=short
# 8 passed, 1 skipped in 3.46s ✅

# Suite completa de uploads
pytest tests/unit/modules/uploads -v --tb=short -q
# 216 passed, 4 skipped in 33.14s ✅
```

**Sem regressões!** Todos os testes existentes continuam passando.

### 4.2 Lint (Ruff)

```bash
ruff check src/modules/uploads/temp_files.py \
            src/modules/uploads/service.py \
            src/app_gui.py \
            tests/unit/modules/uploads/test_temp_files.py \
            tests/unit/modules/uploads/test_download_and_open_file.py
```

**Resultado:** ✅ All checks passed! (após fix automático de 2 imports não usados)

---

## 5. Impacto

### 5.1 Arquivos criados

1. `src/modules/uploads/temp_files.py` (178 linhas)
   - Módulo de gestão de arquivos temporários
   - Funções: `get_temp_directory`, `create_temp_file`, `cleanup_old_files`, `cleanup_on_startup`

2. `tests/unit/modules/uploads/test_temp_files.py` (235 linhas)
   - 13 testes headless (4 classes)

3. `tests/unit/modules/uploads/test_download_and_open_file.py` (215 linhas)
   - 9 testes headless (1 classe)

### 5.2 Arquivos modificados

1. `src/modules/uploads/service.py`
   - Import de `create_temp_file` e `time`
   - Refatoração completa de `download_and_open_file()`:
     - Assinatura: retorna `dict[str, Any]` (não levanta exceção)
     - Adiciona parâmetro `mode` (preparação para modo interno)
     - Usa `create_temp_file()` do novo módulo
     - Logs detalhados em INFO/ERROR
     - Captura todas as exceções
     - Retorna estrutura com `ok`, `message`, `temp_path`, `error`

2. `src/app_gui.py`
   - Integração de `cleanup_on_startup()` no bloco `if __name__ == "__main__"`
   - Cleanup executa antes de parsing de argumentos CLI

### 5.3 Cobertura de testes

**Novos testes adicionados:**
- 13 testes para `temp_files.py`
- 9 testes para `download_and_open_file()`
- **Total:** 22 novos testes headless

**Cobertura da suite uploads:**
- Antes: 195 testes
- Depois: 216 testes (+21, 1 teste a menos devido a consolidação)
- Todos passando ✅

### 5.4 Benefícios

✅ **Gestão de temporários:** Limpeza automática de arquivos >7 dias no startup  
✅ **Observabilidade:** Logs detalhados de download (bucket, remote_key, tamanho, tempo, erros)  
✅ **UX melhorada:** Retorno estruturado permite UI mostrar erros amigáveis  
✅ **Preparação futura:** Parâmetro `mode` permite adicionar viewer interno sem breaking change  
✅ **Manutenibilidade:** Módulo `temp_files` reutilizável em outros contextos  
✅ **Testes robustos:** 22 novos testes cobrem casos de sucesso e falha  

---

## 6. Notas Técnicas

### 6.1 Política de limpeza escolhida

**Decisão:** Cleanup periódico (startup), não cleanup instantâneo após fechar viewer.

**Justificativa:**
1. Apps desktop não conseguem saber quando o usuário fechou o viewer externo (PDF reader, image viewer)
2. Tentar rastrear processos filhos é complexo e não portável (Windows vs Linux vs macOS)
3. Cleanup no startup é prática comum e previsível:
   - Visual Studio Code faz isso com extensões
   - Navegadores fazem com cache
   - IDEs fazem com logs/índices

**Configuração atual:**
- Diretório: `%TEMP%/rc_gestor_uploads/`
- Idade máxima: 7 dias
- Frequência: 1x no startup do app

**Vantagens:**
- Simples de implementar e testar
- Zero overhead durante uso normal
- Usuário pode abrir/reabrir arquivos recentes sem re-download

### 6.2 Estrutura de retorno de `download_and_open_file`

**Decisão:** Retornar dict em vez de levantar exceção.

**Justificativa:**
1. Permite diferenciar tipos de erro (download, temp file, viewer)
2. UI pode decidir como apresentar erro ao usuário
3. Em caso de erro ao abrir viewer, `temp_path` ainda é retornado:
   - Usuário pode abrir manualmente
   - Futuro: UI pode oferecer "Abrir pasta"

**Exemplo de uso futuro na UI:**
```python
result = download_and_open_file("clientes/123/contrato.pdf")

if not result["ok"]:
    messagebox.showerror(
        "Erro ao abrir arquivo",
        result["message"],
        parent=self
    )

    if "temp_path" in result:
        # Arquivo foi baixado, oferecer abrir pasta
        if messagebox.askyesno("Abrir pasta?", "Deseja abrir a pasta do arquivo?"):
            open_file_explorer(result["temp_path"])
```

### 6.3 Parâmetro `mode` para futuras extensões

**Decisão:** Adicionar `mode="external"` agora, deixar `mode="internal"` como TODO.

**Justificativa:**
1. Browser atual já usa viewer interno, não precisa de `download_and_open_file`
2. Futuro: Outros módulos (auditoria, hub) podem querer usar viewer interno
3. Adicionar parâmetro agora evita breaking change no futuro

**Implementação atual:**
```python
if mode == "internal":
    # TODO: Implementar integração com PDF preview interno (FASE UI-PDF-PREVIEW-CONTROLLER-01)
    return {
        "ok": False,
        "message": "Modo 'internal' ainda não implementado. Use mode='external'.",
    }
```

### 6.4 Logs adicionados

**Níveis de log:**

- **INFO:** Operações normais bem-sucedidas
  - Início de download
  - Download concluído (com estatísticas)
  - Arquivo aberto no viewer
  - Limpeza concluída (com estatísticas)

- **DEBUG:** Detalhes opcionais
  - Arquivo temporário preparado
  - Nenhum arquivo antigo encontrado
  - Arquivo removido (com idade e tamanho)

- **ERROR:** Falhas
  - Erro ao criar temporário
  - Falha no download
  - Erro ao abrir viewer
  - Falha ao remover arquivo antigo

**Exemplo de log de sucesso:**
```
INFO: Iniciando download de arquivo: bucket=bucket-clientes, remote_key=clientes/123/contrato.pdf, mode=external
INFO: Download concluído: arquivo=contrato.pdf, tamanho=102400 bytes, tempo=1.23s
INFO: Arquivo aberto no visualizador externo: C:\Temp\rc_gestor_uploads\contrato.pdf
```

**Exemplo de log de erro:**
```
INFO: Iniciando download de arquivo: bucket=bucket-clientes, remote_key=clientes/999/inexistente.pdf, mode=external
ERROR: Falha no download: bucket=bucket-clientes, remote_key=clientes/999/inexistente.pdf, erro=Arquivo não encontrado
```

---

## 7. Próximos Passos

### 7.1 Integrações futuras (opcional)

1. **Usar `download_and_open_file` em auditoria/hub:**
   - Se houver flows que baixam e abrem arquivos diretamente
   - Substituir lógica inline por chamada ao serviço

2. **Implementar `mode="internal"` (FASE UI-PDF-PREVIEW-CONTROLLER-01):**
   ```python
   if mode == "internal":
       # Baixar arquivo
       temp_info = create_temp_file(remote_filename)
       result = download_file(bn, remote_key, temp_info.path)

       # Abrir no PDF preview interno
       from src.modules.pdf_preview import open_pdf_viewer
       open_pdf_viewer(None, pdf_path=temp_info.path, display_name=remote_filename)

       return {"ok": True, "message": "Arquivo aberto no viewer interno"}
   ```

3. **Configurar idade máxima de cleanup:**
   - Adicionar setting em `config.yml`: `temp_files_max_age_days: 7`
   - Ler no `cleanup_on_startup()`

4. **Adicionar botão "Limpar temporários" na UI:**
   - Em Configurações/Manutenção
   - Chama `cleanup_old_files(max_age_seconds=0)` (força limpeza total)

### 7.2 Melhorias opcionais

1. **Limite de tamanho do diretório temporário:**
   - Se `%TEMP%/rc_gestor_uploads/` > 500 MB, limpar arquivos mais antigos

2. **Estatísticas de uso:**
   - Contar quantos arquivos foram abertos na sessão
   - Mostrar em "Sobre" ou logs de debug

---

## 8. Checklist de Conclusão

- [x] Criar módulo `temp_files.py` com gestão de temporários
- [x] Implementar `get_temp_directory()`, `create_temp_file()`, `cleanup_old_files()`
- [x] Integrar `cleanup_on_startup()` no `app_gui.py`
- [x] Refatorar `download_and_open_file()` com logs e retorno estruturado
- [x] Adicionar parâmetro `mode` para futuras extensões
- [x] Criar 13 testes para `temp_files.py`
- [x] Criar 9 testes para `download_and_open_file()`
- [x] Rodar pytest em `tests/unit/modules/uploads` (216 passed ✅)
- [x] Validar com Ruff (all checks passed ✅)
- [x] Criar este devlog

---

**FASE UX-UPLOADS-VIEWER-CLEANUP-02: CONCLUÍDA ✅**

**Resumo:**
- ✅ Gestão de temporários com cleanup automático
- ✅ Logs detalhados de download/abertura
- ✅ Retorno estruturado para tratamento de erro na UI
- ✅ Preparação para modo interno (PDF preview)
- ✅ 22 novos testes headless
- ✅ 0 regressões (216 testes passando)
