# Smoke Test - v1.5.64-rc.1

## 📋 Informações da Release

| Item | Valor |
|------|-------|
| Versão | v1.5.64-rc.1 |
| Data do teste | _[preencher]_ |
| Testador | _[preencher]_ |
| Sistema Operacional | Windows _[versão]_ |
| Python instalado? | ❌ Não (máquina limpa) |

## ✅ Checklist de Validação

### 1. Instalação
- [ ] Baixado instalador `rcgestor-v1.5.64-rc.1.exe` da release
- [ ] Verificado checksum SHA256 → ✅ Match
- [ ] Executado instalador → ✅ Sem erros
- [ ] Aplicação iniciou corretamente → ✅

**Observações**:
```
[Registrar observações sobre a instalação]
```

### 2. Alternância de Tema (CRÍTICO)
- [ ] Menu → Configurações → Tema
- [ ] Alternar de Light para Dark → ✅ Sem crash
- [ ] Alternar de Dark para Light → ✅ Sem crash
- [ ] Tema aplicado corretamente em todos os widgets → ✅
- [ ] Treeview muda de cor conforme tema → ✅
- [ ] Scrollbar segue estilo do tema → ✅

**Observações**:
```
[Registrar comportamento observado, screenshots se necessário]
```

### 3. Módulo ClientesV2 (CRÍTICO)
- [ ] Abrir módulo "Clientes" → ✅ Sem erro
- [ ] Treeview renderiza corretamente → ✅
- [ ] Scrollbar funcional → ✅
- [ ] Busca de clientes funciona → ✅
- [ ] Duplo clique em cliente → ✅ Abre detalhes
- [ ] Alternância de tema com Treeview aberta → ✅ Atualiza corretamente

**Observações**:
```
[Registrar comportamento do Treeview]
```

### 4. Encoding UTF-8 (CRÍTICO)
- [ ] Nomes com acentos renderizam corretamente → ✅
- [ ] Caracteres especiais (ç, ã, õ, etc.) → ✅
- [ ] Logs não mostram erros de encoding → ✅
- [ ] Mensagens de erro em português → ✅

**Observações**:
```
[Registrar qualquer problema de encoding]
```

### 5. Estabilidade Geral
- [ ] App não trava após 5 minutos de uso → ✅
- [ ] Consumo de memória estável (não cresce indefinidamente) → ✅
- [ ] Alternância de tema 10x → ✅ Sem degradação
- [ ] Fechar e reabrir módulos → ✅ Sem memory leaks observáveis

**Observações**:
```
[Registrar métricas de memória/CPU se possível]
```

### 6. Funcionalidades Core
- [ ] Login funciona → ✅
- [ ] Navegação entre módulos → ✅
- [ ] Export de dados → ✅
- [ ] Notificações aparecem → ✅
- [ ] Atalhos de teclado funcionam → ✅

**Observações**:
```
[Registrar funcionalidades testadas]
```

## 🐛 Bugs Encontrados

### Bug #1: [Título]
- **Severidade**: 🔴 Critical / 🟡 Major / 🟢 Minor
- **Descrição**:
- **Passos para reproduzir**:
  1.
  2.
  3.
- **Comportamento esperado**:
- **Comportamento observado**:
- **Screenshots/Logs**:

---

### Bug #2: [Título]
_[Repetir formato acima]_

---

## 📊 Resultado Final

| Categoria | Status | Notas |
|-----------|--------|-------|
| Instalação | ✅ / ⚠️ / ❌ | |
| Alternância de Tema | ✅ / ⚠️ / ❌ | |
| ClientesV2 (Treeview) | ✅ / ⚠️ / ❌ | |
| Encoding UTF-8 | ✅ / ⚠️ / ❌ | |
| Estabilidade | ✅ / ⚠️ / ❌ | |
| Funcionalidades Core | ✅ / ⚠️ / ❌ | |

### Decisão Final

- [ ] ✅ **APROVADO** - Release pode ir para produção
- [ ] ⚠️ **APROVADO COM RESSALVAS** - Bugs menores aceitáveis
- [ ] ❌ **REPROVADO** - Requer correções antes de produção

**Justificativa**:
```
[Explicar decisão final]
```

## 📝 Notas Adicionais

```
[Qualquer observação adicional relevante]
```

---

**Assinatura**: _[Nome do testador]_  
**Data**: _[DD/MM/YYYY HH:MM]_
