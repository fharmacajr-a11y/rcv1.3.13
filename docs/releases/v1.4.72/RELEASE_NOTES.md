# RC-Gestor de Clientes - Release Notes v1.4.72

**Data de Lançamento:** 20 de dezembro de 2025

## 📋 Resumo

Atualização de versão 1.4.52 → 1.4.72 com melhorias significativas no sistema de notificações, módulo ANVISA e qualidade de código.

## ✨ Novidades e Melhorias

### Notificações
- **Timezone Local**: Ajuste automático de horários para timezone local do usuário
- **Marcar Tudo como Lido**: Funcionalidade para marcar todas as notificações como lidas de uma vez
- **Coluna "Por"**: Identificação clara do autor de cada notificação
- **Toast Winotify**: Notificações nativas do Windows com melhor UX
- **Melhorias de UI**: Ícones aprimorados e melhor alinhamento visual

### ANVISA
- **Upload de PDFs**: Sistema completo de upload de arquivos por processo
- **Organização Automática**: PDFs organizados automaticamente em `GERAL/anvisa/{process_slug}/`
- **Slugificação**: Nomes de processos normalizados para facilitar busca
- **Interface Intuitiva**: Seleção múltipla de arquivos com feedback visual
- **Tratamento de Erros**: Mensagens claras e recovery automático

### Qualidade e Testes
- **Cobertura de Testes**: Alta cobertura nos módulos críticos:
  - Notificações
  - ANVISA
  - db_client
  - network
- **Validação**: Testes unitários e de integração para features críticas

## 🔧 Correções

- Path de upload ANVISA corrigido para dentro de GERAL
- TypeError no upload de arquivos ANVISA resolvido
- Assinatura de `upload_file()` padronizada
- Melhorias diversas de tratamento de erros

## 📦 Instalação

1. Download: `RC-Gestor-Clientes-1.4.72.exe`
2. Execute o instalador
3. Siga as instruções na tela

## 📚 Documentação

- [CHANGELOG.md](../../CHANGELOG.md) - Histórico completo de mudanças
- [ANVISA_UPLOAD_FEATURE.md](../ANVISA_UPLOAD_FEATURE.md) - Documentação da feature de upload ANVISA

## ⚠️ Notas Importantes

- Esta versão requer Windows 10 ou superior
- Certifique-se de ter as credenciais corretas do Supabase configuradas
- Recomenda-se backup antes da atualização

---

**Versão:** 1.4.72  
**Build:** 20 de dezembro de 2025  
**Plataforma:** Windows (x64)
