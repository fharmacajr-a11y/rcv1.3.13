# Implementação de Theme Light/Dark no Módulo Clientes

## Resumo das Alterações

Implementação de alternância Light/Dark **SOMENTE** no módulo Clientes usando CustomTkinter como controlador de tema, mantendo 100% de compatibilidade com outros módulos.

## Arquivos Modificados

### 1. Dependências

#### `requirements.txt` e `requirements.in`
- **O que**: Adicionado `customtkinter>=5.2.0`
- **Por que**: Necessário para controle de tema Light/Dark e widget CTkSwitch
- **Impacto**: Nenhum em outros módulos (import com fallback)

#### `rcgestor.spec` (PyInstaller)
- **O que**: Adicionado `datas += collect_data_files("customtkinter")`
- **Por que**: CustomTkinter precisa de assets (.json/.otf) coletados manualmente
- **Impacto**: Aumenta ligeiramente o tamanho do executável

### 2. Novo Módulo - Theme Manager

#### `src/modules/clientes/appearance.py` (NOVO)
**Responsabilidades**:
- Gerenciamento de modo Light/Dark
- Persistência de preferência em arquivo JSON (`~/.regularizeconsultoria/clientes_appearance.json` ou `%APPDATA%\RegularizeConsultoria\clientes_appearance.json`)
- Paletas de cores para cada modo
- Configuração de estilos TTK específicos do módulo Clientes:
  - `Clientes.Treeview` e `Clientes.Treeview.Heading`
  - `Search.TEntry`
  - `Filtro.TCombobox`

**API Principal**:
```python
manager = ClientesThemeManager()
mode = manager.load_mode()  # "light" ou "dark"
manager.apply(mode, style)  # Aplica ao ttk.Style
manager.toggle(style)       # Alterna e salva
palette = manager.get_palette()  # Dict com cores
```

**Fallback Seguro**: Se CustomTkinter não estiver disponível, `HAS_CUSTOMTKINTER = False` e nenhuma funcionalidade crítica quebra.

### 3. Adaptações em Componentes UI

#### `src/ui/components/lists.py`
**Novas Funções**:
- `reapply_clientes_treeview_style()`: Reaplica estilos da Treeview dinamicamente
- `reapply_clientes_treeview_tags()`: Reaplica tags de zebra (even/odd)

**Por que**: Permite atualizar cores da Treeview após mudança de tema sem recarregar dados.

#### `src/ui/components/inputs.py`
**Modificações em `create_search_controls()`**:
- **Novo parâmetro**: `theme_palette: dict[str, str] | None = None`
- **Comportamento**: Se `theme_palette` fornecido, usa essas cores ao invés de lookup do tema global
- **Compatibilidade**: 100% retrocompatível (parâmetro opcional)

### 4. Integração no ClientesFrame

#### `src/modules/clientes/view.py`
**Classe `ClientesFrame`** agora:
1. **Inicializa theme manager** antes de construir UI
2. **Carrega modo salvo** e aplica CustomTkinter appearance mode
3. **Após UI construída**:
   - Aplica estilos TTK específicos
   - Insere CTkSwitch visível na toolbar (à direita)
   - Aplica cores aos widgets tk.Frame locais
4. **Callback de toggle**:
   - Alterna modo (light ↔ dark)
   - Reaplica estilos TTK
   - Atualiza cores de widgets
   - Re-aplica zebra na Treeview
   - Salva preferência

**Compatibilidade**: Herda de `MainScreenFrame`, mantendo todos os métodos/atributos esperados pelo router.

### 5. Testes

#### `tests/modules/test_clientes_theme_smoke.py` (NOVO)
Smoke tests que verificam:
- Imports funcionam
- Theme manager pode ser instanciado
- Operações básicas (load/save/toggle)
- `create_search_controls` aceita `theme_palette`

## Como Funciona

### Fluxo de Inicialização
1. `ClientesFrame.__init__()` cria `ClientesThemeManager`
2. Manager carrega modo salvo (default: "light")
3. Aplica `customtkinter.set_appearance_mode(mode)`
4. `super().__init__()` constrói toda a UI (MainScreenFrame)
5. Após UI pronta:
   - Obtém `tb.Style()` do ttkbootstrap
   - Chama `manager.apply(mode, style)` para configurar estilos específicos
   - Insere CTkSwitch na toolbar
   - Aplica cores aos widgets locais

### Fluxo de Alternância
1. Usuário clica no CTkSwitch
2. Callback `_on_theme_toggle()` chama `manager.toggle(style)`
3. Manager:
   - Alterna modo (light → dark ou vice-versa)
   - Chama `customtkinter.set_appearance_mode(new_mode)`
   - Reconfigura estilos TTK específicos
   - Salva preferência em disco
4. ClientesFrame:
   - Chama `_apply_theme_to_widgets()` para atualizar backgrounds
   - Chama `_reapply_treeview_colors()` para atualizar zebra

## Estilos Isolados (Não Afeta Outros Módulos)

Apenas estes estilos são modificados:
- `Clientes.Treeview` ✓
- `Clientes.Treeview.Heading` ✓
- `Search.TEntry` ✓ (usado apenas em Clientes)
- `Filtro.TCombobox` ✓ (usado apenas em Clientes)

**Outros módulos não são afetados** porque:
- Usam seus próprios estilos ou o tema ttkbootstrap global
- CustomTkinter `set_appearance_mode` não afeta Tk/ttk widgets diretamente

## Paletas de Cores

### Light Mode
- Background: `#FFFFFF`
- Foreground: `#000000`
- Entry BG: `#F5F5F5`
- Tree Even Row: `#FFFFFF`
- Tree Odd Row: `#E8E8E8` (zebra visível)

### Dark Mode
- Background: `#1E1E1E`
- Foreground: `#E0E0E0`
- Entry BG: `#2D2D2D`
- Tree Even Row: `#252525`
- Tree Odd Row: `#303030` (zebra visível)

## Extensibilidade Futura

Para migrar outros módulos:
1. Criar theme manager específico (ou reutilizar `ClientesThemeManager`)
2. Definir estilos prefixados (`NomeModulo.Treeview`, etc)
3. Inserir toggle no módulo
4. Aplicar palette aos widgets do módulo

## Instalação da Dependência

```bash
pip install customtkinter>=5.2.0
# ou
pip install -r requirements.txt
```

## Build do Executável

```bash
pyinstaller rcgestor.spec
```

O spec já está configurado para coletar assets do customtkinter.

## Checklist de Entrega ✓

- [x] customtkinter adicionado às dependências
- [x] rcgestor.spec coleta datas do customtkinter
- [x] Theme manager em `src/modules/clientes/appearance.py`
- [x] Toggle visível na toolbar do Clientes
- [x] Alternar Light/Dark muda cores do módulo Clientes
- [x] Persistência do modo (reabre app e mantém)
- [x] Sem alterações em outros módulos
- [x] Smoke tests criados

## Smoke Test Manual

1. Abrir app
2. Entrar em Clientes
3. Verificar que há um switch "Tema: [ ] Escuro" à direita da toolbar
4. Alternar tema:
   - Background muda
   - Treeview muda (zebra permanece visível)
   - Entry/Combobox mudam
5. Fechar e reabrir app → tema persiste
6. Buscar, ordenar, selecionar, abrir lixeira → tudo funciona normal
7. Navegar para outras telas → tema não afeta elas

## Observações de Design

- **Fallback Seguro**: Se CustomTkinter falhar, app funciona normal sem tema
- **Isolamento**: Apenas prefixos `Clientes.*`, `Search.TEntry`, `Filtro.TCombobox`
- **Performance**: Alternância é instantânea (apenas reconfigura estilos)
- **UX**: Toggle visível e intuitivo, estado salvo automaticamente
