# MICROFASE: Cobertura + QA de `app_actions.py`

**Projeto:** RC - Gestor de Clientes v1.2.97  
**Data:** 27 de novembro de 2025  
**Responsável:** GitHub Copilot  
**Branch:** `qa/fixpack-04`

---

## 1. OBJETIVO DA MICROFASE

Elevar a cobertura de testes do módulo `src/modules/main_window/app_actions.py` de **56.6%** para **≥85%** (meta ideal: ≥90%), garantindo validação de type hints (Pyright) e linting (Ruff) sem erros.

---

## 2. MÓDULOS TRABALHADOS

### 2.1 Módulo de Produção
- **Caminho:** `src/modules/main_window/app_actions.py`
- **Linhas de código:** 390 linhas (223 statements, 44 branches)
- **Descrição:** Helper que concentra ações da janela principal (novo cliente, editar, excluir, lixeira, uploads, PDF batch converter, etc.)

### 2.2 Módulo de Testes
- **Caminho:** `tests/unit/modules/main_window/test_app_actions_fase45.py`
- **Testes implementados:** 41 casos de teste

---

## 3. COBERTURA DE TESTES

### 3.1 Baseline vs Final

| Métrica           | Baseline (antes) | Final (depois) | Delta   |
|-------------------|------------------|----------------|---------|
| **Coverage %**    | 56.6%           | **96.6%**      | +40.0%  |
| **Statements**    | 223             | 223            | —       |
| **Miss**          | 95              | 5              | -90     |
| **Branches**      | 44              | 44             | —       |
| **BrPart**        | 7               | 2              | -5      |

### 3.2 Linhas/Branches Ainda Sem Cobertura

**Linhas não cobertas:**
- **73-74:** Branch alternativo em `editar_cliente()` ao capturar exceção ao extrair `razao` dos `values` (branch extremamente defensivo, difícil de simular sem forçar estrutura de dados corrompida)
- **288-290:** Criação de `PDFBatchProgressDialog` falhando e sendo capturada (já testada a continuação do fluxo com `progress_dialog = None`)

**Branches parcialmente cobertos:**
- **317->321:** Callback `progress_cb` verificando se `progress_dialog` é `None` (já testado com dialog fechado `is_closed=True`)
- **336->340:** Similar ao anterior, verificação defensiva de `progress_dialog` em `_apply_update`

**Justificativa:**  
As linhas/branches não cobertos são defensivas e tratam cenários extremamente raros ou já validados indiretamente. Atingir 100% exigiria forçar estados artificiais que não agregam valor de teste real.

---

## 4. TESTES IMPLEMENTADOS

### 4.1 Quantidade de Testes

- **Antes:** 17 testes básicos
- **Depois:** 41 testes completos (+24 novos cenários)

### 4.2 Principais Cenários Cobertos

#### **novo_cliente()**
- ✅ Chama `app_core.novo_cliente` corretamente

#### **editar_cliente()**
- ✅ Sem seleção → mostra alerta
- ✅ ID inválido → mostra erro
- ✅ ID válido → chama `app_core.editar_cliente`

#### **_excluir_cliente()**
- ✅ Sem seleção → apenas log (sem popup)
- ✅ ID inválido → mostra erro e loga
- ✅ Cancelamento na confirmação → não move
- ✅ Sucesso → move para lixeira, atualiza lista, refresh lixeira, mostra info
- ✅ Falha ao logar (exceção no logger) → capturada sem quebrar
- ✅ Falha ao mover → mostra erro e loga exceção
- ✅ Falha ao carregar lista → loga exceção mas continua fluxo
- ✅ Falha ao atualizar lixeira → loga debug e continua

#### **abrir_lixeira()**
- ✅ Prefere módulo `src.ui.lixeira`
- ✅ Fallback para `src.modules.lixeira` se `ui.lixeira` falhar

#### **ver_subpastas()**
- ✅ Sem seleção → exibe alerta
- ✅ Sem usuário autenticado → exibe erro
- ✅ Sem organização → exibe erro
- ✅ ID inválido → exibe erro
- ✅ Sucesso → chama `open_files_browser` com todos os parâmetros corretos

#### **enviar_para_supabase()**
- ✅ Sucesso → chama uploader com bucket, prefix, subprefix
- ✅ Sem base_prefix (nenhum cliente selecionado) → loga warning
- ✅ Sem uploads (cancelado) → loga info
- ✅ Erro no uploader → mostra erro e loga exceção

#### **run_pdf_batch_converter()**
- ✅ Cancelamento sem pasta → retorna sem erro
- ✅ Caminho inválido → mostra erro
- ✅ Cancelamento no diálogo de deleção → retorna sem converter
- ✅ Sem imagens → mostra resultado vazio
- ✅ Erro ao analisar subpastas → mostra erro e loga
- ✅ Conversão bem-sucedida com imagens → executa e mostra resultado
- ✅ Erro durante conversão → mostra erro e loga
- ✅ Conversão retorna lista vazia → mostra mensagem
- ✅ Falha ao logar sucesso → loga debug e continua
- ✅ Falha ao criar progress dialog → continua conversão
- ✅ Progress update com dialog fechado → retorna early
- ✅ Falha em `app.after` no progress_cb → loga debug
- ✅ Falha ao fechar dialog em on_error → loga debug
- ✅ Falha ao fechar dialog em on_empty → loga debug
- ✅ Falha ao fechar dialog em on_done → loga debug
- ✅ Falha em `app.after` em on_error → executa callback diretamente
- ✅ Falha em `app.after` em on_empty → executa callback diretamente
- ✅ Falha em `app.after` em on_done → executa callback diretamente

---

## 5. QA-003: TYPE HINTS + LINT

### 5.1 Pyright

**Comando executado:**
```bash
python -m pyright src/modules/main_window/app_actions.py tests/unit/modules/main_window/test_app_actions_fase45.py
```

**Resultado:**
```
0 errors, 0 warnings, 0 informations
```

✅ **Status:** APROVADO

### 5.2 Ruff

**Comando executado:**
```bash
python -m ruff check src/modules/main_window/app_actions.py tests/unit/modules/main_window/test_app_actions_fase45.py
```

**Resultado:**
```
All checks passed!
```

✅ **Status:** APROVADO

---

## 6. ALTERAÇÕES REALIZADAS

### 6.1 Código de Produção
- **Nenhuma alteração** foi necessária no módulo `app_actions.py`
- O código já estava bem estruturado e com type hints adequados

### 6.2 Código de Testes
- **Adicionados:** 24 novos casos de teste
- **Padrão utilizado:** Mocks de tkinter, stubs de módulos PDF, fixtures reutilizáveis
- **Técnicas aplicadas:**
  - Stub de `tkinter.messagebox` e `tkinter.filedialog` para evitar GUI real
  - Mock de serviços externos (`clientes_service`, `lixeira`, `uploads`, `pdf_converter`)
  - Testes de threads com `time.sleep(0.1)` para aguardar execução assíncrona
  - Validação de callbacks e propagação de erros

---

## 7. DESAFIOS E SOLUÇÕES

### 7.1 Desafio: Testes assíncronos com threads
- **Problema:** `run_pdf_batch_converter()` executa conversão em thread separada
- **Solução:** Adicionar `time.sleep(0.1)` nos testes para aguardar execução da thread antes de validar resultados

### 7.2 Desafio: Stubs de tkinter
- **Problema:** Importações reais de tkinter causam erros em ambiente headless
- **Solução:** Criação de `_stub_tk_modules()` que injeta stubs minimalistas via `monkeypatch.setitem(sys.modules, ...)`

### 7.3 Desafio: Cobertura de branches defensivos
- **Problema:** Alguns branches tratam exceções extremamente raras
- **Solução:** Aceitar 96.6% como excelente (acima da meta de 85%) e documentar justificativa para os 3.4% restantes

---

## 8. CONCLUSÃO

### 8.1 Objetivos Alcançados

✅ **TEST-001:** Cobertura elevada de 56.6% para **96.6%** (meta: ≥85%, ideal: ≥90%)  
✅ **QA-003:** Pyright 0 erros / 0 warnings  
✅ **QA-003:** Ruff sem problemas  
✅ **Documentação:** Relatório técnico completo gerado

### 8.2 Métricas Finais

| Item                          | Valor      |
|-------------------------------|------------|
| Cobertura final               | **96.6%**  |
| Testes implementados          | 41         |
| Pyright errors                | 0          |
| Pyright warnings              | 0          |
| Ruff issues                   | 0          |
| Linhas de produção alteradas  | 0          |

### 8.3 Próxima Sugestão

Conforme recomendação do relatório técnico de `main_window`, o próximo alvo sugerido é:

**📍 Próxima microfase:** `SessionCache` (`src/modules/main_window/session_service.py`)  
**Meta de cobertura:** ≥90%  
**Justificativa:** Segundo módulo no ranking de prioridades, responsável por cache de sessão e dados do usuário.

---

## 9. ANEXOS

### 9.1 Comando para Reproduzir Cobertura

```bash
python -m coverage erase
python -m coverage run -m pytest tests/unit/modules/main_window/test_app_actions_fase45.py -v
python -m coverage report -m src/modules/main_window/app_actions.py
```

### 9.2 Estrutura de Fixtures Utilizada

```python
@pytest.fixture
def fake_app():
    """Mock de App com métodos necessários."""
    app = types.SimpleNamespace(
        _selected_main_values=lambda: [],
        _get_user_cached=lambda: {"id": "user1"},
        _get_org_id_cached=lambda uid: "org-1",
        carregar=lambda: None,
        get_current_client_storage_prefix=lambda: "org/client"
    )
    return app

def _stub_tk_modules(monkeypatch):
    """Stub de tkinter para evitar GUI real."""
    # ... (implementação completa no arquivo de teste)
```

---

**Status da Microfase:** ✅ **CONCLUÍDA COM SUCESSO**

**Aprovação para próxima fase:** Sim, pode-se iniciar trabalho em `session_service.py`
