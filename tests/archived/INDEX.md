# Índice de Arquivos LEGACY Arquivados

Data de arquivamento: **7 de dezembro de 2025**  
FASE: **6 - Revisão de arquivos LEGACY**  
Branch: **qa/fixpack-04**

---

## Arquivos Movidos

### Módulo Senhas (6 arquivos)

Origem: `tests/unit/modules/passwords/`  
Destino: `tests/archived/passwords/`

| Arquivo LEGACY | Teste Substituto Oficial | Status |
|----------------|--------------------------|--------|
| `LEGACY_test_helpers.py` | `tests/modules/passwords/test_passwords_actions.py` | ✅ Arquivado |
| `LEGACY_test_passwords_service.py` | `tests/modules/passwords/test_passwords_service.py`<br>`tests/unit/modules/passwords/test_passwords_service_errors.py` | ✅ Arquivado |
| `LEGACY_test_passwords_controller.py` | `tests/unit/modules/passwords/test_passwords_controller.py` | ✅ Arquivado |
| `LEGACY_test_passwords_screen_ui.py` | `tests/unit/modules/passwords/test_passwords_controller.py` | ✅ Arquivado |
| `LEGACY_test_passwords_repository_fase53.py` | `tests/modules/passwords/test_passwords_service.py` | ✅ Arquivado |
| `LEGACY_test_passwords_client_selection_feature001.py` | `tests/modules/passwords/test_passwords_actions.py` | ✅ Arquivado |

**Testes oficiais atuais:**
- `tests/modules/passwords/test_passwords_actions.py` - 8 testes
- `tests/modules/passwords/test_passwords_service.py` - 5 testes
- `tests/unit/modules/passwords/test_passwords_controller.py` - 22 testes
- `tests/unit/modules/passwords/test_passwords_service_errors.py` - 23 testes
- **Total: 58 testes passando**

---

### Módulo Clientes/Obrigações (1 arquivo)

Origem: `tests/unit/modules/clientes/views/`  
Destino: `tests/archived/clientes/`

| Arquivo LEGACY | Teste Substituto Oficial | Status |
|----------------|--------------------------|--------|
| `LEGACY_test_obligations_integration.py` | `tests/unit/modules/hub/views/test_dashboard_center.py` | ✅ Arquivado |

**Testes oficiais atuais:**
- `tests/unit/modules/hub/views/test_dashboard_center.py` - 61 testes
- **Contexto:** Funcionalidade de Obrigações foi movida do módulo Clientes para o Hub na v1.3.61

---

## Estatísticas

- **Total de arquivos arquivados:** 7
- **Total de arquivos removidos:** 0
- **Total de arquivos mantidos:** 0

**Motivo do arquivamento:**
1. Todos os arquivos LEGACY possuem substitutos oficiais mais recentes
2. Arquitetura mudou (refatoração REF-001 e migração para Hub v1.3.61)
3. Imports e estrutura de pacotes desatualizados
4. Já estavam marcados com `pytest.skip(allow_module_level=True)`
5. Diretório original já estava em `norecursedirs` do pytest.ini

---

## Características dos Arquivos Arquivados

### Proteções Implementadas

Todos os arquivos LEGACY já possuíam:

```python
pytest.skip(
    "Legacy tests de Senhas (pré-refactor). Mantidos apenas como referência. "
    "Senhas agora é coberto por testes em tests/modules/passwords e "
    "tests/integration/passwords.",
    allow_module_level=True,
)
```

### Markers pytest

```python
pytestmark = [
    pytest.mark.legacy_ui,
    pytest.mark.skip(reason="Service antigo, mantido apenas como referência histórica")
]
```

---

## Configuração pytest

### Antes (v1.3.47)
```ini
norecursedirs = .venv venv build dist .git __pycache__ tests/unit/modules/passwords
```

### Depois (FASE 6)
```ini
norecursedirs = .venv venv build dist .git __pycache__ tests/unit/modules/passwords tests/archived
```

**Comportamento:** Executar `pytest tests` ou `pytest tests --cov` **NÃO** incluirá arquivos em `tests/archived/`.

---

## Validação Executada

### Comando 1: Verificar que archived não é coletado
```powershell
pytest tests/archived --collect-only -q
# ✅ Resultado: Comando retornou erro (diretório ignorado)
```

### Comando 2: Verificar que LEGACY não é coletado
```powershell
pytest tests -k "LEGACY" --collect-only -q
# ✅ Resultado: 0 itens coletados com "LEGACY" no nome
```

### Comando 3: Validar testes oficiais de Senhas
```powershell
pytest tests/modules/passwords tests/unit/modules/passwords -v
# ✅ Resultado: 58 passed
```

### Comando 4: Validar testes oficiais do Hub (Obrigações)
```powershell
pytest tests/unit/modules/hub/views/test_dashboard_center.py -v
# ✅ Resultado: 61 passed
```

---

## Referências

- **Documentação histórica:** `docs/devlog-tests-passwords-legacy-ms1.md`
- **Refatoração estrutural:** REF-001 (módulo Senhas)
- **Migração de funcionalidade:** v1.3.61 (Obrigações: Clientes → Hub)

---

## Próximos Passos Recomendados (FASE 7)

1. **Documentação de Arquitetura de Testes**
   - Criar `docs/TEST_ARCHITECTURE.md`
   - Mapear estrutura oficial de testes
   - Documentar padrões e convenções

2. **Limpeza Final**
   - Revisar se `tests/unit/modules/passwords` (vazio) pode ser removido completamente
   - Atualizar referências em documentação antiga

3. **Auditoria de Markers**
   - Verificar uso consistente de `pytest.mark`
   - Documentar estratégia de markers (legacy_ui, integration, etc.)

---

**Conclusão:** Todos os arquivos LEGACY foram arquivados com segurança. A suíte de testes oficial continua 100% funcional.
