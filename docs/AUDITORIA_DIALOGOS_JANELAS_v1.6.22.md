# AUDITORIA — PADRÃO GLOBAL DE JANELAS, DIÁLOGOS E INTERAÇÕES TRANSVERSAIS

**Versão do app:** v1.6.22  
**Data:** 14 de março de 2026  
**Escopo:** Inventário completo, análise de padronização e proposta arquitetural para diálogos/janelas auxiliares

---

## ÍNDICE

1. [Resposta Direta](#1-resposta-direta)
2. [Inventário Completo de Diálogos](#2-inventário-completo-de-diálogos)
3. [Análise A — Padrão Visual](#3-análise-a--padrão-visual)
4. [Análise B — Padrão de Comportamento](#4-análise-b--padrão-de-comportamento)
5. [Análise C — Padrão de Texto e Copy](#5-análise-c--padrão-de-texto-e-copy)
6. [Análise D — Classificação por Risco](#6-análise-d--classificação-por-risco)
7. [Análise E — Decisão CTk vs TTK vs TK](#7-análise-e--decisão-ctk-vs-ttk-vs-tk)
8. [Análise F — Padrão Arquitetural](#8-análise-f--padrão-arquitetural)
9. [Análise G — Inventário de Exceções](#9-análise-g--inventário-de-exceções)
10. [Matriz de Ação](#10-matriz-de-ação)
11. [Contrato de Diálogos](#11-contrato-de-diálogos)
12. [Diálogos Oficiais do App](#12-diálogos-oficiais-do-app)
13. [Regras de Nomenclatura e Texto](#13-regras-de-nomenclatura-e-texto)
14. [Regras de Quando Usar Confirmação](#14-regras-de-quando-usar-confirmação)
15. [Regra CTk vs TTK vs TK Nativo](#15-regra-ctk-vs-ttk-vs-tk-nativo)

---

## 1. RESPOSTA DIRETA

### 1.1 O app tem ou não tem padrão real de diálogos?

**SIM, TEM — parcialmente.** O app possui um sistema canônico bem desenhado (`rc_dialogs.py` + `feedback.py` + `dialog_icons.py` + `ui_tokens.py`) que define padrão visual, comportamental e modal para diálogos de mensagem. A maioria dos módulos (≈80%) já usa `rc_dialogs` ou `feedback.py` como ponto de entrada. Porém existem **4 bolsões de inconsistência** que quebram o padrão:

| Bolsão | Arquivos | Problema |
|--------|---------|----------|
| `tkinter.messagebox` direto | `app_core.py`, `network.py`, `cloud_guardrails.py` | Visual Tk nativo, sem ícone RC, sem centralização |
| ttkbootstrap legado | `users/users.py`, `forms/layout_helpers.py` | UI inteira em tb.Toplevel/tb.Button/tb.Entry |
| `custom_dialogs.py` duplicado | `custom_dialogs.py` | APIs `show_info` e `ask_ok_cancel` paralelas às de `rc_dialogs` |
| CTkToplevel inline sem checklist completa | `cashflow/dialogs.py`, `hub_dialogs.py` (note_editor) | Faltam bindings, icon, transient, WM_DELETE_WINDOW |

### 1.2 O ideal é centralizar em DialogService/factory?

**O app já caminha nessa direção.** O pipeline `feedback.py` → `rc_dialogs.py` funciona como DialogService implícito. O que falta:
- Forçar que **nenhum** módulo chame `messagebox` diretamente
- Eliminar `custom_dialogs.py` (duplicata)
- Adicionar `InputDialog` e `FileDialogAdapter` ao sistema central
- Formalizar o contrato como interface/protocolo

### 1.3 Quais tipos de diálogo devem virar componente oficial?

| Componente | Status atual | Ação |
|-----------|-------------|------|
| `show_info` / `show_warning` / `show_error` | ✅ Existe em `rc_dialogs` | Manter |
| `ask_yes_no` / `ask_ok_cancel` / `ask_retry_cancel` | ✅ Existe em `rc_dialogs` | Manter |
| `BusyDialog` / `ProgressDialog` | ✅ Existe em `progress_dialog.py` | Manter |
| `InputDialog` (texto simples) | ❌ Não existe centralizado | Criar |
| `ConfirmDestructiveDialog` (ação perigosa com destaque) | ❌ Cada tela resolve sozinha | Criar |
| `UnsavedChangesDialog` (Salvar / Descartar / Cancelar) | ❌ Não existe | Criar |
| `FileDialogAdapter` (wrapper filedialog nativo) | ❌ Parcial em `file_select.py` somente para archives | Expandir |

### 1.4 Quais devem continuar nativos/encapsulados?

- **`filedialog.askopenfilename/asksaveasfilename/askdirectory`** → nativo Tk encapsulado em helper. O diálogo nativo de arquivo do SO é superior a qualquer custom.
- **`messagebox.showerror` em `errors.py` e `tk_exception_handler.py`** → nativo Tk justificável (no ponto mais baixo do stack, antes da UI estar pronta).
- **`tkinter.ttk.Treeview`** → nativo ttk. Não existe equivalente CTk maduro para tabelas/árvores.

### 1.5 Como garantir consistência sem reescrever lógica inteira?

**Plano incremental em 4 ondas:**
1. **Onda 1 (trivial):** Substituir 3 chamadas diretas a `messagebox` por `rc_dialogs` (app_core, network, cloud_guardrails)
2. **Onda 2 (componentes):** Criar `InputDialog` + `ConfirmDestructiveDialog` + `UnsavedChangesDialog` seguindo o template `rc_dialogs`
3. **Onda 3 (eliminação):** Deprecar e remover `custom_dialogs.py`, migrar consumers para `rc_dialogs`
4. **Onda 4 (legado):** Migrar `users/users.py` de ttkbootstrap para CTk; migrar `forms/layout_helpers.py`

---

## 2. INVENTÁRIO COMPLETO DE DIÁLOGOS

### 2.1 Diálogos centrais (sistema canônico)

| Arquivo | API pública | Tipo |
|---------|-------------|------|
| `src/ui/dialogs/rc_dialogs.py` | `show_info`, `show_warning`, `show_error`, `ask_yes_no`, `ask_ok_cancel`, `ask_retry_cancel` | Mensagem modal CTk |
| `src/ui/feedback.py` | `TkFeedback.info/warning/error/confirm/busy/progress` | Fachada de alto nível |
| `src/ui/components/progress_dialog.py` | `BusyDialog`, `ProgressDialog` | Progresso modal CTk |
| `src/ui/dialog_icons.py` | `make_icon_label(kind)` | Ícones PIL para diálogos |
| `src/ui/ui_tokens.py` | Cores, fontes, espaçamentos, raios | Design tokens |
| `src/ui/widgets/button_factory.py` | `make_btn`, `make_btn_sm`, `make_btn_icon` | Fábrica de botões |

### 2.2 Diálogos especializados (CTkToplevel)

| Arquivo | Classe/Função | Propósito |
|---------|--------------|-----------|
| `src/ui/dialogs/download_result_dialog.py` | `DownloadResultDialog` | Resultado de download |
| `src/ui/dialogs/pdf_converter_dialogs.py` | `PDFDeleteImagesConfirmDialog`, `PDFConversionResultDialog` | Confirmações PDF |
| `src/ui/dialogs/file_select.py` | `select_archive_file`, `select_archive_files` | Seleção de arquivo (nativo) |
| `src/ui/login_dialog.py` | `LoginDialog` | Tela de login |
| `src/ui/splash.py` | `show_splash_screen` | Splash screen |
| `src/ui/users/users.py` | `UserManagerDialog` | Gerenciamento de usuários (**ttkbootstrap**) |
| `src/ui/custom_dialogs.py` | `show_info`, `ask_ok_cancel` | **Duplicata de rc_dialogs** |
| `src/modules/tasks/views/task_dialog.py` | `NovaTarefaDialog` | Criar tarefa |
| `src/modules/lixeira/views/lixeira.py` | `abrir_lixeira` + wait_dialog inline | Lixeira + progresso |
| `src/modules/hub/views/hub_dialogs.py` | `show_note_editor`, `confirm_delete_note` | Editor de notas |
| `src/features/cashflow/dialogs.py` | `EntryDialog` | Lançamento financeiro |
| `src/features/cashflow/ui.py` | `CashflowWindow` | Painel financeiro |
| `src/modules/uploads/views/browser_v2.py` | `UploadsBrowserWindowV2` | Browser de uploads |
| `src/modules/pdf_preview/views/main_window.py` | `PdfViewerWin` | Visualizador PDF |
| `src/modules/clientes/ui/views/client_editor_dialog.py` | `ClientEditorDialog` | Editor de clientes |
| `src/modules/clientes/forms/client_subfolder_prompt.py` | `SubpastaDialog` | Input de subpasta |
| `src/modules/chatgpt/views/chatgpt_window.py` | `ChatGPTWindow` | Integração ChatGPT |

### 2.3 Chamadas diretas a `tkinter.messagebox` (NÃO padronizadas)

| Arquivo | Função | Chamada direta |
|---------|--------|---------------|
| `src/core/app_core.py` | `_safe_messagebox` | `messagebox.showwarning`, `showerror`, `askyesno`, `showinfo` |
| `src/utils/network.py` | módulo-level | `messagebox.askokcancel("Internet Necessária", ...)` |
| `src/utils/helpers/cloud_guardrails.py` | `check_cloud()` | `messagebox.showinfo("Atenção", ...)` |
| `src/utils/errors.py` | `_show_error_dialog` | `messagebox.showerror("Erro Inesperado", ...)` |
| `src/core/tk_exception_handler.py` | `_handle_tk_exception` | `messagebox.showerror("Erro Interno (Dev Mode)", ...)` |
| `src/core/app.py` | `_fatal_error` | `messagebox.showerror(...)` (fallback fatal) |

### 2.4 Chamadas a `filedialog` (nativo Tk)

| Arquivo | Função | Tipo |
|---------|--------|------|
| `src/ui/dialogs/file_select.py` | `select_archive_file/files` | `askopenfilename/askopenfilenames` |
| `src/modules/forms/actions_impl.py` | `import_client_folder` | `askdirectory` |
| `src/modules/uploads/views/browser_v2.py` | download/upload | `asksaveasfilename`, `askopenfilenames` |
| `src/modules/uploads/uploader_supabase.py` | upload flows | `askopenfilenames`, `askdirectory` |
| `src/modules/clientes/ui/view.py` | export CSV | `asksaveasfilename` |
| `src/modules/clientes/ui/views/_editor_actions_mixin.py` | select folder | `askdirectory` |
| `src/modules/clientes/forms/client_form_upload_helpers.py` | upload | `askdirectory`, `askopenfilenames` |
| `src/modules/main_window/app_actions.py` | backup/restore | `askdirectory` |

### 2.5 Componentes ttkbootstrap (legado)

| Arquivo | Componentes usados |
|---------|-------------------|
| `src/ui/users/users.py` | `tb.Treeview`, `tb.Button`, `tb.Frame`, `tb.Entry`, `tb.Label`, `tb.Toplevel` |
| `src/ui/forms/layout_helpers.py` | `tb.Frame`, `tb.Label`, `tb.Entry` |

---

## 3. ANÁLISE A — PADRÃO VISUAL

### 3.1 O que `rc_dialogs` define como padrão

| Propriedade | Valor |
|------------|-------|
| **Largura fixa** | 360px |
| **Altura** | Auto (winfo_reqheight + 10) |
| **Padding do frame** | padx=24, pady=20 |
| **Tipografia da mensagem** | `("Segoe UI", 12)`, center-justified |
| **wraplength** | 300px |
| **Ícone** | PIL desenhado, 44×44px (success=verde, warning=âmbar, error=vermelho) |
| **Espaço ícone→texto** | pady=(0, 6) |
| **Espaço texto→botões** | pady=(0, 14) |
| **Botões tamanho** | 110×28 (`DIALOG_BTN_W` × `DIALOG_BTN_H`) |
| **Botão radius** | 10px (`BUTTON_RADIUS`) |
| **Botão primário info** | Azul `#2563eb` / `#3b82f6` |
| **Botão primário destrutivo** | Vermelho `#dc2626` / `#ef4444` |
| **Botão secundário** | Cinza `#6b7280` / `#4b5563` |
| **Botão aviso** | Âmbar `#d97706` / `#f59e0b` |
| **Fundo janela** | `APP_BG` (branco/preto conforme tema) |
| **Corner radius geral** | 0 na janela (SO gerencia), 16 no card interno (`DIALOG_RADIUS`) |
| **Suporte light/dark** | ✅ Todas as cores são tuplas `(light, dark)` |

### 3.2 Inconsistências visuais encontradas

| Diálogo | Problema |
|---------|----------|
| `custom_dialogs.py` `show_info` | Ícone é emoji Unicode "ℹ" em vez de PIL; layout grid em vez de pack; sem cor de fundo APP_BG |
| `custom_dialogs.py` `ask_ok_cancel` | Ícone é "?" em `text_color="#000000"` hardcoded (não funciona em dark mode) |
| `pdf_converter_dialogs.py` | `_BaseDialog` usa `apply_app_icon` própria (diferente de `apply_window_icon`); ícone "?" com `font=("Segoe UI", 26)` em vez de PIL |
| `users/users.py` | ttkbootstrap inteiro; visual completamente diferente; botões bootstyle em vez de CTk |
| `hub_dialogs.py` (note_editor) | Sem `apply_window_icon`; sem `APP_BG`/`SURFACE` tokens; geometry fixa 500×350 |
| `cashflow/dialogs.py` `EntryDialog` | Sem `apply_window_icon`; sem token de cores explícito |
| Chamadas diretas a `messagebox` | Visual nativo do SO (janela Tk padrão) — visualmente alienígena no app |
| `DownloadResultDialog` | Usa `SURFACE_2` como fundo (diferente de `APP_BG` usado em rc_dialogs) |

### 3.3 Posição das janelas

| Componente | Centralização |
|-----------|--------------|
| `rc_dialogs` | Centraliza **no parent** via `_center_on_parent` ✅ |
| `show_centered` (window_utils) | Centraliza **na tela** ✅ (usado por diálogos complexos) |
| `dark_window_helper` | Centraliza **na tela** (não no parent) ⚠️ discrepante para modais |
| `custom_dialogs.py` | Usa `show_centered` (tela) ⚠️ deveria ser no parent |
| `messagebox` nativo | Centraliza no root window do Tk (comportamento do SO) |

---

## 4. ANÁLISE B — PADRÃO DE COMPORTAMENTO

### 4.1 Checklist de conformidade — modais simples (mensagem/confirmação)

| Requisito | `rc_dialogs` | `custom_dialogs` | `pdf_converter_dialogs` | `messagebox` direto |
|----------|:---:|:---:|:---:|:---:|
| Modal (`grab_set`) | ✅ | ✅ | ✅ | ✅ (Tk nativo) |
| `transient(parent)` | ✅ | ✅ | ✅ | N/A |
| Foco inicial | ✅ (`focus_force`) | ✅ | ✅ | N/A |
| `<Return>` = ação primária | ✅ | ✅ | ✅ | ✅ (nativo) |
| `<Escape>` = cancelar/fechar | ✅ | ✅ | ✅ | ✅ (nativo) |
| `WM_DELETE_WINDOW` configurado | ✅ | ❌ ausente | ✅ | N/A |
| `wait_window` | ✅ | ✅ | ✅ | ✅ (nativo) |
| Ícone RC do app | ✅ | ✅ (via `_apply_icon`) | ✅ (via `apply_app_icon` — diferente) | ❌ |
| Anti-flash (withdraw→deiconify) | ✅ (alpha trick) | ✅ (withdraw) | ✅ (withdraw) | N/A |
| Centralizado no parent | ✅ | ❌ (tela) | ❌ (tela) | ❌ (root) |

### 4.2 Checklist — diálogos complexos (formulário/janela)

| Requisito | TaskDialog | LixeiraWin | EntryDialog (cash) | NoteEditor (hub) | LoginDialog | SubpastaDialog |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|
| `withdraw()` inicial | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `transient(parent)` | ✅ | ❌ (singleton) | ❌ | ✅ | ❌ | ✅ |
| `grab_set` | ✅ | ❌ (não-modal) | ✅ | ✅ | ❌ | ✅ |
| `apply_window_icon` | ✅ (`apply_rc_icon`) | ✅ | ❌ | ❌ | ✅ | ✅ |
| `<Return>` binding | ✅ | ❌ | ❌ | `<Control-Return>` ⚠️ | ✅ | ✅ |
| `<Escape>` binding | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| `WM_DELETE_WINDOW` | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| `show_centered` | ✅ | ✅ | ✅ | manual ⚠️ | ✅ | ✅ |
| Destroy correto | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 4.3 Tab Order e navegação

- **Nenhum** diálogo define `takefocus` ou `taborder` explícito — depende da ordem de criação dos widgets (padrão Tk).
- Isso é aceitável para a maioria dos diálogos simples, mas formulários complexos (`ClientEditorDialog`, `EntryDialog`) se beneficiariam de ordem explícita.

---

## 5. ANÁLISE C — PADRÃO DE TEXTO E COPY

### 5.1 Vocabulário de botões encontrado

| Ação | Labels usados |
|------|--------------|
| Confirmar positivo | "Sim", "OK", "Confirmar", "Salvar", "Criar Tarefa", "Entrar" |
| Cancelar/negar | "Não", "Cancelar", "Fechar", "Sair" |
| Retry | "Tentar novamente" |
| Destrutivo | "Excluir", "Apagar Selecionados", "Sim" (para exclusão) |

### 5.2 Inconsistências de copy

| Problema | Onde |
|---------|-----|
| "OK" genérico em `show_info/show_error/show_warning` | `rc_dialogs.py` — aceitável para mensagens informativas |
| "Sim"/"Não" em confirmação destrutiva | `ask_yes_no` — ideal seria "Excluir"/"Cancelar" em contexto destrutivo |
| `custom_dialogs.py` define `OK_LABEL = "Sim"` e `CANCEL_LABEL = "Não"` | Confuso: `ask_ok_cancel` retorna True/False mas mostra "Sim"/"Não" em vez de "OK"/"Cancelar" |
| Botão de login "Sair" em vermelho `#dc3545` | Cor diferente do token `KPI_RED` (`#ef4444`) |
| Nota vazia: "O texto da nota não pode estar vazio." | Correto e claro ✅ |

### 5.3 Títulos de janelas

| Padrão | Exemplos |
|--------|---------|
| ✅ Ação + contexto | "Editar Nota", "Nova Nota", "Nova Tarefa" |
| ✅ Módulo | "Conversor PDF", "Lixeira" |
| ⚠️ Genérico | "Atenção", "Erro", "Aguarde..." |
| ❌ Sem padrão | "Internet Necessária" (network.py), "Erro Inesperado" (errors.py) — vêm de messagebox legado |

---

## 6. ANÁLISE D — CLASSIFICAÇÃO POR RISCO

### 6.1 Inventário por tipo

| Tipo | Onde é usado | Correto? |
|------|-------------|----------|
| **Informativo** | `show_info` (upload completo, backup salvo, nota salva) | ✅ |
| **Confirmação simples** | `ask_ok_cancel` (operações reversíveis) | ✅ |
| **Confirmação destrutiva** | `ask_yes_no` (excluir cliente, apagar notas, purge lixeira) | ⚠️ ver abaixo |
| **Erro** | `show_error` (falha de rede, validação, upload) | ✅ |
| **Sucesso** | `show_info` com ícone "success" | ✅ (mas ícone é "success" mesmo sendo show_info) |
| **Progresso** | `BusyDialog` (indeterminado), `ProgressDialog` (determinado) | ✅ |
| **Input** | `SubpastaDialog`, `show_note_editor` | ⚠️ sem componente central |
| **Aviso** | `show_warning` | ✅ |

### 6.2 Análise de confirmações

| Fluxo | Confirmação | Avaliação |
|-------|------------|-----------|
| Excluir cliente → lixeira | `ask_yes_no("Enviar para Lixeira?")` | ✅ Correto — ação é reversível mas importante |
| Purge da lixeira (permanente) | `ask_yes_no("Deseja excluir permanentemente?")` | ⚠️ Deveria ter destaque extra (ação irreversível) |
| Excluir nota | `confirm_delete_note` → `ask_yes_no` | ✅ Correto |
| Excluir imagens após PDF | `PDFDeleteImagesConfirmDialog` 3 opções | ✅ Correto — bom modelo |
| Upload de arquivo | Sem confirmação | ✅ Correto — não precisa |
| Sair do app | Sem verificação de unsaved changes | ⚠️ Falta `UnsavedChangesDialog` |
| Restaurar da lixeira | `ask_yes_no("Restaurar N clientes?")` | ✅ Correto |
| Excluir tarefa | Provavelmente sim, mas via `ask_yes_no` genérico | ⚠️ Botão deveria dizer "Excluir" |

### 6.3 O que falta

- **Ação irreversível sem destaque visual diferenciado**: `ask_yes_no` usa vermelho no "Sim" sempre, mas não tem texto de aviso extra ou impedimento (ex.: "digite EXCLUIR para confirmar") para purge permanente.
- **Falta confirmação de saída com alterações pendentes**: ClientEditorDialog, NoteEditor, EntryDialog (cashflow) não pedem para salvar ao fechar com X.
- **Confirmações desnecessárias**: Nenhuma detectada — o app é contido nesse aspecto ✅.

---

## 7. ANÁLISE E — DECISÃO CTK vs TTK vs TK

### Critério proposto

| Tipo de janela/diálogo | Abordagem padrão | Justificativa |
|-----------------------|------------------|--------------|
| Diálogos de mensagem (info/warning/error/success) | **`rc_dialogs.py`** (CTkToplevel) | Visual consistente, ícone RC, anti-flash |
| Diálogos de confirmação (sim/não, ok/cancel) | **`rc_dialogs.py`** (CTkToplevel) | Idem |
| Diálogos de progresso/busy | **`progress_dialog.py`** (CTkToplevel) | Visual consistente, progress bar CTk |
| Diálogos de input simples (texto, nome) | **Novo `InputDialog`** (CTkToplevel, template `rc_dialogs`) | Atualmente cada módulo faz seu próprio |
| Formulários complexos (editor de cliente, tarefa, nota) | **CTkToplevel custom** (seguindo checklist de comportamento) | Complexidade exige UI dedicada |
| Janelas de módulo (lixeira, uploads, PDF viewer, cashflow) | **CTkToplevel custom** (não modal, sem grab_set) | São janelas de trabalho, não diálogos |
| Seleção de arquivo/pasta | **`tkinter.filedialog` nativo** encapsulado em helper | Diálogo do SO é superior |
| Tabelas/árvores | **`tkinter.ttk.Treeview`** | Sem equivalente CTk maduro |
| Tooltips | **CTkToplevel overrideredirect** | Padrão já usado em `modules_panel.py` ✅ |
| Toasts (notificação não-bloqueante) | **CTkToplevel overrideredirect** via `feedback.py` | Já implementado ✅ |
| Splash screen | **CTkToplevel overrideredirect** | Já implementado ✅ |
| Autocomplete dropdown | **CTkToplevel overrideredirect** | Já implementado em `ctk_autocomplete_entry.py` ✅ |

### O que NÃO usar mais

| Proibido | Motivo | Substituir por |
|---------|--------|---------------|
| `tkinter.messagebox` direto nos módulos | Visual alienígena, sem ícone RC | `rc_dialogs` |
| `ttkbootstrap` (tb) inteiro | Removido do projeto em jan/2026 | CTkToplevel + CTkButton/CTkEntry |
| `custom_dialogs.py` | Duplicata de `rc_dialogs`, menos polida | `rc_dialogs` |
| `simpledialog` | Nunca usado, mas prevenir uso futuro | `InputDialog` custom |

---

## 8. ANÁLISE F — PADRÃO ARQUITETURAL

### 8.1 Camada existente (o que já funciona)

```
┌─────────────────────────────────────────────┐
│                  MÓDULOS                      │
│  (clientes, hub, tasks, uploads, cashflow)   │
└──────────────┬──────────────┬────────────────┘
               │              │
    ┌──────────▼──────┐  ┌───▼───────────────┐
    │  rc_dialogs.py  │  │   feedback.py      │
    │  (mensagens)    │◄─┤   (fachada)        │
    └──────┬──────────┘  └───┬───────────────┘
           │                 │
    ┌──────▼──────────┐  ┌──▼────────────────┐
    │ dialog_icons.py │  │ progress_dialog.py │
    │ (PIL icons)     │  │ (Busy/Progress)    │
    └──────┬──────────┘  └──┬────────────────┘
           │                │
    ┌──────▼────────────────▼────────────────┐
    │            ui_tokens.py                 │
    │  (cores, fontes, espaçamentos)          │
    └──────┬─────────────────────────────────┘
           │
    ┌──────▼────────────────────┐
    │  button_factory.py        │
    │  window_utils.py          │
    │  window_icon.py           │
    │  dark_window_helper.py    │
    └───────────────────────────┘
```

### 8.2 O que falta adicionar

```
┌─────────────────────────────────────────────┐
│                  MÓDULOS                      │
└──────────────┬──────────────┬────────────────┘
               │              │
    ┌──────────▼──────────────▼────────────────┐
    │          feedback.py (FACHADA)            │  ← ponto único
    │  .info()  .warning()  .error()  .confirm()│
    │  .input()  .confirm_destructive()         │  ← NOVO
    │  .unsaved_changes()                       │  ← NOVO
    │  .busy()  .progress()                     │
    │  .select_file()  .select_folder()         │  ← NOVO (encapsular filedialog)
    └──────────────────────────────────────────┘
```

### 8.3 Recomendações

1. **NÃO criar um `DialogService` separado** — `feedback.py` já é o service. Expandi-lo.
2. **NÃO criar `AppDialogFactory` / `DialogFactory`** — over-engineering. As funções de `rc_dialogs` já são a factory.
3. **Criar 3 novos diálogos** em `src/ui/dialogs/`:
   - `input_dialog.py` → `InputDialog` (campo de texto + OK/Cancelar)
   - `confirm_destructive_dialog.py` → `ConfirmDestructiveDialog` (aviso vermelho + nome da ação)
   - `unsaved_changes_dialog.py` → `UnsavedChangesDialog` (Salvar/Descartar/Cancelar)
4. **Expandir `file_select.py`** com wrappers para `askdirectory` e `asksaveasfilename`
5. **Adicionar lint rule**: grep CI para `from tkinter import messagebox` fora de `errors.py`/`tk_exception_handler.py`/`app.py`

---

## 9. ANÁLISE G — INVENTÁRIO DE EXCEÇÕES

### 9.1 Diálogos que devem ser padronizados globalmente

| Diálogo | Ação | Esforço |
|---------|------|---------|
| `app_core.py` `_safe_messagebox` | Substituir 5 chamadas por `rc_dialogs` | Baixo |
| `network.py` `messagebox.askokcancel` | Substituir por `rc_dialogs.ask_ok_cancel` | Baixo |
| `cloud_guardrails.py` `messagebox.showinfo` | Substituir por `rc_dialogs.show_info` | Trivial |
| `custom_dialogs.py` inteiro | Deprecar; migrar 0 consumers (verificar se há algum import restante) | Médio |

### 9.2 Diálogos que podem continuar nativos

| Diálogo | Motivo |
|---------|--------|
| `filedialog.askopenfilename/asksaveasfilename/askdirectory` | Diálogo nativo do SO — UX superior |
| `messagebox.showerror` em `errors.py` | Exception hook de último recurso — antes da UI existir |
| `messagebox.showerror` em `tk_exception_handler.py` | Dev-only, infra de exceção — risco de recursão se usar CTk |
| `messagebox.showerror` em `app.py` `_fatal_error` | Fallback fatal — CTk pode estar destruído nesse ponto |

### 9.3 Diálogos que estão bons como estão

| Diálogo | Motivo |
|---------|--------|
| `rc_dialogs.py` (todos) | Padrão canônico, bem implementado ✅ |
| `BusyDialog` / `ProgressDialog` | Completos, tokens corretos ✅ |
| `DownloadResultDialog` | Segue padrão anti-flash, modal correto ✅ |
| `SubpastaDialog` | Todos os requisitos atendidos ✅ |
| `NovaTarefaDialog` | Quase perfeito (usa `apply_rc_icon` em vez de `apply_window_icon` — menor) |
| `PDFDeleteImagesConfirmDialog` | Bom modelo de 3 opções ✅ |

### 9.4 Diálogos quebrando o padrão (mas funcionais)

| Diálogo | Problema | Risco de mexer |
|---------|---------|---------------|
| `hub_dialogs.py` `show_note_editor` | Sem icon, sem WM_DELETE_WINDOW | **Baixo** — adicionar é trivial |
| `cashflow/dialogs.py` `EntryDialog` | Sem Return/Esc, sem icon, sem transient | **Médio** — precisa testar bindings com form |
| `login_dialog.py` `LoginDialog` | Sem transient, sem grab_set, sem WM_DELETE_WINDOW | **Médio** — é tela de login, alterar modal pode afetar fluxo |

### 9.5 Alto risco de regressão se alterados

| Diálogo | Motivo do risco |
|---------|----------------|
| `users/users.py` `UserManagerDialog` | Inteiro em ttkbootstrap — reescrita completa necessária |
| `UploadsBrowserWindowV2` | Workarounds complexos de flash/icon/grab — código frágil e bem testado |
| `ClientEditorDialog` | Mixins complexos, grab_set com retry — funciona, não tocar sem necessidade |
| `PdfViewerWin` | Viewer com rendering PDF — alto risco se alterar lifecycle da janela |

---

## 10. MATRIZ DE AÇÃO

### Grupo 1 — Padronização simples (1-2h cada)

| # | Ação | Arquivo | O que fazer |
|---|------|---------|-------------|
| 1.1 | Substituir `messagebox` em `cloud_guardrails.py` | `utils/helpers/cloud_guardrails.py` | `messagebox.showinfo` → `rc_dialogs.show_info` |
| 1.2 | Substituir `messagebox` em `network.py` | `utils/network.py` | `messagebox.askokcancel` → `rc_dialogs.ask_ok_cancel` |
| 1.3 | Substituir `messagebox` em `app_core.py` | `core/app_core.py` | `_safe_messagebox` → wrapper de `rc_dialogs` com try/except |
| 1.4 | Adicionar icon + WM_DELETE em `show_note_editor` | `hub/views/hub_dialogs.py` | `apply_window_icon(dialog)` + `protocol("WM_DELETE_WINDOW", on_cancel)` |
| 1.5 | Adicionar Escape/Return em `EntryDialog` | `cashflow/dialogs.py` | `bind("<Escape>", _cancel)` + `bind("<Return>", _save)` |
| 1.6 | Adicionar transient em `EntryDialog` | `cashflow/dialogs.py` | `self.transient(parent)` |
| 1.7 | Adicionar WM_DELETE no `LoginDialog` | `ui/login_dialog.py` | `protocol("WM_DELETE_WINDOW", _on_exit)` |

### Grupo 2 — Refatoração de componente base (4-8h cada)

| # | Ação | Arquivo(s) | O que fazer |
|---|------|-----------|-------------|
| 2.1 | Criar `InputDialog` | `ui/dialogs/input_dialog.py` | CTkToplevel seguindo template `rc_dialogs._make_dialog` |
| 2.2 | Criar `ConfirmDestructiveDialog` | `ui/dialogs/confirm_destructive_dialog.py` | Vermelho, ícone error, botão com nome da ação |
| 2.3 | Criar `UnsavedChangesDialog` | `ui/dialogs/unsaved_changes_dialog.py` | 3 botões: Salvar/Descartar/Cancelar |
| 2.4 | Expandir `file_select.py` | `ui/dialogs/file_select.py` | Adicionar `select_folder`, `save_file` com logging |
| 2.5 | Registrar novos diálogos em `feedback.py` | `ui/feedback.py` | Adicionar `.input()`, `.confirm_destructive()`, `.unsaved_changes()` |

### Grupo 3 — Refatoração estrutural (8-16h)

| # | Ação | Arquivo(s) | O que fazer |
|---|------|-----------|-------------|
| 3.1 | Deprecar `custom_dialogs.py` | `ui/custom_dialogs.py` | Verificar imports, redirecionar para `rc_dialogs`, depois remover |
| 3.2 | Migrar `users.py` de ttkbootstrap | `ui/users/users.py` | Reescrever inteiro com CTk (tb.Treeview → ctk_treeview ou ttk.Treeview themed) |
| 3.3 | Migrar `layout_helpers.py` | `ui/forms/layout_helpers.py` | `tb.Frame/Label/Entry` → `ctk.CTkFrame/CTkLabel/CTkEntry` |

### Grupo 4 — Manter nativo/ttk

| # | Item | Motivo |
|---|------|--------|
| 4.1 | `filedialog` em todos os módulos | Diálogo nativo do SO é correto |
| 4.2 | `messagebox` em `errors.py` / `tk_exception_handler.py` / `app.py` | Infra de último recurso, antes/além do CTk |
| 4.3 | `ttk.Treeview` em `clientes/view.py`, `ttk_treeview_*.py` | Sem substituto CTk adequado |

---

## 11. CONTRATO DE DIÁLOGOS

### Regras obrigatórias para TODO diálogo CTkToplevel do app

```python
# CHECKLIST OBRIGATÓRIA — todo CTkToplevel modal do app DEVE:

1. withdraw()                          # Antes de qualquer build
2. title(titulo_descritivo)            # Nunca vazio
3. resizable(False, False)             # Para modais simples; True para janelas de trabalho
4. configure(fg_color=APP_BG)          # Token de fundo do app
5. apply_window_icon(self)             # Ícone RC
6. transient(parent)                   # Vincula ao parent
7. # ... build da UI ...
8. protocol("WM_DELETE_WINDOW", _on_close)  # Sempre configurar
9. bind("<Escape>", _on_close)              # Sempre
10. bind("<Return>", _on_primary_action)     # Quando houver ação primária
11. update_idletasks()
12. show_centered(self)                     # Ou _center_on_parent
13. grab_set()                              # Modal
14. focus_force()                           # Foco
15. # Para ação final: destroy() + wait_window no caller
```

### Fluxo anti-flash obrigatório

```
withdraw() → build → apply_icon → transient → update_idletasks →
center → deiconify (via show_centered) → grab_set → focus_force
```

### Convenções de retorno

| Tipo | Retorno |
|------|---------|
| Info/Warning/Error | `None` (sem retorno) |
| Confirmação sim/não | `bool` |
| Confirmação 3 opções | `str` ("yes", "no", "cancel") ou `Optional[str]` com `None` para cancel |
| Input | `str` ou `None` (cancelado) |
| Formulário | `dict` ou `None` (cancelado) |

---

## 12. DIÁLOGOS OFICIAIS DO APP

### Lista canônica — os diálogos que o app reconhece oficialmente

| Nome | Arquivo | Tipo | Retorno |
|------|---------|------|---------|
| `show_info` | `rc_dialogs.py` | Informativo | `None` |
| `show_warning` | `rc_dialogs.py` | Aviso | `None` |
| `show_error` | `rc_dialogs.py` | Erro | `None` |
| `ask_yes_no` | `rc_dialogs.py` | Confirmação | `bool` |
| `ask_ok_cancel` | `rc_dialogs.py` | Confirmação | `bool` |
| `ask_retry_cancel` | `rc_dialogs.py` | Retry | `bool` |
| `BusyDialog` | `progress_dialog.py` | Progresso indeterminado | handle |
| `ProgressDialog` | `progress_dialog.py` | Progresso determinado | handle |
| `InputDialog` | **A CRIAR** `input_dialog.py` | Input de texto | `str \| None` |
| `ConfirmDestructiveDialog` | **A CRIAR** | Confirmação destrutiva | `bool` |
| `UnsavedChangesDialog` | **A CRIAR** | Alterações não salvas | `str` |
| `select_archive_file` | `file_select.py` | Seleção de arquivo | `str` |
| `select_archive_files` | `file_select.py` | Seleção múltipla | `tuple[str]` |
| `select_folder` | **A CRIAR** em `file_select.py` | Seleção de pasta | `str` |
| `save_file` | **A CRIAR** em `file_select.py` | Salvar arquivo | `str` |

### Diálogos especializados (módulo-específicos, mas seguindo o contrato)

| Nome | Módulo | Observação |
|------|--------|-----------|
| `LoginDialog` | `ui/login_dialog.py` | Formulário complexo, aceitável |
| `ClientEditorDialog` | `clientes/` | Formulário complexo, aceitável |
| `NovaTarefaDialog` | `tasks/` | Formulário, quase conforme |
| `SubpastaDialog` | `clientes/forms/` | Input especializado, conforme ✅ |
| `DownloadResultDialog` | `ui/dialogs/` | Resultado de download, conforme ✅ |
| `PDFDeleteImagesConfirmDialog` | `ui/dialogs/` | 3 opções, conforme ✅ |

---

## 13. REGRAS DE NOMENCLATURA E TEXTO

### Botões — verbos de ação

| Contexto | ✅ Correto | ❌ Evitar |
|---------|-----------|----------|
| Salvar formulário | "Salvar" | "OK" |
| Criar novo item | "Criar Tarefa", "Criar Nota" | "OK", "Sim" |
| Excluir item | "Excluir", "Apagar" | "Sim", "OK" |
| Confirmar envio | "Enviar" | "OK" |
| Fechar diálogo info | "OK" | "Fechar" |
| Cancelar ação | "Cancelar" | "Não" (exceto em ask_yes_no) |
| Sair sem salvar | "Descartar" | "Não", "Sair" |
| Retentar operação | "Tentar novamente" | "Retry", "OK" |

### Títulos — padrão

| Tipo | Formato | Exemplos |
|------|---------|---------|
| Informativo | Módulo ou ação | "Upload Concluído", "Backup" |
| Aviso | Contexto | "Campo Obrigatório", "Conexão" |
| Erro | "Erro" + contexto | "Erro ao Salvar", "Erro de Rede" |
| Confirmação | Ação como pergunta | "Excluir Cliente?", "Enviar para Lixeira?" |
| Input | Ação | "Nome da Subpasta", "Nova Nota" |

### Mensagens — regras

1. **Máximo 2 linhas** para diálogos simples
2. **Sem ponto final** em mensagens de uma frase
3. **Sem "Deseja realmente..."** — redundante com o botão
4. **Contexto específico**: "O cliente 'Empresa X' será enviado para a Lixeira" em vez de "O item será excluído"
5. **Tom neutro**: não usar "Atenção!", "Cuidado!", "AVISO"

---

## 14. REGRAS DE QUANDO USAR CONFIRMAÇÃO

### USAR confirmação quando:

| Situação | Tipo de confirmação |
|---------|-------------------|
| Exclusão de dados (lixeira, apagar) | `ask_yes_no` ou `ConfirmDestructiveDialog` |
| Purge permanente (irreversível) | `ConfirmDestructiveDialog` com nome da ação |
| Sair com alterações pendentes | `UnsavedChangesDialog` |
| Operação que afeta múltiplos itens | `ask_yes_no` com contagem ("Excluir 5 clientes?") |
| Operação de rede demorada | Apenas se cancelável |

### NÃO usar confirmação quando:

| Situação | Motivo |
|---------|--------|
| Upload de arquivo | Operação normal, reversível (pode excluir depois) |
| Salvar formulário | O usuário já clicou "Salvar" — confiança |
| Navegar entre telas | Não modificou dados |
| Abrir arquivo/pasta | Sem efeito colateral |
| Login | O usuário quer entrar |
| Atualizar lista/refresh | Sem perda de dados |
| Fechar diálogo info/erro/aviso | Sem consequência |

### Princípio geral

> Confirmar apenas PERDAS. Nunca confirmar GANHOS.
> Se a ação é reversível E de baixo impacto, não confirmar.

---

## 15. REGRA CTK vs TTK vs TK NATIVO

### Decisão por tipo

```
SE é diálogo de mensagem/confirmação/input:
    → rc_dialogs.py (CTkToplevel)
    → NUNCA messagebox/simpledialog

SE é seleção de arquivo/pasta:
    → tkinter.filedialog nativo encapsulado em file_select.py
    → NÃO tentar recriar em CTk

SE é tabela/árvore de dados:
    → tkinter.ttk.Treeview com tema via ttk_treeview_theme.py
    → NÃO usar ttkbootstrap

SE é formulário modal (criar/editar):
    → CTkToplevel custom seguindo CONTRATO (seção 11)
    → NÃO usar ttkbootstrap

SE é janela de trabalho (viewer, browser):
    → CTkToplevel custom, geralmente não-modal
    → Seguir anti-flash pattern

SE é tooltip/dropdown/autocomplete:
    → CTkToplevel com overrideredirect(True)
    → Sem grab_set

SE é toast/notificação:
    → CTkToplevel via feedback.py
    → overrideredirect(True), auto-close

SE é splash:
    → CTkToplevel overrideredirect(True)
    → Próprio lifecycle

SE é fallback de exceção (antes da UI existir):
    → tkinter.messagebox (justificável)
```

### Proibições

| Proibido | Substituto |
|---------|-----------|
| `from tkinter import messagebox` nos módulos de feature | `from src.ui.dialogs.rc_dialogs import ...` |
| `import ttkbootstrap as tb` | `from src.ui.ctk_config import ctk` |
| `from src.ui.custom_dialogs import ...` | `from src.ui.dialogs.rc_dialogs import ...` |
| `simpledialog.askstring` | Novo `InputDialog` quando criado |

---

## RESUMO EXECUTIVO

O app **já possui uma base sólida** de padronização com `rc_dialogs.py` + `feedback.py` como núcleo. A maioria dos módulos (~80%) segue esse padrão.

**Ações prioritárias:**
1. **3 substituições triviais** de `messagebox` direto (app_core, network, cloud_guardrails)
2. **7 ajustes de conformidade** nos diálogos existentes (bindings, icon, WM_DELETE)
3. **3 novos componentes** (InputDialog, ConfirmDestructiveDialog, UnsavedChangesDialog)
4. **1 deprecação** (custom_dialogs.py)
5. **2 migrações de legado** (users.py, layout_helpers.py → de ttkbootstrap para CTk)

**Não tocar sem necessidade:** UploadsBrowserWindowV2, ClientEditorDialog, PdfViewerWin — código frágil, funcional, e já testado.
