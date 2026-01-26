# Análise de Migração CustomTkinter - ClientesV2

**Data**: 26 de janeiro de 2026  
**Módulo**: `src/modules/clientes_v2/`  
**Status**: Migração parcial concluída, pendências identificadas

---

## 📊 Resumo Executivo

O módulo **ClientesV2** já está majoritariamente migrado para CustomTkinter, mas ainda existem:

- ✅ **80% migrado**: Todos os diálogos e componentes principais usam CTk
- ⚠️ **20% pendente**: `ttk.Treeview` (tabela principal) ainda usa Tkinter padrão
- 🔧 **Melhorias**: Oportunidades de usar widgets CTk mais avançados

---

## 📁 Estrutura Atual

```
src/modules/clientes_v2/
├── view.py                          # Frame principal (✅ CTk + ⚠️ ttk.Treeview)
├── tree_theme.py                    # Helper para tema ttk (⚠️ necessário)
├── views/
│   ├── toolbar.py                   # ✅ 100% CTk (CTkEntry, CTkButton, CTkOptionMenu)
│   ├── actionbar.py                 # ✅ 100% CTk (CTkButton)
│   ├── client_editor_dialog.py      # ✅ 100% CTk (CTkToplevel, todos widgets)
│   ├── client_files_dialog.py       # ✅ 100% CTk (CTkToplevel, placeholder)
│   └── upload_dialog.py             # ✅ 100% CTk (CTkScrollableFrame, CTkTextbox)
```

---

## ✅ O Que Já Está Migrado

### 1. **ClientesV2Frame** (view.py)
- ✅ Container principal: `ctk.CTkFrame`
- ✅ Toolbar: `ClientesV2Toolbar` (100% CTk)
- ✅ ActionBar: `ClientesV2ActionBar` (100% CTk)
- ⚠️ **Treeview**: Ainda usa `ttk.Treeview` (ver seção de pendências)

### 2. **ClientEditorDialog** (client_editor_dialog.py)
**Completo**: 739 linhas, 100% CustomTkinter

- ✅ Base: `ctk.CTkToplevel`
- ✅ Todos os campos: `ctk.CTkEntry`
- ✅ Observações: `ctk.CTkTextbox`
- ✅ Status: `ctk.CTkOptionMenu`
- ✅ Botões: `ctk.CTkButton`
- ✅ Scrollable: Layout em duas colunas com rolagem
- ✅ Validação de CNPJ/duplicidades integrada
- ✅ Upload de documentos integrado

**Campos implementados** (27 campos):
- Razão Social, CNPJ, Nome, WhatsApp
- Endereço, Bairro, Cidade, Estado, CEP
- Email, Telefone, Responsável, CPF Responsável
- AFE, CNAE, Observações Internas, Data Abertura
- Inscrição Municipal, Inscrição Estadual
- Certificado Digital, ANVISA, SNGPC, Observações
- Status do Cliente

### 3. **ClientesV2Toolbar** (toolbar.py)
**Completo**: 264 linhas, 100% CustomTkinter

- ✅ Busca: `ctk.CTkEntry` com debounce (400ms)
- ✅ Botões: `ctk.CTkButton` (Buscar, Limpar, Lixeira, Exportar)
- ✅ Filtros: `ctk.CTkOptionMenu` (Ordenação, Status)
- ✅ Tema: Tokens `SURFACE_DARK`, `TEXT_PRIMARY`
- ✅ Layout: Sem widgets Tkinter legado

### 4. **ClientesV2ActionBar** (actionbar.py)
**Completo**: 180 linhas, 100% CustomTkinter

- ✅ Botões de ação: `ctk.CTkButton`
  - Novo Cliente
  - Editar Cliente
  - Arquivos
  - Enviar Documentos
  - Excluir Cliente
- ✅ Tema: Tokens `SURFACE_DARK`

### 5. **ClientUploadDialog** (upload_dialog.py)
**Completo**: 382 linhas, 100% CustomTkinter

- ✅ Base: `ctk.CTkToplevel`
- ✅ Lista de arquivos: `ctk.CTkScrollableFrame`
- ✅ Visualização: `ctk.CTkTextbox`
- ✅ Seleção de arquivos via `tkinter.filedialog` (padrão)
- ✅ Validação e upload integrados

### 6. **ClientFilesDialog** (client_files_dialog.py)
**Placeholder**: 115 linhas, 100% CustomTkinter

- ✅ Base: `ctk.CTkToplevel`
- ⚠️ Implementação básica (a expandir)

---

## ⚠️ Pendências Críticas

### 1. **ttk.Treeview no ClientesV2** 🔴 PRIORITÁRIO

**Problema**: A tabela principal ainda usa `ttk.Treeview` (Tkinter padrão).

**Localização**: `src/modules/clientes_v2/view.py:142`

```python
self.tree = ttk.Treeview(
    parent,
    columns=columns,
    show="headings",
    selectmode="browse",
    style="RC.ClientesV2.Treeview",
)
```

**Por que não foi migrado**:
- `CTkTable` (biblioteca) não suporta todas as features necessárias
- `CTkTreeview` (custom widget) está em `src/ui/widgets/ctk_treeview.py` mas não foi integrado

**Opções de Migração**:

#### **Opção A - Usar CTkTreeview** ⭐ RECOMENDADO
**Vantagem**: Widget customizado já existe no projeto.

**Arquivo**: `src/ui/widgets/ctk_treeview.py`

**O que fazer**:
1. Importar `CTkTreeView` de `src.ui.widgets`
2. Substituir `ttk.Treeview` por `CTkTreeView`
3. Adaptar API (verificar diferenças de métodos)
4. Remover `tree_theme.py` (não será necessário)

**Exemplo de migração**:
```python
# ANTES
from tkinter import ttk
self.tree = ttk.Treeview(parent, columns=columns, ...)

# DEPOIS
from src.ui.widgets import CTkTreeView
self.tree = CTkTreeView(parent, columns=columns, ...)
```

**Impacto**: Médio (1-2 horas)
- Arquivos alterados: `view.py`, `tree_theme.py` (remover)
- Testes necessários: Seleção, ordenação, zebra, scroll

---

#### **Opção B - Manter ttk.Treeview** (temporário)
**Vantagem**: Funciona atualmente com tema configurado.

**Desvantagem**: Inconsistência visual com resto da UI CTk.

**Quando usar**: Se prazo for crítico e não houver tempo para migração completa.

**O que melhorar** (se manter):
- ✅ Já tem tema configurado em `tree_theme.py`
- ⚠️ Cores podem não combinar perfeitamente com tokens CTk
- ⚠️ Fonte não usa sistema CTk

---

#### **Opção C - Usar CTkScrollableFrame + Labels** (alternativa)
**Vantagem**: 100% CTk nativo, controle total.

**Desvantagem**: Muito trabalho manual, performance pode ser problema com muitos registros.

**Quando usar**: Apenas se CTkTreeView não funcionar.

---

### 2. **SubpastaDialog usa tkinter.Toplevel** ⚠️ MÉDIO

**Localização**: `src/modules/clientes/forms/client_subfolder_prompt.py`

**Problema**:
```python
class SubpastaDialog(tk.Toplevel):  # ❌ Tkinter padrão
```

**Migração**:
```python
class SubpastaDialog(ctk.CTkToplevel):  # ✅ CustomTkinter
```

**Arquivos afetados**:
- `client_subfolder_prompt.py` (declaração da classe)
- `client_form_upload_helpers.py:95` (instância)

**Impacto**: Baixo (30 minutos)
- Widgets internos já estão em CTk (botões usam `tk.Button` mas em frame)
- Apenas mudar herança e testar modal

---

### 3. **Botões no SubpastaDialog usam tk.Button** ⚠️ BAIXO

**Localização**: `src/modules/clientes/forms/client_subfolder_prompt.py:73-74`

```python
tk.Button(btns, text="OK", command=self._ok).pack(side="left", padx=4)
tk.Button(btns, text="Cancelar", command=self._cancel).pack(side="left", padx=4)
```

**Migração**:
```python
ctk.CTkButton(btns, text="OK", command=self._ok, width=80).pack(side="left", padx=4)
ctk.CTkButton(btns, text="Cancelar", command=self._cancel, width=100).pack(side="left", padx=4)
```

**Impacto**: Trivial (5 minutos)

---

## 🔧 Oportunidades de Melhoria

### 1. **Adicionar CTkAutocompleteEntry para campos** 💡

**Widget disponível**: `src/ui/widgets/ctk_autocomplete_entry.py`

**Onde usar**:
- **Cliente Editor**: Campo "Status do Cliente" (atualmente `CTkOptionMenu`)
- **Toolbar**: Campo de busca (autocompletar clientes recentes)
- **Cliente Editor**: Campo "Cidade", "Estado" (autocompletar)

**Benefício**: UX melhorada, menos cliques

**Exemplo**:
```python
from src.ui.widgets import CTkAutocompleteEntry

self.cidade_autocomplete = CTkAutocompleteEntry(
    parent,
    placeholder_text="Digite a cidade...",
    suggestions=["São Paulo", "Rio de Janeiro", "Belo Horizonte", ...],
)
```

---

### 2. **Usar CTkScrollableFrame no ClientEditorDialog** 💡

**Atualmente**: Layout fixo com grid

**Problema**: Não rola se janela for pequena (campos internos podem ficar cortados)

**Solução**: Envolver painéis left/right em `ctk.CTkScrollableFrame`

**Exemplo**:
```python
# Container scrollable para painéis
scrollable = ctk.CTkScrollableFrame(main_frame, fg_color="transparent")
scrollable.grid(row=0, column=0, sticky="nsew")

# Painéis dentro do scrollable
left_frame = ctk.CTkFrame(scrollable, fg_color=SURFACE, ...)
right_frame = ctk.CTkFrame(scrollable, fg_color=SURFACE, ...)
```

**Benefício**: Suporte a resoluções menores

---

### 3. **Adicionar CTkSection para agrupar campos** 💡

**Widget disponível**: `src/ui/widgets/ctk_section.py`

**Onde usar**: ClientEditorDialog - separar visualmente grupos de campos

**Exemplo**:
```python
from src.ui.widgets import CTkSection

# Seção "Dados Principais"
section_main = CTkSection(left_frame, title="Dados Principais", collapsible=True)
section_main.pack(fill="x", padx=5, pady=5)

# Campos dentro da seção
ctk.CTkEntry(section_main.content, ...).pack(...)
```

**Benefício**: UI mais organizada, seções colapsáveis (economia de espaço)

---

### 4. **Usar CTkDatePicker para data_abertura** 💡

**Widget disponível**: `src/ui/widgets/ctk_datepicker.py`

**Atualmente**: `ctk.CTkEntry` (texto livre)

**Problema**: Usuário pode digitar data inválida

**Solução**:
```python
from src.ui.widgets import CTkDatePicker

self.data_abertura_picker = CTkDatePicker(
    parent,
    placeholder_text="DD/MM/AAAA",
)
```

**Benefício**: Validação automática, calendário visual

---

## 🎨 Consistência de Tema

### Tokens Usados ✅

Todos os componentes ClientesV2 usam tokens centralizados:

**Arquivo**: `src/ui/ui_tokens.py`

```python
APP_BG = "#f5f5f5"          # Background geral
SURFACE = "#ffffff"         # Cards/painéis
SURFACE_DARK = "#2b2b2b"    # Toolbar/ActionBar
TEXT_PRIMARY = "#000000"    # Texto principal
TEXT_MUTED = "#6c757d"      # Texto secundário
BORDER = "#cccccc"          # Bordas
```

### Fontes

- ⚠️ **Inconsistência detectada**: Alguns lugares usam `("Segoe UI", 11)`, outros usam default
- 💡 **Recomendação**: Criar constantes de fonte em `ui_tokens.py`

```python
# Adicionar a ui_tokens.py
FONT_FAMILY = "Segoe UI"
FONT_SIZE_NORMAL = 11
FONT_SIZE_LARGE = 14
FONT_SIZE_SMALL = 9
```

---

## 🚀 Plano de Ação Recomendado

### Fase 1 - Crítico (1-2 dias) 🔴

1. **Migrar ttk.Treeview para CTkTreeView**
   - [ ] Estudar API de `CTkTreeView` em `src/ui/widgets/ctk_treeview.py`
   - [ ] Substituir em `view.py:142`
   - [ ] Adaptar métodos (insert, selection, delete)
   - [ ] Testar seleção, zebra, scroll
   - [ ] Remover `tree_theme.py` (não necessário)

2. **Migrar SubpastaDialog para CTkToplevel**
   - [ ] Mudar herança em `client_subfolder_prompt.py:24`
   - [ ] Trocar `tk.Button` por `ctk.CTkButton`
   - [ ] Testar modal e resultado

### Fase 2 - Melhorias (2-3 dias) 💡

3. **Adicionar CTkScrollableFrame no ClientEditorDialog**
   - [ ] Envolver painéis em scrollable frame
   - [ ] Testar em resoluções menores (1366x768)

4. **Adicionar CTkDatePicker para data_abertura**
   - [ ] Substituir entry por datepicker
   - [ ] Validação automática

5. **Adicionar CTkAutocompleteEntry**
   - [ ] Campo "Cidade" (sugestões de cidades brasileiras)
   - [ ] Campo "Estado" (27 estados)

### Fase 3 - Refinamentos (1 dia) 🎨

6. **Padronizar fontes**
   - [ ] Criar constantes em `ui_tokens.py`
   - [ ] Aplicar em todos os widgets

7. **Adicionar CTkSection (opcional)**
   - [ ] Agrupar campos por categoria
   - [ ] Seções colapsáveis

---

## 📝 Checklist de Validação

Após migrar `ttk.Treeview`:

```
□ Tabela renderiza corretamente
□ Zebra (linhas alternadas) funciona
□ Seleção única funciona
□ Duplo clique abre edição
□ Scroll vertical funciona
□ Ordenação por coluna funciona
□ Tema light/dark alterna corretamente
□ Performance com 1000+ registros é aceitável
□ Busca/filtros continuam funcionando
□ Exportar CSV funciona
```

Após migrar `SubpastaDialog`:

```
□ Dialog abre como modal
□ Botões OK/Cancelar funcionam
□ Enter envia (OK)
□ Escape cancela
□ Resultado retorna corretamente
□ Ícone da janela aparece
□ Centraliza na tela
```

---

## 🔍 Arquivos do Módulo Antigo Úteis

**Localização**: `src/modules/clientes/forms/_archived/`

### Arquivos Relevantes para Referência

1. **client_form_view_ctk.py** (632 linhas)
   - Layout completo do formulário legado em CTk
   - Pode servir de referência para campos faltando

2. **client_form_ui_builders_ctk.py** (244 linhas)
   - Helpers para criar pares Label+Entry CTk
   - Pode reutilizar funções

3. **client_picker.py** (161 linhas)
   - Dialog de seleção de cliente (pick mode)
   - ⚠️ Ainda usa `tk.Toplevel`, precisa migrar

### O Que NÃO Precisa Migrar

❌ **client_form.py** - Legado Tkinter puro (obsoleto)  
❌ **client_form_view.py** - Legado Tkinter puro (obsoleto)  
❌ **client_form_ui_builders.py** - Legado Tkinter puro (obsoleto)

---

## 📊 Estatísticas

### Widgets Customtkinter vs Tkinter

| Componente | CTk | ttk/tk | Status |
|------------|-----|--------|--------|
| ClientesV2Frame | ✅ | - | OK |
| ClientEditorDialog | ✅ | - | OK |
| ClientFilesDialog | ✅ | - | OK |
| ClientUploadDialog | ✅ | - | OK |
| ClientesV2Toolbar | ✅ | - | OK |
| ClientesV2ActionBar | ✅ | - | OK |
| **Treeview (lista)** | ❌ | ttk | **PENDENTE** |
| SubpastaDialog | ⚠️ | tk.Toplevel + Buttons | **PARCIAL** |

### Cobertura CustomTkinter

- **Diálogos**: 100% (5/5)
- **Componentes UI**: 100% (2/2)
- **Widgets principais**: 90% (1 pendente: Treeview)
- **Total**: ~95% migrado

---

## 🎯 Conclusão

O módulo **ClientesV2** está **majoritariamente migrado** para CustomTkinter, com apenas **2 pendências críticas**:

1. 🔴 **Treeview** (tabela principal) - Requer migração para `CTkTreeView`
2. ⚠️ **SubpastaDialog** - Requer migração para `CTkToplevel`

Todas as outras telas, diálogos e componentes estão 100% em CustomTkinter e seguem os padrões de tokens de UI definidos.

**Tempo estimado para completar migração**: 2-3 dias de trabalho focado.

**Prioridade**: ALTA (inconsistência visual entre tabela e resto da UI)

---

## 📎 Referências

- **UI Tokens**: `src/ui/ui_tokens.py`
- **CTkTreeView**: `src/ui/widgets/ctk_treeview.py`
- **CTkAutocompleteEntry**: `src/ui/widgets/ctk_autocomplete_entry.py`
- **CTkDatePicker**: `src/ui/widgets/ctk_datepicker.py`
- **CTkSection**: `src/ui/widgets/ctk_section.py`
- **Módulo Legado**: `src/modules/clientes/forms/_archived/`

---

**Gerado em**: 26 de janeiro de 2026  
**Autor**: Análise automatizada do módulo ClientesV2
