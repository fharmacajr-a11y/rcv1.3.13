# Checklist de Staging - RC Gestor

**Data:** 2026-01-24  
**Fase:** FASE 6 - CI/CD + Staging  
**Versão:** 1.5.62+

---

## 📋 Objetivo

Este documento define o roteiro de **smoke test manual** que deve ser executado antes de cada release em produção, garantindo que as funcionalidades críticas do sistema estejam funcionais.

---

## 🎯 Escopo do Smoke Test

O smoke test foca nas **funcionalidades principais** do módulo ClientesV2, que é o módulo padrão da aplicação.

---

## ✅ Roteiro de Testes

### 1. Inicialização do Aplicativo

- [ ] **Abrir o aplicativo**
  - Executável inicia sem erros
  - Tela de login é exibida corretamente
  - Tema (light/dark) é carregado conforme configuração

- [ ] **Login**
  - Autenticação com credenciais válidas funciona
  - Mensagem de erro para credenciais inválidas é exibida
  - Transição para tela principal após login bem-sucedido

---

### 2. Módulo ClientesV2 - Operações CRUD

#### 2.1 Listar Clientes

- [ ] **Visualizar lista de clientes**
  - Lista carrega sem erros
  - Dados são exibidos corretamente na tabela (CTkTreeview)
  - Scroll funciona adequadamente
  - Ordenação por colunas funciona (se implementada)

#### 2.2 Buscar Clientes

- [ ] **Busca por nome**
  - Campo de busca filtra resultados em tempo real
  - Resultados são precisos

- [ ] **Busca por outros critérios**
  - Busca por CPF/CNPJ funciona
  - Busca por telefone funciona
  - Limpar busca restaura lista completa

#### 2.3 Novo Cliente

- [ ] **Criar novo cliente**
  - Formulário de novo cliente abre corretamente
  - Validações de campos funcionam (obrigatórios, formato)
  - Cliente é salvo com sucesso no backend
  - Novo cliente aparece na lista após criação
  - Feedback visual (mensagem de sucesso) é exibido

#### 2.4 Editar Cliente

- [ ] **Editar cliente existente**
  - Formulário de edição carrega dados corretos do cliente
  - Modificações são salvas com sucesso
  - Alterações refletem na lista imediatamente
  - Feedback visual (mensagem de sucesso) é exibido

#### 2.5 Excluir Cliente (Lixeira)

- [ ] **Mover cliente para lixeira**
  - Cliente é removido da lista principal
  - Cliente aparece na lixeira
  - Confirmação de exclusão é solicitada

- [ ] **Restaurar cliente da lixeira**
  - Cliente é restaurado para lista principal
  - Dados permanecem intactos após restauração

- [ ] **Exclusão permanente da lixeira**
  - Cliente é excluído definitivamente
  - Confirmação de exclusão permanente é solicitada

---

### 3. Funcionalidades Auxiliares

#### 3.1 Upload de Arquivos

- [ ] **Upload de documento/imagem**
  - Diálogo de seleção de arquivo abre
  - Arquivo é enviado com sucesso
  - Preview do arquivo é exibido (se implementado)
  - Arquivo fica associado ao cliente correto

#### 3.2 Export de Dados

- [ ] **Exportar lista de clientes**
  - Exportação para CSV funciona
  - Exportação para Excel funciona (se implementado)
  - Arquivo exportado contém dados corretos
  - Arquivo é salvo no local esperado

#### 3.3 Modo Pick (Seleção de Cliente)

- [ ] **Modo de seleção**
  - Modo pick é ativado corretamente
  - Cliente pode ser selecionado da lista
  - Retorno do cliente selecionado funciona
  - Modal fecha após seleção

#### 3.4 Integração WhatsApp

- [ ] **Enviar mensagem via WhatsApp**
  - Botão de WhatsApp abre aplicativo/web
  - Número de telefone do cliente é preenchido automaticamente
  - Link/deep link funciona corretamente

---

### 4. Testes de Estabilidade

#### 4.1 Performance

- [ ] **Tempo de resposta**
  - Lista de clientes carrega em < 3 segundos
  - Busca retorna resultados em < 1 segundo
  - Salvamento de cliente completa em < 2 segundos

#### 4.2 Tratamento de Erros

- [ ] **Cenários de erro**
  - Erro de rede é tratado graciosamente
  - Timeout de requisição exibe mensagem apropriada
  - Erro de validação no backend é exibido ao usuário

#### 4.3 Encoding UTF-8 (Windows)

- [ ] **Caracteres especiais**
  - Nomes com acentuação são salvos/exibidos corretamente
  - Emojis (se permitidos) são tratados adequadamente
  - Logs não apresentam `UnicodeEncodeError`

---

### 5. Testes de Interface

#### 5.1 Responsividade

- [ ] **Redimensionamento de janela**
  - Aplicativo se adapta a diferentes tamanhos de janela
  - Elementos não ficam cortados/sobrepostos
  - Scroll aparece quando necessário

#### 5.2 Temas

- [ ] **Alternância de temas**
  - Troca entre light/dark mode funciona
  - Todos os componentes refletem o tema selecionado
  - Preferência de tema é salva

---

## 📝 Registro de Evidências

### Modelo de Registro

Para cada execução do checklist, preencher:

```markdown
### Execução: [Data] - [Versão] - [Ambiente]

**Testador:** [Nome]  
**Build:** [Hash do commit / Tag]  
**OS:** Windows 10/11  
**Python:** 3.13.x

#### Resultados:

- ✅ Todos os testes passaram
- ⚠️ [X] testes falharam (detalhar abaixo)
- ❌ Bloqueador encontrado (detalhar abaixo)

#### Notas:
[Observações, bugs encontrados, etc.]

#### Screenshots/Logs:
[Anexar prints ou links para logs]
```

---

## 🔄 Frequência de Execução

- **Obrigatório:**
  - Antes de cada release de produção (tag `v*`)
  - Após merge de features críticas

- **Recomendado:**
  - Semanalmente no branch `develop`
  - Após correção de bugs críticos

---

## 📊 Critérios de Aprovação

Para uma release ser aprovada:

1. **100% dos itens obrigatórios** marcados como ✅
2. **Nenhum bloqueador** (`❌`) pendente
3. **Warnings** (`⚠️`) documentados e aceitos como risco

---

## 🚨 Fluxo de Falha

Se um teste falhar:

1. **Registrar** o problema no GitHub Issues
2. **Priorizar** conforme severidade:
   - **Bloqueador:** Impede release
   - **Crítico:** Deve ser corrigido antes do release
   - **Normal:** Pode ser adiado para próxima versão

3. **Re-executar** checklist após correção

---

## 🔗 Referências

- [FASE_5_RELEASE.md](./FASE_5_RELEASE.md) - Documentação da fase anterior
- [CHANGELOG.md](../CHANGELOG.md) - Histórico de mudanças
- [CI Workflow](../.github/workflows/ci.yml) - Pipeline de CI/CD

---

## 📌 Notas

- Este checklist complementa (não substitui) os testes automatizados
- Foco em **validação funcional de ponta a ponta**
- Atualizar este documento conforme novas features são adicionadas

---

**Última atualização:** 2026-01-24  
**Responsável:** Time de QA / DevOps
