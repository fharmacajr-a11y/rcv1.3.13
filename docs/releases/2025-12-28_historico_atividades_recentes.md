# Histórico de Atividades Recentes - Implementação

## Resumo

Implementação de um "mini-histórico" no bloco "Atividade recente da equipe" do Hub, que registra ações importantes da ANVISA em tempo real, sem persistência no banco de dados.

## Arquivos Criados

### 1. `src/modules/hub/recent_activity_store.py`
Store singleton thread-safe que:
- Mantém até 200 eventos em memória (usando `deque`)
- Notifica observers em tempo real quando novos eventos são adicionados
- Fornece função de formatação para eventos ANVISA (`format_anvisa_event`)

**Principais funções:**
- `get_recent_activity_store()`: Retorna instância singleton
- `add_event(event_str)`: Adiciona evento e notifica observers
- `get_lines()`: Retorna eventos (mais recente primeiro)
- `subscribe(callback)`: Inscreve observer, retorna função unsubscribe
- `format_anvisa_event(...)`: Formata eventos ANVISA com timestamp, cliente, CNPJ, tipo, prazo e usuário

### 2. `tests/unit/modules/hub/test_recent_activity_store.py`
Testes unitários completos para o store, cobrindo:
- Adicionar e recuperar eventos
- Limite máximo de eventos
- Mecanismo de subscrição/desinscrição
- Formatação de eventos completos e mínimos
- Singleton pattern

## Arquivos Modificados

### 1. `src/modules/hub/views/dashboard_center.py`
**Alterações:**
- `_build_recent_activity_section()`: Substituiu Labels por `ScrolledText` read-only
- Integrou com o store usando padrão observer
- Adiciona cleanup automático ao destruir widget (unsubscribe)
- Remove imports não utilizados (`defaultdict`, `date`, etc.)

**Comportamento:**
- Exibe "Nenhuma atividade recente." quando vazio
- Auto-scroll para o final quando novos eventos chegam
- Atualização em tempo real sem refresh manual

### 2. `src/modules/anvisa/views/_anvisa_handlers_mixin.py`
**Alterações em 3 métodos:**

#### `_finalizar_demanda()`
- Registra evento "Concluída" após sucesso
- Extrai dados: cliente, CNPJ, tipo, prazo, usuário
- Adiciona ao store com `format_anvisa_event`

#### `_cancelar_demanda()`
- Registra evento "Cancelada" após sucesso
- Mesma lógica de extração de dados

#### `_excluir_demanda_popup()`
- Registra evento "Excluída" após sucesso
- Obtém `due_date` antes de invalidar cache

**Tratamento de erros:**
- Todos os registros estão em `try/except` para não quebrar fluxo principal
- Logs de warning se falhar ao registrar evento

## Formato dos Eventos

Exemplo completo:
```
[28/12 17:33] ANVISA — Concluída — Cliente 312 — CNPJ 07.816.095/0001-65 — Cancelamento de AFE — Prazo 27/12/2025 — por Junior
```

Campos opcionais:
- Se faltar usuário: `— por —`
- Campos ausentes são omitidos (exceto action)

## Características Técnicas

### Thread-Safety
- Usa `RLock` para garantir segurança em operações concorrentes
- Observer pattern thread-safe

### Memória
- Máximo 200 eventos (`MAX_EVENTS`)
- Usa `deque` com `maxlen` para rotação automática
- Session-only (sem persistência)

### UI
- `ScrolledText` com scrollbar vertical automática
- Read-only (state="disabled")
- Auto-scroll para o final
- Font: Segoe UI 9pt
- Background: #f8f9fa

### Cleanup
- Unsubscribe automático ao destruir widget
- Evita memory leaks com callbacks soltos

## Smoke Tests Executados

1. ✅ `python -m compileall`: Sem erros de sintaxe
2. ✅ `ruff check`: Sem problemas de linting
3. ✅ `pytest tests/unit/modules/hub/test_layout_config.py`: 16 passed
4. ✅ `pytest tests/unit/modules/anvisa/`: 257 passed
5. ✅ `pytest tests/unit/modules/hub/test_recent_activity_store.py`: 6 passed

## Próximos Passos (Opcional)

Se desejado futuramente:
1. Persistir eventos no Supabase (nova tabela `recent_activities`)
2. Adicionar filtros (por módulo, usuário, data)
3. Exportar histórico para arquivo
4. Adicionar outros tipos de eventos (além de ANVISA)
5. Configurar limite máximo de eventos via settings

## Notas de Desenvolvimento

- Layout geral do Hub não foi alterado
- Compatibilidade mantida com código existente
- Sem breaking changes em APIs públicas
- Testes existentes continuam passando
