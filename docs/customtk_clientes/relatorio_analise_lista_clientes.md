# Análise da Lista de Clientes (READ-ONLY)

**Data da análise:** 12 de janeiro de 2026  
**Projeto:** v1.5.41  
**Componente alvo:** Tela de listagem de Clientes (MainScreenFrame)

---

## 1) Mapa do fluxo (arquivos e responsabilidades)

### Arquivos principais (caminhos completos)

| Arquivo | Responsabilidade | Classes/Funções principais |
|---------|------------------|---------------------------|
| `src/modules/clientes/view.py` | Entry point / alias da tela de clientes | `ClientesFrame` (herda `MainScreenFrame`) |
| `src/modules/clientes/views/main_screen_frame.py` | Frame principal - ciclo de vida, wiring, callbacks | `MainScreenFrame` (431 linhas) - herda mixins e `tb.Frame` |
| `src/modules/clientes/views/main_screen_ui_builder.py` | Builders da UI (toolbar, tree, footer, banner) | `build_toolbar()`, `build_tree_and_column_controls()`, `build_footer()`, `build_pick_mode_banner()`, `bind_main_events()` |
| `src/modules/clientes/views/main_screen_dataflow.py` | Carregamento, filtros, ordenação, refresh de dados | `MainScreenDataflowMixin`, `carregar()`, `carregar_async()`, `_refresh_rows()`, `_render_clientes()` |
| `src/modules/clientes/views/main_screen_events.py` | Handlers de eventos (clique, duplo clique, delete) | `MainScreenEventsMixin`, `_on_double_click()`, `_on_click()`, `_on_right_click()` |
| `src/modules/clientes/views/main_screen_constants.py` | Constantes de layout (dimensões, paddings, fontes) | `DEFAULT_COLUMN_ORDER`, `HEADER_CTRL_H`, `COLUMN_MIN_WIDTH`, etc. |
| `src/modules/clientes/views/toolbar.py` | Toolbar com busca, filtros e lixeira | `ClientesToolbar` |
| `src/modules/clientes/views/footer.py` | Footer com botões CRUD | `ClientesFooter` |
| `src/ui/components/lists.py` | Factory da Treeview de clientes | `create_clients_treeview()` |
| `src/ui/components/inputs.py` | Controles de busca/filtros | `create_search_controls()`, `SearchControls` |
| `src/ui/components/buttons.py` | Botões do footer | `create_footer_buttons()`, `FooterButtons` |
| `src/config/constants.py` | Larguras das colunas | `COL_ID_WIDTH`, `COL_RAZAO_WIDTH`, `COL_CNPJ_WIDTH`, etc. |
| `src/modules/clientes/viewmodel.py` | ViewModel com dados dos clientes | `ClientesViewModel`, `ClienteRow` |
| `src/modules/clientes/controllers/rendering_adapter.py` | Converte ClienteRow para valores/tags da Treeview | `build_row_values()`, `build_row_tags()` |
| `src/ui/theme.py` | Inicialização de tema e escala | `init_theme()`, `DEFAULT_SCALING = 1.25` |
| `src/utils/themes.py` | Gerenciamento de temas (dark/light) | `toggle_theme()`, `load_theme()`, `save_theme()` |

---

## 2) Como a lista é montada

### 2.1) Onde a tabela (Treeview) é criada

**Arquivo:** `src/ui/components/lists.py`  
**Função:** `create_clients_treeview()` (linhas 30-91)

```
tree = tb.Treeview(parent, columns=[c[0] for c in columns], show="headings")
```

A Treeview é instanciada usando **ttkbootstrap** (tb.Treeview) e configurada com 8 colunas.

### 2.2) Onde as colunas são definidas

**Arquivo:** `src/ui/components/lists.py` (linhas 40-50)

As colunas são definidas em uma tupla:
```python
columns = (
    ("ID", "ID", COL_ID_WIDTH, False),
    ("Razao Social", "Razão Social", COL_RAZAO_WIDTH, True),  # stretch
    ("CNPJ", "CNPJ", COL_CNPJ_WIDTH, False),
    ("Nome", "Nome", COL_NOME_WIDTH, False),
    ("WhatsApp", "WhatsApp", COL_WHATSAPP_WIDTH, False),
    ("Observacoes", "Observações", COL_OBS_WIDTH, True),  # stretch
    ("Status", "Status", COL_STATUS_WIDTH, False),
    ("Ultima Alteracao", "Última Alteração", COL_ULTIMA_WIDTH, False),
)
```

**Larguras definidas em:** `src/config/constants.py`
```python
COL_ID_WIDTH = 40
COL_RAZAO_WIDTH = 240
COL_CNPJ_WIDTH = 140
COL_NOME_WIDTH = 170
COL_WHATSAPP_WIDTH = 120
COL_OBS_WIDTH = 180
COL_STATUS_WIDTH = 200
COL_ULTIMA_WIDTH = 165
```

**Alinhamento:** Todas as colunas usam `anchor="center"` (linhas 56-57 de lists.py)

**Ordem de exibição controlada por:** `src/modules/clientes/views/main_screen_constants.py`
```python
DEFAULT_COLUMN_ORDER = (
    "ID", "Razao Social", "CNPJ", "Nome", "WhatsApp",
    "Observacoes", "Status", "Ultima Alteracao",
)
```

### 2.3) Onde e como as linhas são inseridas/atualizadas

**Arquivo:** `src/modules/clientes/views/main_screen_dataflow.py`  
**Função:** `_render_clientes()` (linhas 336-355)

```python
for row in rows:
    tags = build_row_tags(row)
    self.client_list.insert("", "end", values=self._row_values_masked(row), tags=tags)
```

**Função auxiliar:** `_refresh_rows()` (linhas 323-334) - atualiza linhas existentes sem recriar

**Conversão de dados:** `src/modules/clientes/controllers/rendering_adapter.py`
- `build_row_values()` - converte ClienteRow para tupla de valores
- `build_row_tags()` - determina tags visuais (ex: "has_obs" para clientes com observações)

### 2.4) Onde ocorrem filtros/ordenação/status/pesquisa

**Arquivo:** `src/modules/clientes/views/main_screen_dataflow.py`

| Funcionalidade | Método | Linha |
|---------------|--------|-------|
| Filtro de busca | `_buscar()` | ~278 |
| Filtro de status | `apply_filters()` | ~292 |
| Ordenação | `_sort_by()` | ~258 |
| Limpar busca | `_limpar_busca()` | ~287 |

**Controller headless:** `src/modules/clientes/views/main_screen_controller.py`
- `compute_filtered_and_ordered()` - aplica filtros e ordenação
- `FilterOrderInput` - dataclass com parâmetros de filtro

---

## 3) Pontos de melhoria (UI/UX) — Prioridade Alta/Média/Baixa

### 3.1) 🔴 Alta Prioridade: Lista Zebrada (Linhas Alternadas)

**Problema observado:**  
A lista de clientes NÃO possui alternância de cores nas linhas (zebra/striping). Todas as linhas têm o mesmo fundo, dificultando o acompanhamento visual horizontal em tabelas largas.

**Impacto:**  
- Legibilidade: ALTO - dificulta seguir dados de uma linha específica
- Usabilidade: MÉDIO - aumenta chance de erro ao ler informações
- Manutenção: BAIXO - implementação simples

**Onde ajustar:**  
- **Arquivo:** `src/modules/clientes/views/main_screen_dataflow.py`
- **Função:** `_render_clientes()` (linha ~336)
- **Arquivo auxiliar:** `src/modules/clientes/controllers/rendering_adapter.py`
- **Função:** `build_row_tags()` (linha ~125)

**Sugestão:**  
Adicionar tags `odd` e `even` alternadamente ao inserir linhas. Configurar estilos no `create_clients_treeview()` via `tree.tag_configure("odd", background="#f8f9fa")`.

**Risco/Efeitos colaterais:**  
- Zebra pode conflitar com highlight de seleção (precisa garantir que seleção sobreponha zebra)
- Tag `has_obs` (negrito azul) deve permanecer funcional junto com zebra
- Após filtro/ordenação, zebra precisa ser recalculada

---

### 3.2) 🟡 Média Prioridade: Tamanho de Fonte e Altura de Linha

**Problema observado:**  
A fonte da tabela segue o padrão do sistema (`TkDefaultFont` = Segoe UI 10 com scaling 1.25). Pode ser pequena para alguns usuários. Não há configuração específica de rowheight na Treeview.

**Impacto:**  
- Legibilidade: MÉDIO - fonte pode ser pequena para leitura prolongada
- Usabilidade: MÉDIO - linhas podem parecer "apertadas"
- Manutenção: BAIXO - ajuste simples de estilo

**Onde ajustar:**  
- **Tema/Fonte global:** `src/ui/theme.py` → `init_theme()` (linha 39-44)
- **Fonte específica da Treeview:** `src/ui/components/lists.py` → `create_clients_treeview()`
- **Altura de linha (rowheight):** Configurar via `ttk.Style().configure("Treeview", rowheight=XX)`

**Sugestão:**  
- Aumentar fonte em +1 ou +2 pontos apenas na Treeview (não globalmente)
- Configurar `rowheight` para 24-28px (padrão é ~20px)
- Manter padding vertical proporcional

**Risco/Efeitos colaterais:**  
- Alterar fonte global afeta toda a aplicação
- Rowheight muito alto reduz quantidade de linhas visíveis sem scroll
- Verificar se ícones/checkboxes continuam alinhados

---

### 3.3) 🟡 Média Prioridade: Alinhamento e Espaçamento de Colunas

**Problema observado:**  
Todas as colunas usam `anchor="center"`, incluindo "Razão Social" e "Observações" que são textos longos. Colunas de texto longo ficam melhor alinhadas à esquerda.

**Impacto:**  
- Legibilidade: MÉDIO - texto centralizado dificulta scan visual
- Usabilidade: BAIXO - não afeta funcionalidade
- Manutenção: BAIXO - mudança pontual

**Onde ajustar:**  
- **Arquivo:** `src/ui/components/lists.py`
- **Linhas:** 56-57 (loop de configuração de colunas)

**Sugestão:**  
```python
# Colunas de texto longo → anchor="w" (west/esquerda)
# Colunas numéricas/curtas → anchor="center"
text_columns = {"Razao Social", "Nome", "Observacoes"}
for key, _, width, can_stretch in columns:
    anch = "w" if key in text_columns else "center"
    tree.column(key, width=width, minwidth=width, anchor=anch, stretch=can_stretch)
```

**Risco/Efeitos colaterais:**  
- Mudança visual pode exigir ajuste de larguras
- Cabeçalhos permanecem centralizados (consistência)

---

### 3.4) 🟢 Baixa Prioridade: Controles "Ocultar/Mostrar" por Coluna

**Problema observado:**  
Os controles de visibilidade de colunas já existem (`_col_ctrls` em main_screen_ui_builder.py), mas o label alterna entre "Ocultar" e "Mostrar" dinamicamente. A UX poderia ser melhorada com ícones ou tooltips.

**Impacto:**  
- Legibilidade: BAIXO
- Usabilidade: BAIXO - funcionalidade já existe
- Manutenção: BAIXO

**Onde ajustar:**  
- **Arquivo:** `src/modules/clientes/views/main_screen_ui_builder.py`
- **Função:** `build_tree_and_column_controls()` (linhas 203-227)

**Sugestão:**  
- Adicionar ícone de olho (👁/👁‍🗨) em vez de texto
- Ou usar Checkbutton com label fixo (nome da coluna)

---

### 3.5) 🟢 Baixa Prioridade: Indicador Visual de Ordenação

**Problema observado:**  
Não há indicador visual no cabeçalho da coluna mostrando qual está ordenada e em qual direção (↑↓).

**Impacto:**  
- Legibilidade: BAIXO
- Usabilidade: MÉDIO - usuário não sabe qual ordenação está ativa
- Manutenção: MÉDIO - requer lógica adicional

**Onde ajustar:**  
- **Arquivo:** `src/modules/clientes/views/main_screen_dataflow.py`
- **Função:** `_on_order_changed()` (via main_screen_events.py)

**Sugestão:**  
Adicionar seta (▲/▼) ao texto do heading da coluna ativa.

---

## 4) Sugestão específica: Lista Zebrada

### Estratégia recomendada para ttkbootstrap.Treeview

A Treeview do Tkinter/ttkbootstrap suporta **tags** para estilização condicional de linhas. A estratégia é:

1. **Definir estilos para tags `odd` e `even`** no momento da criação da Treeview
2. **Aplicar tags alternadamente** ao inserir linhas
3. **Recalcular tags** após filtro/ordenação/refresh

### Ponto exato de implementação

**Arquivo 1:** `src/ui/components/lists.py`  
**Função:** `create_clients_treeview()` (após linha 70)

Adicionar configuração de tags:
```python
# Após tree.tag_configure("has_obs", font=bold_font, foreground=OBS_FG)
tree.tag_configure("odd", background="#f8f9fa")   # cinza claro
tree.tag_configure("even", background="#ffffff")  # branco
```

**Arquivo 2:** `src/modules/clientes/controllers/rendering_adapter.py`  
**Função:** `build_row_tags()` - NÃO é o local ideal pois não tem índice

**Arquivo 3 (RECOMENDADO):** `src/modules/clientes/views/main_screen_dataflow.py`  
**Função:** `_render_clientes()` (linha ~336)

Modificar o loop de inserção:
```python
for idx, row in enumerate(rows):
    base_tags = build_row_tags(row)
    zebra_tag = "odd" if idx % 2 else "even"
    all_tags = base_tags + (zebra_tag,)
    self.client_list.insert("", "end", values=self._row_values_masked(row), tags=all_tags)
```

### Manutenção da zebra após refresh/filtro/ordenação

- `_refresh_rows()` (linha 323) também precisa aplicar tags zebra
- `_render_clientes()` é chamado após cada filtro/ordenação, então zebra será recalculada automaticamente
- **Não é necessário** handler especial para ordenação

### Cores sugeridas (compatíveis com tema flatly)

| Tag | Background | Observação |
|-----|------------|------------|
| `even` | `#ffffff` | Branco (padrão) |
| `odd` | `#f8f9fa` | Cinza muito claro |
| Seleção | `#0d6efd` (automático) | Azul do Bootstrap |

---

## 5) Sugestão específica: Fonte e altura de linha

### 5.1) Onde definir fonte global vs. fonte só da tabela

**Fonte global (toda a aplicação):**  
- **Arquivo:** `src/ui/theme.py`
- **Função:** `init_theme()` (linhas 39-44)
- **Configuração atual:**
  ```python
  base = 10
  size = int(round(base * scaling))  # ~12 com scaling 1.25
  f.configure(family="Segoe UI", size=size)
  ```

**Fonte específica da Treeview:**  
- **Arquivo:** `src/ui/components/lists.py`
- **Função:** `create_clients_treeview()` (após linha 52)
- **Adicionar:**
  ```python
  # Configurar fonte específica da Treeview
  style = tb.Style()
  style.configure("Treeview", font=("Segoe UI", 11))  # +1 ponto
  style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))
  ```

### 5.2) Onde ajustar altura/padding (rowheight)

**Arquivo:** `src/ui/components/lists.py`  
**Função:** `create_clients_treeview()` (início)

Adicionar configuração de rowheight via Style:
```python
style = tb.Style()
style.configure("Treeview", rowheight=26)  # padrão é ~20
```

**Alternativa global:** `src/ui/theme.py` → `init_theme()`

### 5.3) Valores recomendados (alteração "leve")

| Parâmetro | Valor atual | Valor sugerido | Mudança |
|-----------|-------------|----------------|---------|
| Fonte Treeview | 10pt (via TkDefaultFont) | 11pt | +1pt |
| Rowheight | ~20px (padrão ttk) | 26px | +6px |
| Fonte cabeçalho | 10pt | 11pt bold | +1pt |

**Não recomendado:** Aumentar mais que +2pt na fonte, pois pode desalinhar ícones e reduzir muito as linhas visíveis.

---

## 6) Checklist rápido de implementação (para depois)

### Lista Zebrada

1. [ ] Abrir `src/ui/components/lists.py`
2. [ ] Na função `create_clients_treeview()`, após `tree.tag_configure("has_obs", ...)`, adicionar:
   - `tree.tag_configure("odd", background="#f8f9fa")`
   - `tree.tag_configure("even", background="#ffffff")`
3. [ ] Abrir `src/modules/clientes/views/main_screen_dataflow.py`
4. [ ] Na função `_render_clientes()`, modificar o loop para:
   - Usar `enumerate(rows)` para obter índice
   - Adicionar tag `"odd"` ou `"even"` baseado em `idx % 2`
   - Concatenar com tags existentes de `build_row_tags()`
5. [ ] Repetir ajuste em `_refresh_rows()` se necessário
6. [ ] Testar com filtros e ordenação para garantir que zebra se mantém correta
7. [ ] Verificar que highlight de seleção sobrepõe zebra corretamente

### Fonte e Altura de Linha

1. [ ] Abrir `src/ui/components/lists.py`
2. [ ] No início de `create_clients_treeview()`, adicionar:
   - `style = tb.Style()`
   - `style.configure("Treeview", font=("Segoe UI", 11), rowheight=26)`
   - `style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))`
3. [ ] Testar com diferentes quantidades de dados para verificar scroll
4. [ ] Verificar alinhamento de checkboxes (se houver)
5. [ ] Testar em diferentes resoluções de tela

### Alinhamento de Colunas

1. [ ] Abrir `src/ui/components/lists.py`
2. [ ] Na função `create_clients_treeview()`, modificar o loop de configuração de colunas
3. [ ] Definir set de colunas que devem usar `anchor="w"` (texto longo)
4. [ ] Aplicar `anchor="w"` apenas para: Razao Social, Nome, Observacoes
5. [ ] Manter `anchor="center"` para: ID, CNPJ, WhatsApp, Status, Ultima Alteracao
6. [ ] Testar visualmente com dados reais

---

## Anexo: Buscas realizadas

| Busca | Resultado |
|-------|-----------|
| `cliente\|clientes\|customer` (regex) | 20+ matches - identificou arquivos do módulo |
| `**/cliente*` (file search) | `src/core/services/clientes_service.py` |
| `**/client*` (file search) | 20 arquivos no módulo clientes |
| `create_clients_treeview` (grep) | 7 matches - factory da Treeview |
| `tag_configure\|odd\|even\|zebra` (grep) | Nenhum match em código fonte (apenas licenças) |
| `Style\|theme_use\|rowheight` (grep) | 20+ matches - tema e estilos |

---

**Fim do relatório.**
