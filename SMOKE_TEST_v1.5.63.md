# 🧪 Smoke Test Checklist — RC-Gestor v1.5.63

**Data**: 25/01/2026  
**Release**: v1.5.63  
**Executável**: RC-Gestor-v1.5.63.exe (68.13 MB)  
**SHA256**: ✅ Verificado

---

## ✅ Pré-requisitos
- [ ] Máquina Windows **sem Python instalado** (para validar bundle standalone)
- [ ] Executável extraído de `release_download/RC-Gestor-v1.5.63.exe`
- [ ] Nenhum processo RC-Gestor.exe em execução

---

## 📋 Testes Funcionais

### 1️⃣ Inicialização do Aplicativo
- [ ] **1.1** Duplo clique no RC-Gestor-v1.5.63.exe
- [ ] **1.2** Aplicativo abre **sem erros de console**
- [ ] **1.3** Splash screen aparece (se aplicável)
- [ ] **1.4** Tela principal carrega completamente
- [ ] **1.5** **CRÍTICO**: Nenhum erro de `ModuleNotFoundError` no log/tela

**Erros conhecidos corrigidos nesta versão:**
- ✅ `NameError: ctk not defined` — deve estar RESOLVIDO
- ✅ `TypeError: ClientesV2Frame missing 'master'` — deve estar RESOLVIDO
- ✅ `ModuleNotFoundError: src.core.logs` — deve estar RESOLVIDO

---

### 2️⃣ Alternância de Tema
- [ ] **2.1** Localizar botão/menu de tema (light/dark)
- [ ] **2.2** Alternar para tema **Dark**
  - [ ] Interface muda visualmente (backgrounds escuros)
  - [ ] Textos permanecem legíveis (contraste adequado)
- [ ] **2.3** Alternar para tema **Light**
  - [ ] Interface retorna ao tema claro
  - [ ] Nenhum erro de encoding UTF-8 em labels/botões

---

### 3️⃣ Login (se aplicável)
- [ ] **3.1** Tela de login aparece (ou skip se auto-login)
- [ ] **3.2** Credenciais de teste funcionam
- [ ] **3.3** Após login, dashboard/hub carrega
- [ ] **3.4** Nenhum erro de `UnicodeDecodeError` em mensagens

---

### 4️⃣ Navegação ClientesV2
- [ ] **4.1** Abrir módulo **ClientesV2** via menu/atalho
- [ ] **4.2** Tela de clientes carrega sem crash
- [ ] **4.3** **CRÍTICO**: Widget `ClientesV2Frame` instancia corretamente
  - Confirmação: lista de clientes aparece (mesmo que vazia)
- [ ] **4.4** Botões de ação (Novo, Editar, Excluir) são clicáveis
- [ ] **4.5** Filtros/busca respondem (opcional)

---

### 5️⃣ Encoding e Caracteres Especiais
- [ ] **5.1** Inserir texto com acentos em campo de texto: `São Paulo`, `José María`
- [ ] **5.2** Texto renderiza corretamente (sem �)
- [ ] **5.3** Salvar/recarregar mantém encoding
- [ ] **5.4** Mensagens de erro/sucesso exibem corretamente em português

---

### 6️⃣ Estabilidade ao Fechar
- [ ] **6.1** Fechar aplicativo via botão X
- [ ] **6.2** Processo termina limpo (sem "Não Respondendo")
- [ ] **6.3** Reabrir RC-Gestor-v1.5.63.exe
- [ ] **6.4** App reabre sem erros de estado corrupto
- [ ] **6.5** Configurações persistem (tema escolhido, última tela, etc.)

---

## 🚨 Critérios de Falha (Show Stoppers)

Qualquer um destes **reprova** a release:
1. ❌ App não abre (crash imediato)
2. ❌ `ModuleNotFoundError` ao iniciar
3. ❌ ClientesV2Frame não carrega (TypeError)
4. ❌ Encoding UTF-8 quebrado (� em textos portugueses)
5. ❌ Crash ao alternar tema

---

## 📝 Observações

**Bugs conhecidos (não bloqueantes):**
- Alguns testes unitários desabilitados (estrutura antiga)
- Merge com main bloqueado (divergência estrutural)

**Notas adicionais:**
```
[Escreva aqui qualquer observação durante o teste]
```

---

## ✅ Resultado Final

- [ ] **APROVADO** — Todos os critérios essenciais passaram
- [ ] **REPROVADO** — Pelo menos 1 show stopper encontrado
- [ ] **COM RESSALVAS** — Bugs menores encontrados (detalhar abaixo)

**Testado por**: _______________  
**Data**: ___/___/2026  
**Duração**: ___ minutos

---

## 📎 Anexos

**Logs relevantes** (se houver erros):
```
[Colar aqui erros de console/logs]
```

**Screenshots** (opcional):
- Tela principal (tema light)
- Tela principal (tema dark)
- ClientesV2 carregado
