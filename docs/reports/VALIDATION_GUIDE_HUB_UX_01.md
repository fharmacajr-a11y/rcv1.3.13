# ✅ GUIA DE VALIDAÇÃO MANUAL - FASE HUB-UX-01

**Cards Clicáveis no Dashboard HUB**

---

## 🎯 O Que Foi Implementado?

Os **3 cards principais** do dashboard HUB agora são **clicáveis** e navegam para telas relacionadas:

| Card | Aparência | Ação ao Clicar |
|------|-----------|----------------|
| 🔵 **Clientes** (azul) | Número de clientes ativos | Abre tela de **Clientes** (lista completa) |
| 🔴/🟢 **Pendências** (vermelho/verde) | Número de obrigações pendentes | Abre tela de **Auditoria** |
| 🟡/🟢 **Tarefas Hoje** (amarelo/verde) | Número de tarefas de hoje | Abre diálogo **Nova Tarefa** |

---

## 🧪 Como Testar (Passo a Passo)

### 1️⃣ **Executar a Aplicação**

```powershell
# No terminal PowerShell (com venv ativado)
python -m src.app_gui
```

### 2️⃣ **Fazer Login**

- Usar credenciais válidas
- Aguardar carregamento completo da tela

### 3️⃣ **Navegar para o HUB**

- O HUB deve aparecer como tela inicial (ou clicar no botão "Hub" se necessário)
- Aguardar dashboard carregar (3 cards aparecem no topo)

### 4️⃣ **Validar Cursor de Mão**

- **Passar o mouse** sobre cada um dos 3 cards
- ✅ **Esperado:** Cursor muda para **mão (hand2)**
- ❌ **Falha:** Cursor permanece normal (seta)

### 5️⃣ **Testar Clique no Card "Clientes"** (azul)

1. **Clicar** em qualquer parte do card azul "Clientes"
2. ✅ **Esperado:** Tela de **Clientes** abre (lista de clientes)
3. ✅ **Validar:** Você está na tela de Clientes (topbar mostra "Clientes")
4. **Voltar ao HUB:** Clicar em "Home" ou "Hub" no menu

### 6️⃣ **Testar Clique no Card "Pendências"** (vermelho/verde)

1. **Clicar** no card "Pendências" (segundo card)
2. ✅ **Esperado:** Tela de **Auditoria** abre
3. ✅ **Validar:** Você está na tela de Auditoria (topbar mostra "Auditoria")
4. **Voltar ao HUB:** Clicar em "Home" ou "Hub" no menu

### 7️⃣ **Testar Clique no Card "Tarefas Hoje"** (amarelo/verde)

1. **Clicar** no card "Tarefas Hoje" (terceiro card)
2. ✅ **Esperado:** Diálogo **"Nova Tarefa"** abre (janela modal)
3. ✅ **Validar:** Modal com campos de tarefa está visível
4. **Fechar:** Clicar em "Cancelar" ou "X" no modal

### 8️⃣ **Validar Que Nada Quebrou**

- ✅ Dashboard carrega normalmente (cards, radar, seções)
- ✅ Painel de **Notas Compartilhadas** funciona (lateral direita)
- ✅ Botões de navegação do menu (Clientes, Senhas, Auditoria) funcionam
- ✅ Botões **"➕ Nova Tarefa"** e **"➕ Nova Obrigação"** funcionam

---

## ✅ Checklist de Validação

Marque `[x]` após validar cada item:

- [ ] **Aplicação inicia sem erros**
- [ ] **Login funciona normalmente**
- [ ] **HUB carrega (3 cards visíveis)**
- [ ] **Cursor muda para mão ao passar sobre cards**
- [ ] **Card "Clientes"** → Abre tela de Clientes ✅
- [ ] **Card "Pendências"** → Abre tela de Auditoria ✅
- [ ] **Card "Tarefas Hoje"** → Abre diálogo Nova Tarefa ✅
- [ ] **Navegação de volta ao HUB funciona**
- [ ] **Notas compartilhadas funcionam (adicionar/visualizar)**
- [ ] **Botões do menu lateral funcionam**
- [ ] **Nenhum erro no console/logs**

---

## 🐛 Problemas Comuns e Soluções

### ❌ **Cursor não muda para mão**

**Possíveis Causas:**
1. Callbacks não foram passados corretamente
2. Código em `dashboard_center.py` não aplicou `cursor="hand2"`

**Verificar:**
- Arquivo `src/modules/hub/views/dashboard_center.py` tem `on_click` em `_build_indicator_card`
- Arquivo `src/modules/hub/views/hub_screen.py` passa callbacks em `build_dashboard_center`

### ❌ **Clique no card não faz nada**

**Possíveis Causas:**
1. Binding `<Button-1>` não foi configurado
2. Callback levanta exceção (verificar logs)

**Verificar:**
```powershell
# Ver logs do terminal onde a aplicação está rodando
# Procurar por:
# - "Erro ao navegar para Clientes"
# - "Erro ao navegar para Auditoria"
# - "Erro ao abrir tarefas"
```

### ❌ **Aplicação trava ao clicar em card**

**Possíveis Causas:**
1. Navegação chamou código síncrono pesado na thread principal
2. Callback levantou exceção não tratada

**Ação:**
- Verificar logs/console
- Reportar stack trace no devlog

---

## 📸 Como Validar Visualmente

### **ANTES (cards estáticos):**
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Clientes  │  │ Pendências  │  │Tarefas Hoje │
│      42     │  │    5 ⚠      │  │      3      │
└─────────────┘  └─────────────┘  └─────────────┘
      ↑                ↑                  ↑
   Cursor normal  Cursor normal    Cursor normal
```

### **DEPOIS (cards clicáveis):**
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Clientes  │  │ Pendências  │  │Tarefas Hoje │
│      42     │  │    5 ⚠      │  │      3      │
└─────────────┘  └─────────────┘  └─────────────┘
      ↑                ↑                  ↑
   Cursor MÃO     Cursor MÃO        Cursor MÃO
   👆 Clicável    👆 Clicável      👆 Clicável
```

---

## 📝 Reportar Resultados

Após validação, atualizar **devlog** (`docs/devlog-hub-ux-01-cards-clickable.md`):

### Se **TUDO PASSOU** ✅:

```markdown
## ✅ Validação Manual Concluída

**Data:** [DATA]  
**Validador:** [SEU NOME]

**Resultado:** ✅ **APROVADO** - Todos os cards clicáveis funcionam corretamente.

**Observações:**
- Cards mudam cursor para mão ao hover
- Cliques navegam para telas corretas
- Nenhum erro detectado
```

### Se **HOUVER PROBLEMAS** ❌:

```markdown
## ⚠️ Validação Manual - Problemas Detectados

**Data:** [DATA]  
**Validador:** [SEU NOME]

**Resultado:** ❌ **REQUER CORREÇÃO**

**Problemas Encontrados:**
1. [Descrever problema 1]
   - Card afetado: [Clientes/Pendências/Tarefas]
   - Comportamento esperado: [X]
   - Comportamento observado: [Y]
   - Stack trace (se houver): [colar logs]

2. [Descrever problema 2]
   ...
```

---

## 🚀 Após Validação Bem-Sucedida

1. ✅ Marcar fase como **CONCLUÍDA** no devlog
2. 📋 Atualizar checklist de validação manual
3. 🎯 Seguir para próxima fase recomendada: **FASE HUB-SPLIT-01**

---

**FIM DO GUIA DE VALIDAÇÃO**
