# 🧪 Smoke Test Manual — MainWindow v1.4.72

**Data:** 21 de dezembro de 2025  
**Versão:** v1.4.72  
**Refatoração:** MainWindow Bootstrap + Actions (649 LOC)

---

## 📋 Objetivo

Este guia permite validar manualmente que a grande refatoração do MainWindow não introduziu regressões visíveis. O MainWindow foi reduzido de **1230 → 649 LOC** através da extração de bootstrap e actions, mantendo comportamento idêntico.

---

## A) Como Rodar o Aplicativo

### Modo Normal (Produção)
```powershell
cd C:\Users\Pichau\Desktop\v1.4.72
.\.venv\Scripts\Activate.ps1
python main.py
```

### Modo Debug (Logs Verbose)
```powershell
cd C:\Users\Pichau\Desktop\v1.4.72
.\.venv\Scripts\Activate.ps1
$env:RC_VERBOSE="1"
python main.py
```

### Verificar Versão
- Abrir o app
- Menu: **Ajuda → Sobre**
- Confirmar: `v1.4.72`

---

## B) Checklist de Navegação/Telas

### B.1 — Inicialização
- [ ] App abre sem erros no console
- [ ] Login funciona (ou auto-login se credenciais salvas)
- [ ] Janela maximiza automaticamente após login
- [ ] TopBar aparece com botão Home e ícone de notificações
- [ ] StatusBar aparece no rodapé com:
  - Contador de clientes
  - Status online/offline (●)
  - Usuário logado

### B.2 — Navegação entre Telas
- [ ] **Home (Hub)**: Clicar no botão Home → exibe tela de notas compartilhadas
- [ ] **Clientes**: Menu ou atalho → exibe lista de clientes
- [ ] **Senhas**: Menu → exibe gerenciador de senhas
- [ ] **Fluxo de Caixa**: Menu → exibe tela de cashflow
- [ ] **Voltar ao Hub**: Clicar Home novamente → retorna ao Hub

### B.3 — Atalhos de Teclado
- [ ] `Ctrl+N`: Novo cliente
- [ ] `Ctrl+E`: Editar cliente (com cliente selecionado)
- [ ] `Ctrl+Del`: Excluir cliente (com cliente selecionado)
- [ ] `Ctrl+U`: Upload de arquivos
- [ ] `Ctrl+H`: Voltar ao Hub
- [ ] `Ctrl+F`: Buscar (na tela de clientes)
- [ ] `Ctrl+Q`: Sair do app

### B.4 — Menu Bar
- [ ] **Arquivo → Sair**: Abre diálogo de confirmação → fecha app
- [ ] **Tema → [Trocar tema]**: Troca visual (cosmo, flatly, etc.)
- [ ] **Ajuda → Changelog**: Exibe preview do changelog
- [ ] **Ajuda → Sobre**: Exibe versão e créditos

---

## C) Checklist TopBar/Notificações

### C.1 — Badge de Notificações
- [ ] Badge aparece no TopBar (ícone de sino)
- [ ] Contador numérico aparece quando há notificações não lidas
- [ ] Badge atualiza automaticamente (polling a cada 20s)

### C.2 — Painel de Notificações
- [ ] Clicar no badge → abre painel flutuante
- [ ] Painel lista notificações não lidas
- [ ] Cada notificação mostra:
  - Título
  - Mensagem
  - Timestamp (ex: "2 horas atrás")
- [ ] Notificações mais recentes aparecem no topo

### C.3 — Ações de Notificações
- [ ] **Marcar como lida** (ícone de check): marca individual
- [ ] **Marcar todas como lidas** (botão no topo): limpa badge
- [ ] **Mute/Unmute** (ícone de sino barrado):
  - Ativa/desativa toasts de novas notificações
  - Estado persiste enquanto app estiver aberto
- [ ] **Fechar painel** (X): painel desaparece sem marcar como lidas

### C.4 — Toasts de Novas Notificações
- [ ] Quando chega nova notificação (testar com outro usuário criando nota):
  - Toast aparece no canto inferior direito
  - Mostra quantidade de novas notificações
  - Desaparece automaticamente após ~5s
- [ ] Se mute ativo: toasts NÃO aparecem

### C.5 — Badge Zero
- [ ] Quando todas marcadas como lidas → contador desaparece
- [ ] Badge fica visível mas sem número
- [ ] Painel abre vazio ou mostra "Nenhuma notificação não lida"

---

## D) Checklist Hub/Anotações Compartilhadas

### D.1 — UI do Hub
- [ ] Hub exibe título "Anotações Compartilhadas"
- [ ] Lista de notas aparece (ou "Nenhuma anotação" se vazia)
- [ ] Cada nota mostra:
  - Texto da nota
  - Autor (email)
  - Data/hora de criação
  - Botão "Copiar" (ícone)
  - Botão "Apagar" (ícone, só se for autor ou owner)

### D.2 — Criar Nova Nota
- [ ] Botão "+ Nova Anotação" visível
- [ ] Clicar → abre diálogo de edição
- [ ] Digitar texto → clicar "Salvar"
- [ ] Nota aparece na lista imediatamente
- [ ] Notificação é enviada aos outros membros da org

### D.3 — Copiar Nota
- [ ] Clicar ícone "Copiar" em uma nota
- [ ] Texto é copiado para clipboard
- [ ] Toast de confirmação aparece: "Texto copiado!"

### D.4 — Apagar Nota (Própria)
- [ ] Clicar ícone "Apagar" em nota própria
- [ ] Diálogo de confirmação aparece:
  - "Tem certeza que deseja apagar esta anotação?"
- [ ] Clicar "OK" → nota desaparece da lista
- [ ] Se outro usuário recarregar → vê "Mensagem apagada"

### D.5 — Nota Apagada (Hard Delete)
- [ ] Se nota foi deletada (hard delete no DB):
  - Aparece card com mensagem: **"Mensagem apagada"**
  - Card tem fundo diferente (cinza/outline)
  - Não tem botões de ação
- [ ] Clicar "Recarregar" → limpa notas apagadas da UI

### D.6 — Permissões de Deleção
- [ ] **Se for autor da nota**: botão "Apagar" visível
- [ ] **Se for owner da org**: botão "Apagar" visível (em qualquer nota)
- [ ] **Se for membro comum**: botão "Apagar" NÃO aparece em notas de outros
- [ ] **Nota de sistema/admin**: botão "Apagar" oculto para todos

### D.7 — Recarregar Notas
- [ ] Botão "Recarregar" (ícone de refresh) no topo
- [ ] Clicar → busca notas atualizadas do Supabase
- [ ] Lista atualiza com novas notas/alterações

### D.8 — Scroll e Performance
- [ ] Se tiver muitas notas (>20): scroll funciona
- [ ] Notas carregam rápido (<2s)
- [ ] UI não trava ao carregar ou recarregar

---

## E) Checklist de Fechamento/Cleanup

### E.1 — Fechar App Normalmente
- [ ] Menu → Arquivo → Sair
- [ ] Diálogo de confirmação: "Tem certeza que deseja sair?"
- [ ] Clicar "OK" → app fecha sem erros
- [ ] Console não mostra tracebacks
- [ ] Logs mostram:
  ```
  INFO: App fechado.
  ```

### E.2 — Fechar pela Barra de Título (X)
- [ ] Clicar X no canto superior direito
- [ ] Diálogo de confirmação aparece
- [ ] Confirmar → app fecha limpo

### E.3 — Logout
- [ ] Menu → Arquivo → Sair
- [ ] Durante logout, verifica:
  - Nenhum erro de "after_cancel"
  - Nenhum erro de "winfo_exists"
  - Pollers param corretamente

### E.4 — Reabrir o App
- [ ] Fechar e reabrir app múltiplas vezes
- [ ] Verificar que:
  - Não há duplicação de pollers (notificações não aparecem 2x)
  - Não há memory leaks visíveis (consumo de RAM estável)
  - Tela inicial continua sendo o Hub

### E.5 — Teste de After/Pollers
- [ ] Abrir app → aguardar 1 minuto
- [ ] Verificar no console logs de:
  - Polling de notificações (a cada 20s)
  - Health check (a cada 30s)
  - Refresh de status (se necessário)
- [ ] Fechar app → logs devem mostrar:
  ```
  DEBUG: Falha ao parar pollers: [ou sucesso]
  DEBUG: Falha ao parar StatusMonitor: [ou sucesso]
  INFO: App fechado.
  ```
- [ ] Nenhum erro de "after called on destroyed widget"

---

## F) Onde Olhar Logs e O Que Copiar

### F.1 — Logs do Console
- Ao rodar `python main.py`, todos os logs aparecem no terminal
- **Níveis de log:**
  - `DEBUG`: Detalhes técnicos (só com `RC_VERBOSE=1`)
  - `INFO`: Eventos normais (app iniciado, telas abertas)
  - `WARNING`: Problemas não críticos
  - `ERROR`: Erros que não param o app
  - `CRITICAL`: Erros graves

### F.2 — O Que Copiar se Der Erro

#### Se o app não iniciar:
```
1. Copiar TODA a saída do terminal desde "python main.py"
2. Procurar por:
   - ERROR:
   - CRITICAL:
   - Traceback (most recent call last):
3. Copiar o traceback completo até a última linha
```

#### Se houver erro em runtime (app aberto):
```
1. Anotar o que estava fazendo (ex: "clicando em Nova Anotação")
2. Olhar o terminal para logs de ERROR ou WARNING
3. Copiar o traceback se houver
4. Verificar se o app continua funcionando ou travou
```

#### Se o app fechar inesperadamente:
```
1. Copiar os últimos 50 linhas do terminal
2. Procurar por "destroy", "exception", "error"
3. Anotar se havia diálogo aberto ou operação em andamento
```

### F.3 — Arquivos de Log (se configurado)
- Por padrão, app não grava logs em arquivo
- Se configurado: procurar em `logs/` ou `~/.rcgestor/logs/`

### F.4 — Informações Úteis para Reportar Bug
- Versão: `v1.4.72`
- Python: `python --version`
- OS: `Windows 10/11` (ou outro)
- Passos para reproduzir: lista numerada
- Logs/Traceback: texto completo
- Screenshot (se for erro visual)

---

## G) Checklist de Temas

### G.1 — Trocar Tema em Runtime
- [ ] Menu → Tema → [Escolher tema diferente]
- [ ] App mostra diálogo: "Tema será alterado ao reiniciar"
- [ ] Confirmar → app fecha e reabre automaticamente
- [ ] Tema novo aplicado corretamente

### G.2 — Temas Disponíveis
Testar troca entre:
- [ ] cosmo (padrão light)
- [ ] darkly (dark)
- [ ] flatly (light)
- [ ] solar (dark laranja)
- [ ] superhero (dark azul)

Para cada tema:
- [ ] Cores aplicadas globalmente
- [ ] Comboboxes funcionam (sem erro "Duplicate element")
- [ ] StatusBar legível
- [ ] TopBar legível

---

## H) Checklist de Conectividade

### H.1 — Status Dot (Rodapé)
- [ ] Quando online: ● verde + "Online"
- [ ] Quando offline: ● vermelho + "Offline"
- [ ] Transição detectada automaticamente

### H.2 — Alerta de Offline (só primeira vez)
- [ ] Se ficar offline pela primeira vez:
  - Messagebox aparece: "Sem conexão. Verifique internet."
- [ ] Se ficar offline novamente (mesma sessão):
  - Alerta NÃO aparece novamente

### H.3 — Recuperação Online
- [ ] Se voltar online:
  - Status dot muda para verde
  - App continua funcionando normalmente
  - Nenhum alerta (só log DEBUG)

---

## I) Checklist de ChatGPT Window (se habilitado)

### I.1 — Abrir ChatGPT
- [ ] Menu → Ferramentas → ChatGPT (ou atalho)
- [ ] Janela separada abre

### I.2 — Fechar ChatGPT
- [ ] Clicar X na janela do ChatGPT
- [ ] Janela fecha sem erros
- [ ] MainWindow continua funcionando

### I.3 — Reabrir ChatGPT
- [ ] Abrir novamente após fechar
- [ ] Nova instância criada (ou mesma janela reaparece)
- [ ] Sem duplicação de handlers

---

## J) Critérios de Aceitação (Pass/Fail)

### ✅ PASS se:
- Todos os checkboxes de navegação funcionam
- Notificações aparecem e podem ser marcadas como lidas
- Hub carrega e permite criar/copiar/apagar notas
- Permissões de deleção respeitadas
- "Mensagem apagada" aparece para notas deletadas
- App fecha limpo (sem tracebacks)
- Reabrir app funciona sem duplicar pollers

### ❌ FAIL se:
- Crash ao abrir app
- Erro de import/atributo não tratado
- Notificações não atualizam
- Notas não carregam no Hub
- Botão "Apagar" aparece para usuário sem permissão
- "Mensagem apagada" não aparece ou causa erro
- Tracebacks ao fechar app
- Pollers duplicam após reabrir

---

## K) Notas Finais

### K.1 — Refatoração Aplicada
Esta versão passou por **grande refatoração do MainWindow**:
- **Redução de LOC:** 1230 → 649 (-47%)
- **Arquitetura:**
  - `main_window_bootstrap.py`: inicialização centralizada
  - `main_window_actions.py`: 30+ métodos extraídos
  - `main_window.py`: orquestrador com wrappers

### K.2 — Áreas Críticas (Atenção Extra)
- **Pollers** (notifications, health, status): verificar que não duplicam
- **Destroy/Cleanup**: verificar que não há after_cancel em widget destruído
- **Hub/Notas**: verificar permissões de deleção e "Mensagem apagada"
- **TopBar**: verificar que badge atualiza e mute funciona

### K.3 — Testes Automatizados (Já Passaram)
- ✅ 215 testes do main_window
- ✅ 18 testes do topbar
- ✅ 451 testes do hub/notes
- ✅ Total: 684 testes passed, 66 skipped

### K.4 — Performance Esperada
- Inicialização: < 3s
- Troca de tela: < 1s
- Carregamento de notas: < 2s
- Polling de notificações: a cada 20s (não perceptível)

---

**Fim do Smoke Test Manual**  
Se encontrar algum problema, consulte a seção **F) Onde Olhar Logs**.
