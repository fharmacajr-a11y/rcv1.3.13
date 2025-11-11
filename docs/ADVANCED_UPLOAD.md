# Upload Avançado - Documentação Técnica

## 📊 Visão Geral

Implementação completa de sistema avançado de upload com:
- **(A) Pré-check de duplicatas** com diálogo de escolha (Pular/Substituir/Renomear)
- **(B) Cancelamento com reversão** opcional dos arquivos já enviados
- **(C) Finalização suave** (fecha modal antes de recarregar browser)
- **(D) Progresso por bytes** com ETA aprimorado (mm:ss ou HH:MM:SS)

---

## 🎯 Funcionalidades Implementadas

### ✅ (A) Pré-check de Duplicatas

**Fluxo**:
1. Após pré-scan dos arquivos, lista nomes existentes no Storage via `_list_existing_names()`
2. Calcula duplicatas: `file_names & existing_names`
3. Se duplicatas encontradas, mostra `DuplicatesDialog` com 3 opções:
   - **⊘ Pular** (padrão): Não envia arquivos que já existem
   - **♻ Substituir**: Sobrescreve com `upsert=True`
   - **✏ Renomear**: Adiciona sufixo `(2)`, `(3)`, ... usando `_next_copy_name()`
4. Monta `_UploadPlan` para cada arquivo com `dest_name` e `upsert` corretos

**Exemplo de uso**:
```python
# Listar arquivos existentes
existing = self._list_existing_names("rc-docs", "org/client/GERAL/Auditoria")

# Calcular duplicatas
duplicates = {"doc.pdf", "foto.jpg"}

# Aplicar estratégia "rename"
new_name = _next_copy_name("doc.pdf", existing)
# Resultado: "doc (2).pdf"
```

---

### ✅ (B) Cancelamento com Reversão

**Fluxo**:
1. Durante upload, mantém lista `uploaded_paths` com caminhos completos dos arquivos enviados
2. A cada iteração, verifica `self._cancel_flag` antes de upload
3. Se cancelado, chama `_ask_rollback(uploaded_paths, bucket)`
4. Usuário escolhe:
   - **SIM**: Remove arquivos via `storage.remove()` (em lotes de 1000)
   - **NÃO**: Mantém arquivos já enviados

**Thread-safe**: Remoção em thread separada + callbacks via `after()`

**Exemplo**:
```python
uploaded_paths = [
    "org/client/GERAL/Auditoria/doc1.pdf",
    "org/client/GERAL/Auditoria/doc2.pdf"
]

# Remover em lotes
batch_size = 1000
for i in range(0, len(uploaded_paths), batch_size):
    batch = uploaded_paths[i:i + batch_size]
    storage.from_("rc-docs").remove(batch)
```

---

### ✅ (C) Finalização Suave

**Antes**:
```python
self._close_busy()
# Browser abre imediatamente, pode travar se modal ainda visível
open_files_browser(...)
```

**Depois**:
```python
# FASE 1: Fechar modal primeiro
self._close_busy()

# FASE 2: Aguardar 50ms, depois abrir browser
self.after(50, _refresh_browser)
```

**Benefícios**:
- Modal fecha completamente antes de browser abrir
- Evita travamentos de UI
- Transição suave entre janelas

---

### ✅ (D) Progresso por Bytes

**Antes**:
```
47% — 23/50 itens
00:00:12 restantes @ 3.2 MB/s
```

**Depois**:
```
47% — 23/50 itens • 12.5 MB / 26.8 MB
ETA ~ 05:32 @ 3.2 MB/s
```

**Melhorias**:
- **Bytes enviados/total**: `12.5 MB / 26.8 MB`
- **ETA adaptativo**: `mm:ss` se < 1h, senão `HH:MM:SS`
- **Formato legível**: `_fmt_bytes()` usa KB, MB, GB automaticamente

---

## 🔧 Alterações Técnicas

### 1. Novos Dataclasses

#### `_UploadPlan`
```python
@dataclass
class _UploadPlan:
    source_path: Path  # Caminho local (ex: Path("subdir/doc.pdf"))
    dest_name: str     # Nome destino (ex: "subdir/doc (2).pdf")
    upsert: bool       # True = substituir, False = erro se existir
    file_size: int     # Tamanho em bytes
```

**Uso**:
```python
# Não duplicado
plan = _UploadPlan(Path("doc.pdf"), "doc.pdf", upsert=False, file_size=1024)

# Duplicado - Substituir
plan = _UploadPlan(Path("doc.pdf"), "doc.pdf", upsert=True, file_size=1024)

# Duplicado - Renomear
plan = _UploadPlan(Path("doc.pdf"), "doc (2).pdf", upsert=False, file_size=1024)
```

---

### 2. Helpers Globais

#### `_next_copy_name()`
```python
def _next_copy_name(name: str, existing: set[str]) -> str:
    """
    Gera nome com sufixo (2), (3), ... evitando colisão.

    Example:
        >>> _next_copy_name("doc.pdf", {"doc.pdf", "doc (2).pdf"})
        'doc (3).pdf'
    """
```

**Algoritmo**:
1. Se `name` não existe, retorna original
2. Separa stem e suffix: `doc.pdf` → `doc` + `.pdf`
3. Tenta `doc (2).pdf`, `doc (3).pdf`, ... até encontrar disponível

---

### 3. Métodos da Classe

#### `_list_existing_names()`
```python
def _list_existing_names(self, bucket: str, prefix: str) -> set[str]:
    """
    Lista nomes de arquivos existentes no Storage (com paginação).

    Args:
        bucket: Nome do bucket (ex: "rc-docs")
        prefix: Caminho da pasta (ex: "org/client/GERAL/Auditoria")

    Returns:
        Set de nomes (ex: {"doc.pdf", "foto.jpg"})
    """
```

**Paginação automática**:
- Usa `limit=1000, offset=0`
- Loop até retornar < 1000 itens
- Retorna set único de nomes

---

#### `_ask_rollback()`
```python
def _ask_rollback(self, uploaded_paths: list[str], bucket: str) -> None:
    """
    Pergunta ao usuário se deseja reverter arquivos após cancelamento.

    Args:
        uploaded_paths: Lista de caminhos completos
        bucket: Nome do bucket
    """
```

**Fluxo**:
1. Se `uploaded_paths` vazio: apenas avisa "Nenhum arquivo enviado"
2. Mostra `messagebox.askyesno()` com contagem
3. Se SIM: remove em thread + callback de sucesso/erro
4. Se NÃO: avisa "Arquivos mantidos"

---

#### `_fmt_bytes()`
```python
def _fmt_bytes(self, bytes_val: int) -> str:
    """Formata bytes em KB/MB/GB."""
```

**Exemplos**:
- `500` → `"500 B"`
- `1536` → `"1.5 KB"`
- `1_572_864` → `"1.5 MB"`
- `1_073_741_824` → `"1.0 GB"`

---

#### `_progress_update_ui()` (atualizado)
```python
def _progress_update_ui(self, state: _ProgressState, alpha: float = 0.2) -> None:
    """Atualiza UI com % por bytes, MB/s e ETA adaptativo."""
```

**Novo formato de ETA**:
```python
if eta_sec < 3600:
    eta_str = f"{m:02d}:{s:02d}"  # "05:32"
else:
    eta_str = f"{h:02d}:{m:02d}:{s:02d}"  # "01:05:32"
```

**Novo label de status**:
```python
status_text = f"{pct:.0f}% — {done_files}/{total_files} itens • {done_bytes_fmt} / {total_bytes_fmt}"
# "47% — 23/50 itens • 12.5 MB / 26.8 MB"
```

---

### 4. Refatoração `_worker_upload()`

**6 Fases**:

#### Fase 1: Pré-scan + Montagem de Lista
```python
files_to_upload: list[tuple[str, int]] = []  # (rel_path, file_size)

# ZIP: ler metadados
for info in zf.infolist():
    files_to_upload.append((info.filename, info.file_size))

# RAR/7Z: extrair e listar
extract_archive(path, tmpdir)
for f in Path(tmpdir).rglob("*"):
    files_to_upload.append((f.relative_to(tmpdir).as_posix(), f.stat().st_size))
```

#### Fase 2: Pré-check de Duplicatas
```python
existing_names = self._list_existing_names(bucket, base_prefix)
file_names = {Path(rel).name for rel, _ in files_to_upload}
duplicates_names = file_names & existing_names

if duplicates_names:
    # Mostrar diálogo (thread-safe)
    dialog_result = {"strategy": None}

    def _show_dup_dialog():
        dlg = DuplicatesDialog(self, len(duplicates_names), sorted(duplicates_names))
        self.wait_window(dlg)
        dialog_result["strategy"] = dlg.strategy

    self.after(0, _show_dup_dialog)

    # Aguardar resposta (polling)
    while dialog_result["strategy"] is None:
        time.sleep(0.05)
```

#### Fase 3: Montar Plano de Upload
```python
for rel, file_size in files_to_upload:
    file_name = Path(rel).name
    is_dup = file_name in duplicates_names

    if is_dup and strategy == "skip":
        continue  # Não adiciona ao plano
    elif is_dup and strategy == "replace":
        plan = _UploadPlan(Path(rel), rel, upsert=True, file_size)
    elif is_dup and strategy == "rename":
        new_name = _next_copy_name(file_name, existing_names)
        existing_names.add(new_name)
        plan = _UploadPlan(Path(rel), new_rel_with_new_name, upsert=False, file_size)
    else:
        plan = _UploadPlan(Path(rel), rel, upsert=False, file_size)

    upload_plans.append(plan)
```

#### Fase 4: Upload com Tracking
```python
state = _ProgressState()
state.total_files = len(upload_plans)
state.total_bytes = sum(p.file_size for p in upload_plans)

for plan in upload_plans:
    if self._cancel_flag:
        break

    # Upload
    storage.upload(dest, data, {"upsert": str(plan.upsert).lower()})

    # Tracking
    uploaded_paths.append(dest)
    state.done_files += 1
    state.done_bytes += plan.file_size

    # UI update
    self.after(0, lambda s=state: self._progress_update_ui(s))
```

#### Fase 5: Verificar Cancelamento
```python
if self._cancel_flag:
    self.after(0, lambda: self._ask_rollback(uploaded_paths, bucket))
    return
```

#### Fase 6: Finalização
```python
self.after(0, lambda: self._busy_done(state.done_files, fail, ...))
```

---

## 🎨 UI: DuplicatesDialog

**Layout**:
```
┌─────────────────────────────────────────────┐
│ Duplicatas Detectadas                   [×] │
├─────────────────────────────────────────────┤
│ Encontrados 15 arquivo(s) duplicado(s).     │
│ Escolha como proceder:                      │
│                                             │
│ ┌─ Amostra (até 20 nomes) ──────────────┐  │
│ │ • documento.pdf                        │  │
│ │ • planilha.xlsx                        │  │
│ │ • foto.jpg                             │  │
│ │ ...                                    ↕  │
│ └────────────────────────────────────────┘  │
│                                             │
│ ┌─ Estratégia ───────────────────────────┐  │
│ │ (•) Pular duplicatas (não envia)       │  │
│ │ ( ) Substituir duplicatas (sobrescreve)│  │
│ │ ( ) Renomear com sufixo (arquivo (2))  │  │
│ └────────────────────────────────────────┘  │
│                                             │
│          [   OK   ]  [ Cancelar ]           │
└─────────────────────────────────────────────┘
```

**Características**:
- Dimensões: 500x450
- Text widget scrollable (até 20 nomes)
- Radiobuttons com ícones (⊘, ♻, ✏)
- Padrão: "skip" (recomendado)
- Atalhos: Enter (OK), Escape (Cancelar)
- Modal + grab_set (bloqueia pai)

---

## 📊 Testes Implementados

### `test_upload_advanced.py`

**5 testes automatizados**:

1. **test_next_copy_name**: Valida geração de sufixos
   - Nome não existe → retorna original
   - Nome existe → gera `(2)`
   - `(2)` existe → gera `(3)`
   - Múltiplos sufixos

2. **test_upload_plan_dataclass**: Valida `_UploadPlan`
   - Campos corretos
   - `upsert=True` e `upsert=False`

3. **test_progress_state**: Valida `_ProgressState`
   - Tracking de files e bytes
   - Cálculo de % correto
   - EMA de velocidade

4. **test_fmt_bytes**: Valida formatação
   - B, KB, MB, GB
   - Precisão de 1 casa decimal

5. **test_fmt_eta**: Valida HH:MM:SS
   - 0s → `"00:00:00"`
   - 65s → `"00:01:05"`
   - 3665s → `"01:01:05"`

**Execução**:
```bash
python scripts/test_upload_advanced.py
```

**Resultado esperado**:
```
✅ TODOS OS TESTES PASSARAM
  ✓ _next_copy_name gera sufixos corretamente
  ✓ _UploadPlan dataclass funciona
  ✓ _ProgressState tracking preciso
  ✓ _fmt_bytes formata B/KB/MB/GB
  ✓ _fmt_eta formata HH:MM:SS
```

---

### `demo_duplicates_dialog.py`

**Demo interativo da UI**:
- Simula 15 arquivos duplicados
- Mostra diálogo real
- Imprime estratégia escolhida

**Execução**:
```bash
python scripts/demo_duplicates_dialog.py
```

---

## 🔬 Fórmulas Matemáticas

### 1. Porcentagem por Bytes
$$\text{pct} = \left(\frac{\text{done\_bytes}}{\text{total\_bytes}}\right) \times 100$$

### 2. EMA de Velocidade
$$\text{ema\_bps}_t = \alpha \cdot \text{instant\_bps}_t + (1 - \alpha) \cdot \text{ema\_bps}_{t-1}$$

Onde $\alpha = 0.2$ (suavização de 20%)

### 3. ETA
$$\text{eta\_sec} = \frac{\text{total\_bytes} - \text{done\_bytes}}{\text{ema\_bps}}$$

### 4. Conversão de Bytes
$$\text{MB} = \frac{\text{bytes}}{1{,}048{,}576}$$
$$\text{KB} = \frac{\text{bytes}}{1{,}024}$$

---

## 📝 Exemplos de Uso

### Cenário 1: Upload com Duplicatas (Pular)
```
1. Usuário seleciona arquivo.zip com 50 arquivos
2. Pré-scan detecta 10 duplicatas
3. Diálogo mostra: "Encontrados 10 arquivo(s) duplicado(s)"
4. Usuário escolhe: "⊘ Pular duplicatas"
5. Upload envia apenas 40 arquivos novos
6. Progresso: "100% — 40/40 itens • 15.2 MB / 15.2 MB"
```

### Cenário 2: Upload com Duplicatas (Renomear)
```
1. Arquivo.zip tem "doc.pdf" (já existe no Storage)
2. Usuário escolhe: "✏ Renomear duplicatas"
3. Plano: dest_name = "doc (2).pdf", upsert = False
4. Upload: "doc.pdf" → "org/.../doc (2).pdf"
5. Nenhum arquivo sobrescrito
```

### Cenário 3: Cancelamento com Reversão
```
1. Upload de 100 arquivos inicia
2. Após 30 arquivos, usuário clica "Cancelar"
3. Diálogo: "30 arquivo(s) já foram enviados. Remover?"
4. Usuário clica "SIM"
5. Thread remove 30 arquivos do Storage
6. Mensagem: "30 arquivo(s) removido(s) com sucesso"
```

### Cenário 4: Finalização Suave
```
1. Upload de 50 arquivos completo
2. Modal fecha (self._close_busy())
3. Aguarda 50ms (self.after(50, ...))
4. Browser abre mostrando arquivos enviados
5. Transição suave, sem travamentos
```

---

## 🚀 Próximos Passos (Sugestões)

### 1. Validação de MIME Types
Detectar e alertar sobre tipos de arquivo não permitidos:
```python
ALLOWED_MIMES = {".pdf", ".xlsx", ".docx", ".jpg", ".png"}
if Path(file).suffix not in ALLOWED_MIMES:
    fail.append((file, "Tipo de arquivo não permitido"))
```

### 2. Limite de Tamanho
Rejeitar arquivos muito grandes:
```python
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
if file_size > MAX_FILE_SIZE:
    fail.append((file, f"Arquivo muito grande: {_fmt_bytes(file_size)}"))
```

### 3. Retry com Backoff Exponencial
Para falhas de rede temporárias:
```python
for attempt in range(3):
    try:
        storage.upload(...)
        break
    except NetworkError:
        time.sleep(2 ** attempt)  # 1s, 2s, 4s
```

### 4. Compressão Transparente
Comprimir arquivos grandes antes de enviar:
```python
if file_size > 10_000_000:  # > 10 MB
    compressed = gzip.compress(data)
    mime = "application/gzip"
```

---

## ✅ Checklist de Validação

- [x] **Pré-check de duplicatas** funciona
- [x] **Diálogo de duplicatas** exibe corretamente
- [x] **Estratégia "skip"** não envia duplicatas
- [x] **Estratégia "replace"** usa `upsert=True`
- [x] **Estratégia "rename"** gera sufixos corretos
- [x] **Tracking de uploaded_paths** funciona
- [x] **Cancelamento** detectado corretamente
- [x] **Rollback** remove arquivos em lotes
- [x] **Progresso por bytes** exibido
- [x] **ETA adaptativo** (mm:ss ou HH:MM:SS)
- [x] **Finalização suave** (modal fecha antes de browser)
- [x] **0 erros Pylance**
- [x] **5 testes automatizados passando**
- [x] **Demo UI funcional**

---

## 📚 Referências

- [Supabase Storage Upload](https://supabase.com/docs/reference/python/storage-from-upload)
- [Supabase Overwrite Files](https://supabase.com/docs/guides/storage/uploads/standard-uploads)
- [Supabase Storage List](https://supabase.com/docs/reference/python/storage-from-list)
- [Tkinter Event Loop](https://tkdocs.com/tutorial/eventloop.html)
- [EMA - Wikipedia](https://en.wikipedia.org/wiki/Moving_average#Exponential_moving_average)

---

## 🎉 Conclusão

Implementação completa de sistema avançado de upload com:
- ✅ **Pré-check de duplicatas** com 3 estratégias
- ✅ **Cancelamento inteligente** com reversão opcional
- ✅ **Progresso detalhado** (bytes, MB/s, ETA)
- ✅ **Finalização suave** sem travamentos
- ✅ **Thread-safe** via `after()`
- ✅ **5 testes passando**
- ✅ **0 erros Pylance**
- ✅ **UI polida e intuitiva**

**Pronto para produção! 🚀**
