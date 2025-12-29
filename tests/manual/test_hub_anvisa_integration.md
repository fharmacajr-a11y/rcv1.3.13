# Teste Manual: Integração HUB + ANVISA

## Objetivo
Validar as 3 melhorias implementadas:
1. Picker ANVISA filtra apenas demandas abertas
2. HUB atualiza imediatamente após ações ANVISA
3. Mini-histórico coloriza ações (vermelho/verde + bold)

---

## Pré-requisitos
- Aplicação rodando com dados de teste
- Acesso ao módulo ANVISA e HUB
- Pelo menos 2 clientes com demandas:
  - Cliente 312 com demanda cancelada/concluída (para teste de filtro)
  - Cliente com demanda aberta (para teste de atualização)

---

## Teste 1: Picker ANVISA - Filtrar apenas abertas

### Passos:
1. Acessar HUB
2. Clicar em qualquer item de "Prazos de hoje" ou "Tarefas pendentes" do ANVISA
3. Observar o picker "Escolher histórico ANVISA"

### Resultado Esperado:
- ✅ Cliente 312 (com apenas demandas fechadas) **NÃO APARECE** no picker
- ✅ Apenas clientes com demandas em "draft", "submitted", "in_progress" aparecem
- ✅ Coluna "Situação" mostra apenas status tipo "Em aberto — Atrasada/Hoje/Em Xd"
- ✅ NUNCA aparece "Cancelada" ou "Concluída" na coluna Situação

---

## Teste 2: HUB atualiza imediatamente

### Cenário A: Cancelar demanda

#### Passos:
1. Notar o contador de tarefas/prazos ANVISA no HUB (ex: "3 tarefas pendentes")
2. Abrir módulo ANVISA
3. Selecionar cliente com demanda aberta
4. Abrir popup de histórico
5. Cancelar uma demanda
6. **Observar HUB imediatamente** (sem fechar popup ANVISA)

#### Resultado Esperado:
- ✅ Contador HUB atualiza na hora (ex: "3" → "2")
- ✅ Lista de prazos/tarefas no HUB remove o item cancelado
- ✅ Não precisa clicar em "Atualizar" ou reabrir HUB

### Cenário B: Concluir demanda

#### Passos:
1. Notar contadores no HUB
2. Concluir demanda no ANVISA (botão "Finalizar")
3. Observar HUB

#### Resultado Esperado:
- ✅ Mesma atualização imediata (contadores + listas)

### Cenário C: Excluir demanda

#### Passos:
1. Notar contadores no HUB
2. Excluir demanda no ANVISA (botão "Excluir")
3. Observar HUB

#### Resultado Esperado:
- ✅ Mesma atualização imediata (contadores + listas)

---

## Teste 3: Mini-histórico com cores

### Passos:
1. Acessar HUB
2. Rolar até seção "📋 Atividade recente da equipe" (mini-histórico)
3. **Cancelar** uma regularização ANVISA
4. Observar nova linha no mini-histórico
5. **Concluir** outra regularização ANVISA
6. Observar nova linha no mini-histórico

### Resultado Esperado:
- ✅ Linha de CANCELAMENTO:
  - Formato: `28/12 - 21:37 (ANVISA) — Cliente | ID: 312 — 07.816.095/0001-65 — REGULARIZAÇÃO CANCELADA: Cancelamento de AFE — por: Júnior`
  - **"REGULARIZAÇÃO CANCELADA"** aparece em **VERMELHO + NEGRITO**
  - Resto da linha em fonte normal

- ✅ Linha de CONCLUSÃO:
  - Formato: `28/12 - 21:37 (ANVISA) — Cliente | ID: 312 — 07.816.095/0001-65 — REGULARIZAÇÃO CONCLUÍDA: RDC 44/2009 — por: Júnior`
  - **"REGULARIZAÇÃO CONCLUÍDA"** aparece em **VERDE + NEGRITO**
  - Resto da linha em fonte normal

- ✅ Linha de EXCLUSÃO:
  - Formato: `28/12 - 21:37 (ANVISA) — Cliente | ID: 312 — REGULARIZAÇÃO EXCLUÍDA: Licença Sanitária — por: Elisabete`
  - Texto permanece normal (sem cor especial)

---

## Teste Integrado: Fluxo Completo

### Cenário: Cliente 312 com demanda cancelada

#### Estado Inicial:
- Cliente 312 tem 1 demanda aberta + 1 demanda cancelada

#### Passos:
1. Abrir picker ANVISA no HUB
   - ✅ Cliente 312 **APARECE** (tem demanda aberta)
2. Cancelar a última demanda aberta do cliente 312 no ANVISA
3. Observar HUB:
   - ✅ Contador atualiza imediatamente
   - ✅ Mini-histórico adiciona linha vermelha "REGULARIZAÇÃO CANCELADA"
4. Reabrir picker ANVISA
   - ✅ Cliente 312 **DESAPARECE** (agora só tem demandas fechadas)

---

## Validação Visual

### Cores esperadas no mini-histórico:
```
28/12 - 21:37 (ANVISA) — Cliente | ID: 312 — 07.816.095/0001-65 — REGULARIZAÇÃO CANCELADA: X — por: Y
                                                                    ^^^^^^^^^^^^^^^^^^^^^^^^
                                                                    VERMELHO + BOLD (#dc3545)

28/12 - 21:37 (ANVISA) — Cliente | ID: 312 — 07.816.095/0001-65 — REGULARIZAÇÃO CONCLUÍDA: X — por: Y
                                                                    ^^^^^^^^^^^^^^^^^^^^^^^^
                                                                    VERDE + BOLD (#28a745)
```

---

## Critérios de Aceitação

### ✅ TODOS devem passar:
1. Picker ANVISA não mostra clientes que só têm demandas fechadas
2. Picker ANVISA nunca mostra status "Cancelada" ou "Concluída" na coluna Situação
3. Após cancelar/concluir/excluir no ANVISA, HUB atualiza contadores E listas imediatamente
4. Mini-histórico coloriza APENAS "REGULARIZAÇÃO CANCELADA" (vermelho) e "REGULARIZAÇÃO CONCLUÍDA" (verde)
5. Colorização aplica bold + cor APENAS na substring específica, não na linha inteira
6. Todos os testes automatizados passam (pytest)
7. Ruff e compileall não reportam erros

---

## Notas de Implementação

### Arquivos Modificados:
- `src/modules/hub/views/hub_dialogs.py`: Filtro de demandas abertas no picker
- `src/modules/anvisa/views/_anvisa_handlers_mixin.py`: Já chamava `_refresh_hub_dashboard_if_present()` + fix due_date
- `src/modules/hub/views/dashboard_center.py`: Colorização com tags no ScrolledText

### Tecnologias Usadas:
- `tkinter.Text.tag_configure()`: Configurar tags com foreground/font
- `tkinter.Text.tag_add()`: Aplicar tags em ranges específicos (keyword matching)
- `STATUS_OPEN` do `src/modules/anvisa/constants.py`: Fonte única de verdade para status abertos
- `_refresh_hub_dashboard_if_present()`: Já implementado, garante atualização imediata

### Commits Sugeridos:
```
feat(hub): picker ANVISA filtra apenas demandas abertas

- Importa STATUS_OPEN de constants
- Modifica _choose_representative_request para retornar None se não houver abertas
- Cliente sem demandas abertas não aparece no picker
- Atualiza sort_key para remover categoria de fechadas

Refs: PROMPT-CODEX (1/3)
```

```
feat(anvisa): fix due_date não definido em _excluir_demanda_popup

- Adiciona obtenção de due_date antes de criar ActivityEvent
- Mantém consistência com handlers _finalizar e _cancelar

Refs: PROMPT-CODEX (2/3)
```

```
feat(hub): colorizar ações no mini-histórico

- "REGULARIZAÇÃO CANCELADA" em vermelho + bold
- "REGULARIZAÇÃO CONCLUÍDA" em verde + bold
- Usa Text.tag_configure e tag_add para colorização precisa
- Aplica cor apenas na substring específica, não linha inteira

Refs: PROMPT-CODEX (3/3)
```
