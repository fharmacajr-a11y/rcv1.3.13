# DevLog - Coverage Round CF-3: Extração de Lógica do Cartão CNPJ

**Data**: 2025-12-01  
**Objetivo**: Extrair lógica de preenchimento via Cartão CNPJ do `client_form.py` para módulo headless testável  
**Status**: ✅ Completo

---

## 📋 Contexto

Terceira fase da refatoração do formulário de clientes, focada na extração da funcionalidade de preenchimento automático via Cartão CNPJ. Esta funcionalidade permite ao usuário selecionar uma pasta contendo um PDF do Cartão CNPJ, que é então processado para extrair CNPJ e Razão Social.

### Fases Anteriores
- **CF-1**: Extração de lógica de salvamento → `client_form_actions.py` (13 testes)
- **CF-2**: Extração de lógica de upload → `client_form_upload_actions.py` (12 testes)
- **CF-3**: Extração de lógica de Cartão CNPJ → `client_form_cnpj_actions.py` (14 testes)

---

## 🎯 Objetivos Alcançados

### 1. Análise do Fluxo Atual
**Arquivo**: `src/modules/clientes/forms/client_form.py`

Fluxo identificado:
```
_on_cartao_cnpj() [linha 648]
  ↓ proteção reentrância (_cnpj_busy flag)
  ↓ desabilita botão
  ↓ chama preencher_via_pasta(ents)
  ↓ marca formulário como modificado
  ↓ reabilita botão
```

**Arquivo**: `src/ui/forms/actions.py` (linhas 50-84)

Função `preencher_via_pasta()`:
1. Abre diálogo de seleção de pasta (`filedialog.askdirectory`)
2. Chama `extrair_dados_cartao_cnpj_em_pasta(base_dir)`
3. Exibe aviso se nenhum dado for encontrado
4. Preenche campos "Razão Social" e "CNPJ" no formulário

**Arquivo**: `src/modules/clientes/service.py` (linhas 116-165)

Serviço `extrair_dados_cartao_cnpj_em_pasta()`:
- Busca PDF do Cartão CNPJ na pasta
- Usa classificação e extração de texto de PDF
- Retorna `{"cnpj": str|None, "razao_social": str|None}`

### 2. Criação do Módulo Headless
**Arquivo**: `src/modules/clientes/forms/client_form_cnpj_actions.py` (150 linhas)

#### Protocols Definidos:
```python
class MessageSink(Protocol):
    """Exibição de mensagens (warnings, info)"""
    def warn(self, title: str, message: str) -> None: ...
    def info(self, title: str, message: str) -> None: ...

class FormFieldSetter(Protocol):
    """Preenchimento de campos do formulário"""
    def set_value(self, field_name: str, value: str) -> None: ...

class DirectorySelector(Protocol):
    """Seleção de diretório"""
    def select_directory(self, title: str) -> str | None: ...
```

#### Tipos de Dados:
```python
@dataclass
class CnpjExtractionResult:
    """Resultado da extração de dados do Cartão CNPJ"""
    ok: bool
    base_dir: str | None
    cnpj: str | None = None
    razao_social: str | None = None
    error_message: str | None = None

@dataclass
class CnpjActionDeps:
    """Dependências externas para ações de Cartão CNPJ"""
    messages: MessageSink
    field_setter: FormFieldSetter
    directory_selector: DirectorySelector
```

#### Funções Principais:
```python
def extract_cnpj_from_directory(base_dir: str) -> CnpjExtractionResult:
    """Extrai dados do Cartão CNPJ usando serviço"""

def apply_cnpj_data_to_form(result: CnpjExtractionResult, setter: FormFieldSetter) -> None:
    """Preenche campos com dados extraídos (normaliza CNPJ para apenas dígitos)"""

def handle_cartao_cnpj_action(deps: CnpjActionDeps) -> CnpjExtractionResult:
    """Fluxo completo: selecionar pasta → extrair → preencher → exibir mensagens"""
```

### 3. Adaptação do UI Handler
**Arquivo**: `src/modules/clientes/forms/client_form.py` (linhas 648-693)

Implementação dos adaptadores Tkinter:
```python
def _on_cartao_cnpj() -> None:
    """Handler com bloqueio de múltiplos cliques usando módulo headless CF-3."""
    if _cnpj_busy[0]:
        return
    _cnpj_busy[0] = True
    try:
        # Desabilita botão...

        # --- CF-3: Delegação para módulo headless ---
        from src.modules.clientes.forms.client_form_cnpj_actions import (
            CnpjActionDeps,
            handle_cartao_cnpj_action,
        )

        # Adaptadores
        class _TkMessageSink:
            def warn(self, title: str, message: str) -> None:
                messagebox.showwarning(title, message, parent=win)
            def info(self, title: str, message: str) -> None:
                messagebox.showinfo(title, message, parent=win)

        class _TkDirectorySelector:
            def select_directory(self, title: str) -> str | None:
                return filedialog.askdirectory(title=title, parent=win)

        class _TkFormFieldSetter:
            def set_value(self, field_name: str, value: str) -> None:
                if field_name in ents:
                    widget = ents[field_name]
                    widget.delete(0, "end")
                    widget.insert(0, value)

        deps = CnpjActionDeps(
            messages=_TkMessageSink(),
            field_setter=_TkFormFieldSetter(),
            directory_selector=_TkDirectorySelector(),
        )

        result = handle_cartao_cnpj_action(deps)
        if result.ok:
            state.mark_dirty()
    finally:
        # Reabilita botão...
```

### 4. Wrapper de Compatibilidade
**Arquivo**: `src/modules/clientes/forms/client_form.py` (linhas 119-128)

Adicionado wrapper para manter compatibilidade com testes Round 14:
```python
def preencher_via_pasta(*args: Any, **kwargs: Any) -> Any:
    """
    Wrapper de compatibilidade para preencher formulário via pasta (Cartão CNPJ).
    Delegado para src.ui.forms.actions.preencher_via_pasta.
    """
    from src.ui.forms.actions import preencher_via_pasta as _impl
    return _impl(*args, **kwargs)
```

---

## 🧪 Suite de Testes

### Arquivo: `tests/modules/clientes/forms/test_client_form_cnpj_actions_cf3.py`

**Total**: 14 testes, 100% passando

#### Fakes Implementados:
```python
class FakeMessageSink:
    """Captura warnings e infos exibidos"""

class FakeFormFieldSetter:
    """Captura valores setados no formulário"""

class FakeDirectorySelector:
    """Simula seleção de diretório com controle total"""
```

#### Fixtures de Mock:
- `mock_service_success`: Retorna CNPJ e razão social
- `mock_service_no_data`: Retorna campos vazios
- `mock_service_partial_data`: Retorna apenas CNPJ
- `mock_service_exception`: Simula erro no serviço

#### Cobertura de Testes:

**Testes de Extração (`extract_cnpj_from_directory`):**
1. ✅ `test_extract_cnpj_success` - Extração bem-sucedida
2. ✅ `test_extract_cnpj_no_data` - Nenhum dado encontrado
3. ✅ `test_extract_cnpj_partial_data_ok` - Apenas CNPJ (sem razão social)
4. ✅ `test_extract_cnpj_exception` - Exceção no serviço

**Testes de Aplicação ao Form (`apply_cnpj_data_to_form`):**
5. ✅ `test_apply_cnpj_data_full` - CNPJ + razão social (normaliza CNPJ)
6. ✅ `test_apply_cnpj_data_only_cnpj` - Apenas CNPJ
7. ✅ `test_apply_cnpj_data_only_razao` - Apenas razão social
8. ✅ `test_apply_cnpj_data_not_ok` - Não aplica se result.ok=False

**Testes de Fluxo Completo (`handle_cartao_cnpj_action`):**
9. ✅ `test_handle_cartao_cnpj_user_cancel` - Usuário cancela seleção
10. ✅ `test_handle_cartao_cnpj_success` - Fluxo completo OK
11. ✅ `test_handle_cartao_cnpj_no_data_warning` - Exibe warning quando não encontra dados
12. ✅ `test_handle_cartao_cnpj_exception_warning` - Exibe warning em exceção
13. ✅ `test_handle_cartao_cnpj_partial_data_fills_form` - Preenche com dados parciais
14. ✅ `test_handle_cartao_cnpj_directory_selector_title` - Valida título do diálogo

---

## ✅ Validações de Qualidade

### Ruff (Linting)
```bash
$ python -m ruff check src/modules/clientes/forms/client_form_cnpj_actions.py \
    tests/modules/clientes/forms/test_client_form_cnpj_actions_cf3.py \
    src/modules/clientes/forms/client_form.py
```
**Resultado**: ✅ All checks passed!

### Bandit (Segurança)
```bash
$ python -m bandit -c .bandit -r src/modules/clientes/forms/client_form_cnpj_actions.py
```
**Resultado**: ✅ No issues identified (150 linhas escaneadas)

### Suite Completa de Testes
```bash
$ python -m pytest tests/unit/modules/clientes/forms/ tests/modules/clientes/forms/ -v
```
**Resultado**: ✅ **211 testes passando**

Breakdown:
- CF-1 (save): 13 testes ✅
- CF-2 (upload): 12 testes ✅
- CF-3 (cnpj): 14 testes ✅
- Round 10-14: 172 testes ✅

---

## 📊 Impacto

### Arquivos Criados
1. `src/modules/clientes/forms/client_form_cnpj_actions.py` (150 linhas)
2. `tests/modules/clientes/forms/test_client_form_cnpj_actions_cf3.py` (390 linhas)

### Arquivos Modificados
1. `src/modules/clientes/forms/client_form.py`:
   - Removido import `preencher_via_pasta` (evita F401)
   - Adicionado wrapper de compatibilidade `preencher_via_pasta()`
   - Refatorado `_on_cartao_cnpj()` com adaptadores (46 linhas → 69 linhas)

### Métricas
- **Testes adicionados**: 14
- **Total de testes**: 211 (100% passando)
- **Cobertura estimada**: ~95% do módulo CF-3
- **Zero regressões**: Nenhuma funcionalidade quebrada

---

## 🔑 Destaques Técnicos

### 1. Normalização de CNPJ
O módulo headless normaliza CNPJs para apenas dígitos:
```python
def apply_cnpj_data_to_form(result: CnpjExtractionResult, setter: FormFieldSetter) -> None:
    if result.cnpj:
        cnpj_digits = "".join(ch for ch in result.cnpj if ch.isdigit())
        setter.set_value("CNPJ", cnpj_digits)
```

Entrada: `"12.345.678/0001-90"` → Saída: `"12345678000190"`

### 2. Separação de Responsabilidades
- **Módulo headless**: Lógica de negócio, orquestração, validação
- **UI adapters**: Bridge entre Tkinter e módulo headless
- **Serviço**: Extração de dados do PDF (já existente)

### 3. Protocolo-Based Design
Permite testar sem dependências de UI:
```python
# Em teste: Fake com controle total
selector = FakeDirectorySelector(directory="/fake/path")

# Em produção: Adaptador Tkinter real
class _TkDirectorySelector:
    def select_directory(self, title: str) -> str | None:
        return filedialog.askdirectory(title=title, parent=win)
```

### 4. Tratamento de Erros Robusto
- Cancelamento pelo usuário (retorna `ok=False`, sem warning)
- Dados não encontrados (retorna `ok=False`, exibe warning)
- Exceção no serviço (captura, loga, retorna `ok=False`, exibe warning)

---

## 🎓 Lições Aprendidas

### 1. Padrão de Wrapper Consolidado
Estabelecido em CF-1/CF-2, aplicado com sucesso em CF-3:
```python
def preencher_via_pasta(*args: Any, **kwargs: Any) -> Any:
    """Wrapper de compatibilidade..."""
    from src.ui.forms.actions import preencher_via_pasta as _impl
    return _impl(*args, **kwargs)
```
**Benefício**: Mantém API pública estável sem F401 errors.

### 2. Mock de Imports Internos
Quando a função usa `from ... import` internamente, o mock deve ser aplicado no módulo de origem:
```python
# ❌ Incorreto (AttributeError)
@patch("src.modules.clientes.forms.client_form_cnpj_actions.extrair_dados_cartao_cnpj_em_pasta")

# ✅ Correto
@patch("src.modules.clientes.service.extrair_dados_cartao_cnpj_em_pasta")
```

### 3. Adapter Classes Inline
Para adaptadores UI simples, classes inline no handler são suficientes:
```python
class _TkMessageSink:
    def warn(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message, parent=win)
```
**Vantagem**: Menos arquivos, closure sobre `win`, simplicidade.

### 4. Result Objects para Comunicação
`CnpjExtractionResult` serve como contrato entre camadas:
- Sucesso/falha (`ok: bool`)
- Dados extraídos (`cnpj`, `razao_social`)
- Contexto (`base_dir`)
- Mensagem de erro (`error_message`)

---

## 🚀 Próximos Passos Potenciais

1. **CF-4**: Extrair lógica de navegação de senhas (`open_senhas_for_cliente`)
2. **CF-5**: Extrair lógica de duplicatas (`checar_duplicatas_para_form`)
3. **CF-6**: Extrair validação de campos antes de salvar
4. **Consolidação**: Revisar todos os módulos CF-* e criar documentação arquitetural

---

## 📝 Checklist de Validação

- [x] Módulo headless criado (`client_form_cnpj_actions.py`)
- [x] Protocols definidos para abstração de UI
- [x] Adaptadores Tkinter implementados
- [x] 14 testes criados (100% passando)
- [x] Wrapper de compatibilidade adicionado
- [x] Ruff: Zero warnings/erros
- [x] Bandit: Zero issues de segurança
- [x] Suite completa: 211 testes passando
- [x] Zero regressões em funcionalidades existentes
- [x] Documentação (devlog) gerada

---

## 🎉 Conclusão

**CF-3 foi concluído com sucesso!** A funcionalidade de preenchimento via Cartão CNPJ agora está completamente testável de forma independente da UI, mantendo 100% de compatibilidade com código existente.

**Total acumulado:**
- **Módulos headless**: 3 (CF-1: save, CF-2: upload, CF-3: cnpj)
- **Testes adicionados**: 39 (13+12+14)
- **Taxa de sucesso**: 211/211 testes (100%)

A arquitetura do formulário de clientes está progressivamente mais modular, testável e manutenível. 🚀
