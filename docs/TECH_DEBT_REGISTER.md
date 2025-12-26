# 📋 Registro de Dívida Técnica - RC Gestor de Clientes

**Data de Geração:** 26 de dezembro de 2025  
**Versão:** 1.4.93  
**Escopo:** Inventário de TODOs/FIXMEs/XXXs no código-fonte

---

## 📊 Resumo Executivo

| Tag | Quantidade | Descrição |
|-----|-----------|-----------|
| TODO | 4 | Funcionalidades pendentes ou melhorias planejadas |
| FIXME | 0 | Bugs conhecidos ou problemas que precisam correção |
| XXX | 0 | Alertas de código problemático ou hacky |
| **TOTAL** | **4** | |

---

## 📐 Padrão Recomendado para Novos Comentários

Para manter rastreabilidade e evitar TODOs órfãos, adote o seguinte padrão:

```python
# TODO(@autor, YYYY-MM-DD): Descrição curta do que precisa ser feito [ticket-opcional]
# FIXME(@autor, YYYY-MM-DD): Descrição do bug ou problema [ticket-opcional]
```

**Exemplos:**
```python
# TODO(@joao, 2025-12-26): Implementar cache de consultas SQL [PERF-123]
# FIXME(@maria, 2025-12-26): Corrigir race condition no upload [BUG-456]
```

**Benefícios:**
- ✅ Identificar responsável original
- ✅ Rastrear há quanto tempo o TODO existe
- ✅ Vincular com sistema de tickets (Jira, GitHub Issues, etc.)
- ✅ Compatível com linters (Ruff TD002, TD003)

---

## 📝 Inventário Completo

### 🔍 Legenda de Prioridades

| Prioridade | Descrição | Quando Resolver |
|-----------|-----------|-----------------|
| **P3** | Alta - Impacta funcionalidade core | Próximo sprint |
| **P4** | Média - Melhoria importante | 1-2 sprints |
| **Backlog** | Baixa - Nice to have | Quando possível |

---

### 1. Módulo ANVISA - User ID em Demandas

| Campo | Valor |
|-------|-------|
| **Tag** | TODO |
| **Arquivo** | `src/modules/anvisa/views/anvisa_screen.py` |
| **Linha** | 419 |
| **Comentário** | `TODO: passar user_id se disponível` |
| **Contexto** | Criação de demanda ANVISA sem rastreamento de autor |
| **Ação Sugerida** | Integrar com sistema de autenticação para registrar `created_by` |
| **Tipo** | Auditoria / Rastreabilidade |
| **Prioridade** | **P4** (Média) |
| **Impacto** | Melhora auditoria, mas não bloqueia funcionalidade |
| **Esforço Estimado** | 2-4 horas (integração com auth + testes) |

**Descrição Detalhada:**
Atualmente, demandas ANVISA são criadas com `created_by=None`, perdendo rastreabilidade de quem criou cada demanda. Implementar integração com `src.helpers.auth_utils.current_user_id()` para registrar autor.

**Arquivos Relacionados:**
- `src/modules/anvisa/services/anvisa_service.py` (lógica de criação)
- `src/helpers/auth_utils.py` (obtenção de user_id)

---

### 2. Clientes - Exportação de Dados (CSV/Excel)

| Campo | Valor |
|-------|-------|
| **Tag** | TODO |
| **Arquivo** | `src/modules/clientes/viewmodel.py` |
| **Linha** | 277 |
| **Comentário** | `TODO: Implementar exportação real (CSV/Excel) em fase futura` |
| **Contexto** | Funcionalidade de exportação em lote de clientes |
| **Ação Sugerida** | Implementar exportação usando `pandas` ou `openpyxl` |
| **Tipo** | Feature / Melhoria UX |
| **Prioridade** | **Backlog** |
| **Impacto** | Nice to have - usuários podem copiar dados manualmente |
| **Esforço Estimado** | 1-2 dias (UI + lógica + testes) |

**Descrição Detalhada:**
Método `export_batch()` existe mas não implementa a exportação real. Atualmente apenas loga a ação. Implementação futura deve:
1. Gerar arquivo CSV ou Excel com dados dos clientes selecionados
2. Incluir campos: CNPJ, Razão Social, Responsável, Contatos, etc.
3. Oferecer opção de formato (CSV vs XLSX)
4. Salvar em local escolhido pelo usuário (file dialog)

**Dependências:**
- `openpyxl` ou `xlsxwriter` (para Excel)
- `pandas` (opcional, para facilitar manipulação)

---

### 3. Formulário de Cliente - Dirty State Check

| Campo | Valor |
|-------|-------|
| **Tag** | TODO |
| **Arquivo** | `src/modules/clientes/forms/client_form_controller.py` |
| **Linha** | 264 |
| **Comentário** | `TODO: Verificar dirty state e perguntar confirmação` |
| **Contexto** | Cancelamento de formulário sem verificar alterações não salvas |
| **Ação Sugerida** | Implementar verificação de dirty state antes de fechar |
| **Tipo** | UX / Prevenção de perda de dados |
| **Prioridade** | **P3** (Alta) |
| **Impacto** | Risco de perda de dados não salvos pelo usuário |
| **Esforço Estimado** | 4-6 horas (dirty tracking + confirmação + testes) |

**Descrição Detalhada:**
Atualmente, ao clicar em "Cancelar" no formulário de cliente, o formulário fecha imediatamente sem verificar se há alterações não salvas. Isso pode causar perda de dados acidental.

**Implementação Sugerida:**
1. Adicionar flag `_is_dirty` no controller
2. Marcar dirty=True ao detectar alterações nos campos
3. No `handle_cancel()`, verificar dirty state
4. Se dirty, mostrar messagebox: "Há alterações não salvas. Deseja descartar?"
5. Apenas fechar se usuário confirmar

**Padrão Similar:**
Veja `src/modules/passwords/` que já implementa dirty tracking.

---

### 4. Hub - Tooltips em Botões de Módulos

| Campo | Valor |
|-------|-------|
| **Tag** | TODO |
| **Arquivo** | `src/modules/hub/views/modules_panel.py` |
| **Linha** | 114 |
| **Comentário** | `TODO: Adicionar tooltip quando disponível` |
| **Contexto** | Botões de módulos têm descrição mas não exibem tooltip |
| **Ação Sugerida** | Implementar sistema de tooltips usando ttkbootstrap.Tooltip |
| **Tipo** | UX / Melhoria de usabilidade |
| **Prioridade** | **P4** (Média) |
| **Impacto** | Melhora descoberta de funcionalidades, mas não crítico |
| **Esforço Estimado** | 2-3 horas (implementação + testes visuais) |

**Descrição Detalhada:**
Os botões de módulos no Hub têm campo `description` mas não exibem tooltips ao passar o mouse. Isso dificulta descoberta de funcionalidades pelos usuários.

**Implementação Sugerida:**
```python
from ttkbootstrap.tooltip import ToolTip

if action.description:
    ToolTip(btn, text=action.description, bootstyle="info")
```

**Considerações:**
- Verificar se ttkbootstrap.Tooltip está disponível na versão usada
- Testar em Windows (tema dark/light)
- Garantir que tooltip não bloqueia cliques

---

## 📈 Análise de Tendências

### Distribuição por Tipo

| Tipo | Quantidade | % |
|------|-----------|---|
| Feature/Melhoria UX | 3 | 75% |
| Auditoria/Rastreabilidade | 1 | 25% |
| Bug/Correção | 0 | 0% |

**Observação:** Nenhum TODO indica bug crítico ou código problemático (XXX/FIXME), o que indica boa qualidade geral do código.

### Distribuição por Prioridade

| Prioridade | Quantidade | % |
|-----------|-----------|---|
| P3 (Alta) | 1 | 25% |
| P4 (Média) | 2 | 50% |
| Backlog | 1 | 25% |

---

## 🎯 Recomendações

### Imediato (Próximo Sprint)

1. ✅ **P3: Dirty State Check (client_form_controller.py)**
   - Previne perda de dados
   - Impacto direto na experiência do usuário

### Curto Prazo (1-2 Sprints)

2. ✅ **P4: User ID em Demandas ANVISA**
   - Melhora auditoria
   - Relativamente simples (2-4h)

3. ✅ **P4: Tooltips no Hub**
   - Melhora onboarding de novos usuários
   - Simples e rápido (2-3h)

### Backlog (Quando Possível)

4. 📦 **Exportação CSV/Excel**
   - Nice to have
   - Esforço maior (1-2 dias)
   - Priorizar apenas se houver demanda recorrente de usuários

---

## 🔄 Processo de Atualização

Este documento deve ser atualizado:

- ✅ **Mensalmente:** Review geral de novos TODOs
- ✅ **A cada release:** Remover TODOs resolvidos
- ✅ **Ad-hoc:** Ao adicionar TODOs significativos no código

**Comando para regenerar inventário:**
```powershell
Get-ChildItem -Path src -Recurse -Filter *.py | Select-String -Pattern "(# TODO|# FIXME|# XXX)" -CaseSensitive
```

---

## 📚 Referências

- [Ruff TD Rules](https://docs.astral.sh/ruff/rules/#flake8-todos-td) - Linting de TODOs
- [Google Style Guide - TODO Comments](https://google.github.io/styleguide/pyguide.html#312-todo-comments)
- [PEP 350 - Codetags](https://peps.python.org/pep-0350/) (Draft) - Proposta de padronização

---

## 📝 Histórico de Mudanças

| Versão | Data | Descrição | Autor |
|--------|------|-----------|-------|
| 1.0 | 2025-12-26 | Criação inicial do registro (P2-004) | GitHub Copilot |

---

*Este documento é parte do processo de gestão de dívida técnica do RC Gestor de Clientes. Para adicionar novos itens, siga o padrão recomendado e atualize este registro periodicamente.*
