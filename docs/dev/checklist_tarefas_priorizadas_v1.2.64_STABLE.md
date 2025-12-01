# Checklist de Tarefas – v1.2.64 STABLE (Reset)

**Data:** 23 de novembro de 2025  
**Base:** v1.2.64 (após refactor/coverage/alta prioridade estabilizados)  
**Branch:** qa/fixpack-04  
**Contexto:** Checklist consolidado após conclusão de BUG-PROD-*, COV-*, VERIFY-CHANGES-001 e HIGH-RISK-REVIEW-001

---

## 📋 Legenda

- **P0** 🔴 **CRÍTICO** - Bloqueadores, bugs graves, segurança crítica
- **P1** 🟡 **IMPORTANTE** - Funcionalidade essencial, manutenibilidade, performance
- **P2** 🟢 **DESEJÁVEL** - Melhorias, documentação, qualidade de código
- **P3** ⚪ **COSMÉTICO / LONGO PRAZO** - Nice-to-have, arquitetura futura

---

## 📊 Status Atual do Projeto

### Suíte de Testes
- ✅ **1253+ testes passando** (100% de sucesso)
- ✅ Infraestrutura de isolamento implementada (conftest.py)
- ✅ Coverage global: **43.78%** (meta inicial 25% superada)
- ✅ Auth, prefs, validators, phone_utils, security/crypto com coverage >85%

### Bugs Críticos Resolvidos
- ✅ BUG-PROD-AUTH-001: YAML opcional + helpers de teste
- ✅ BUG-PROD-FASE-B: Testes de integração estabilizados
- ✅ BUG-PROD-SUITE-ISOLATION-001: Isolamento completo implementado
- ✅ ResourceWarnings de SQLite/TemporaryDirectory eliminados

### Módulos de Alto Risco Validados
- ✅ app_actions.py: Nova funcionalidade PDF batch converter
- ✅ auth_bootstrap.py: "Manter conectado" implementado
- ✅ prefs.py: Persistência de login e sessão auth
- ✅ login_dialog.py + splash.py: UI melhorada

---

## P0 – CRÍTICO 🔴

> **Status:** Nenhuma tarefa crítica identificada no momento

O projeto está em estado estável após correções de segurança, bugs de auth e isolamento de testes. Próximas releases podem adicionar P0 conforme surgirem.

---

## P1 – IMPORTANTE 🟡

### Cobertura e Testes

- [ ] **COV-DATA-001: Resolver ciclo de importação em data/supabase_repo.py**
  - **Área:** `data/supabase_repo.py`, arquitetura de imports
  - **Descrição:** Refatorar para quebrar ciclo `data.supabase_repo → infra.supabase_client → ... → adapters.storage → infra.supabase_client`
  - **Motivo:** Bloqueio de testes unitários e coverage (~16.2% atual, meta >50%)
  - **Esforço:** ALTO (6-10h) - Requer refatoração arquitetural cuidadosa
  - **Bloqueador:** Sim - Impede aumento de coverage de módulo crítico
  - **Referência:** `dev/cov_data_supabase_repo.md`
  - **Próximos passos:**
    1. Analisar cadeia completa de imports
    2. Identificar ponto de quebra do ciclo (sugestão: extrair tipos compartilhados)
    3. Refatorar imports mantendo comportamento
    4. Validar que app não quebra
    5. Criar testes com coverage >50%

- [ ] **COV-INFRA-001: Aumentar coverage de infra/settings.py**
  - **Área:** `infra/settings.py`
  - **Descrição:** Criar testes para carregamento de .env, fallbacks, validação de variáveis
  - **Motivo:** Módulo crítico de configuração com coverage atual ~97.3% (2 linhas faltando)
  - **Esforço:** BAIXO (2-3h)
  - **Referência:** `dev/cov_infra_settings_storage_client.md`
  - **Meta:** Atingir 100% coverage

- [ ] **COV-ADAPTERS-001: Completar coverage de adapters/storage**
  - **Área:** `adapters/storage/supabase_storage.py`, `adapters/storage/api.py`
  - **Descrição:** Adicionar testes para edge cases de upload/download, error handling
  - **Motivo:** Coverage atual 78.9% (supabase_storage) e 62.7% (api)
  - **Esforço:** MÉDIO (4-6h)
  - **Meta:** >85% em ambos os módulos

### Validação e Qualidade

- [ ] **VAL-MANUAL-001: Validação manual de funcionalidade "Manter conectado"**
  - **Área:** UI, auth_bootstrap, login_dialog
  - **Descrição:** Testar fluxo completo na aplicação real:
    1. Login com checkbox "Manter conectado" marcado
    2. Fechar aplicação
    3. Reabrir e validar que sessão foi restaurada (sem pedir login)
    4. Testar expiração após 7 dias (mockar data do sistema)
  - **Motivo:** Funcionalidade nova com mudanças significativas (+176 linhas em prefs, +93 em auth_bootstrap)
  - **Esforço:** BAIXO (1-2h de testes manuais)
  - **Crítico antes de release:** Sim

- [ ] **VAL-VISUAL-001: Validação visual de splash e login dialog**
  - **Área:** `src/ui/splash.py` (+92 linhas), `src/ui/login_dialog.py` (+58 linhas)
  - **Descrição:** Validar visualmente que:
    - Splash screen aparece centralizada e sem travamentos
    - Login dialog carrega email salvo corretamente
    - Checkbox "Manter conectado" persiste entre sessões
  - **Esforço:** BAIXO (30min-1h)

### Build e CI/CD

- [ ] **BUILD-004: Adicionar job de linting no CI**
  - **Área:** GitHub Actions
  - **Descrição:** Configurar Ruff/Flake8 para rodar em PRs
  - **Comando:** `ruff check . --select=E,F,W`
  - **Benefício:** Detectar problemas de qualidade antes do merge
  - **Esforço:** BAIXO (1-2h)

- [ ] **BUILD-003: Cache de dependências no CI**
  - **Área:** `.github/workflows/`
  - **Descrição:** Usar `actions/cache` para pip packages
  - **Benefício:** Reduzir tempo de build de ~5min para ~2min
  - **Esforço:** BAIXO (1h)

---

## P2 – DESEJÁVEL 🟢

### Documentação

- [ ] **DOC-001: Criar README.md principal**
  - **Área:** Raiz do projeto
  - **Descrição:** README com overview, setup, build, contribuição
  - **Seções:** Descrição, Features, Instalação, Build, Testes, Licença
  - **Benefício:** Onboarding de novos devs
  - **Esforço:** MÉDIO (2-3h)

- [ ] **DOC-002: Documentar funcionalidade "Manter conectado"**
  - **Área:** Docs de usuário
  - **Descrição:** Explicar que sessão dura 7 dias, como ativar/desativar
  - **Esforço:** BAIXO (30min)

- [ ] **DOC-003: Consolidar relatórios de dev/**
  - **Área:** `dev/*.md`, `docs/dev/*.md`
  - **Descrição:** Revisar e arquivar relatórios antigos, manter apenas os relevantes
  - **Exemplo:** Mover `resultado_*.txt` para subpasta `dev/archive/`
  - **Benefício:** Reduzir ruído, facilitar navegação
  - **Esforço:** BAIXO (1-2h)

### Build e Distribuição

- [ ] **BUILD-001: Otimizar tamanho do executável**
  - **Área:** PyInstaller, `rcgestor.spec`
  - **Descrição:** Reduzir de ~120MB para ~80MB removendo dependências não usadas
  - **Técnicas:** `--exclude-module`, tree shaking, UPX compression
  - **Benefício:** Download e instalação mais rápidos
  - **Esforço:** MÉDIO (3-5h)

- [ ] **BUILD-002: Criar instalador Windows (Inno Setup)**
  - **Área:** `installers/windows/`
  - **Descrição:** Script .iss para instalador com ícone, shortcuts, uninstaller
  - **Benefício:** Distribuição profissional para usuários finais
  - **Esforço:** MÉDIO (4-6h)

### Código e Arquitetura

- [ ] **CODE-002: Remover arquivos temporários versionados**
  - **Área:** Raiz, `tests/`
  - **Descrição:** Limpar `__pycache__`, `.pytest_cache`, arquivos `.pyc` do git
  - **Ação:** `git rm -r --cached __pycache__`, adicionar ao `.gitignore`
  - **Benefício:** Repositório mais limpo
  - **Esforço:** BAIXO (15min)

- [ ] **CODE-003: Mover relatórios da raiz para docs/**
  - **Área:** `*.txt`, `*.md` na raiz
  - **Descrição:** Organizar arquivos soltos em estrutura docs/
  - **Benefício:** Melhor organização do projeto
  - **Esforço:** BAIXO (30min)

### Ferramentas

- [ ] **TOOL-002: Integrar bandit no CI**
  - **Área:** GitHub Actions
  - **Descrição:** Scanner de segurança estática
  - **Comando:** `bandit -r src/ -ll`
  - **Benefício:** Detectar vulnerabilidades em código Python
  - **Esforço:** BAIXO (1-2h)

- [ ] **TOOL-003: Ajustar configuração do Ruff**
  - **Área:** `ruff.toml`
  - **Descrição:** Adicionar regras de complexidade (C90), naming (N)
  - **Benefício:** Código mais consistente e legível
  - **Esforço:** BAIXO (1h)

---

## P3 – COSMÉTICO / LONGO PRAZO ⚪

### Arquitetura

- [ ] **ARCH-001: Resolver ciclo de importação global**
  - **Área:** Arquitetura completa do projeto
  - **Descrição:** Refatoração profunda para eliminar todos os ciclos de import (data, infra, adapters, src)
  - **Motivação:** COV-DATA-001 é apenas a ponta do iceberg
  - **Esforço:** MUITO ALTO (20-40h)
  - **Risco:** Alto - Pode quebrar app se não for feito com cuidado extremo
  - **Pré-requisito:** Criar suite completa de testes de integração E2E antes

- [ ] **ARCH-002: Migrar para async/await sistemático**
  - **Área:** Operações de rede, DB, arquivo
  - **Descrição:** Usar asyncio para I/O não bloqueante
  - **Benefício:** UI mais responsiva em redes lentas
  - **Esforço:** MUITO ALTO (30-50h)

### Testes

- [ ] **TEST-E2E-001: Testes E2E de GUI**
  - **Área:** Criar `tests/e2e/`
  - **Descrição:** Testes com pyautogui ou pytest-qt
  - **Cenários:** Login → listagem → upload → logout
  - **Benefício:** Validação de fluxos críticos
  - **Esforço:** MUITO ALTO (15-25h)

### Internacionalização

- [ ] **I18N-001: Suporte a múltiplos idiomas**
  - **Área:** Todo o app
  - **Descrição:** Usar gettext ou babel para i18n
  - **Idiomas:** PT-BR (base), EN, ES
  - **Benefício:** Alcance internacional
  - **Esforço:** MUITO ALTO (40-60h)

### Funcionalidade

- [ ] **FEAT-001: Sistema de plugins**
  - **Área:** Arquitetura extensível
  - **Descrição:** Permitir módulos externos sem recompilar
  - **Benefício:** Customização por cliente
  - **Esforço:** MUITO ALTO (30-50h)

---

## 🎯 Recomendações para Próxima Sprint

### Tarefas Prioritárias (Ordem Sugerida)

1. **VAL-MANUAL-001** - Validar "Manter conectado" (CRÍTICO antes de release)
2. **VAL-VISUAL-001** - Validar splash e login visualmente (CRÍTICO antes de release)
3. **BUILD-004** - Linting no CI (rápido, alto impacto em qualidade)
4. **BUILD-003** - Cache de dependências no CI (rápido, melhora DX)
5. **DOC-001** - README principal (importante para onboarding)
6. **COV-INFRA-001** - Completar coverage de settings.py (baixo esforço, fecha módulo)
7. **COV-ADAPTERS-001** - Aumentar coverage de storage (médio esforço, fecha adapters)

### Tarefas Bloqueadas para Futuro

- **COV-DATA-001**: Requer refatoração arquitetural (ARCH-001) - Não atacar ainda
- **ARCH-001**: Requer suite E2E completa antes de refatorar - Muito arriscado agora

### Comandos Sugeridos para Validação Manual

**Antes da próxima release, rodar:**

```powershell
# Validação completa da suíte
python -m pytest --cov --cov-report=term-missing --cov-fail-under=25 -q

# Verificar ResourceWarnings
python -m pytest -W error::ResourceWarning -q

# Linting
ruff check . --select=E,F,W

# Segurança
bandit -r src/ -ll
```

---

## 📝 Notas Importantes

### Estado Atual (Pontos Fortes)
- ✅ Suíte de testes 100% verde (1253+ testes)
- ✅ Coverage >40% (superou baseline de 25%)
- ✅ Auth e prefs com >85% coverage
- ✅ Infraestrutura de isolamento robusta
- ✅ Módulos de alto risco validados e documentados

### Pontos de Atenção
- ⚠️ COV-DATA-001 bloqueado por ciclo de import (não crítico, mas limita coverage)
- ⚠️ Funcionalidade "Manter conectado" precisa validação manual antes de release
- ⚠️ PDF batch converter novo, sem testes automatizados (baixo risco, funcionalidade isolada)

### Decisões Técnicas para Próximas Versões
- Focar em **estabilidade** e **manutenibilidade** antes de novas features grandes
- Priorizar **documentação** e **CI/CD** para melhorar DX
- Deixar refatorações arquiteturais grandes (ARCH-*) para quando houver suite E2E robusta
- Manter coverage crescendo gradualmente (meta 50% antes de atacar 80%+)

---

**Última atualização:** 23 de novembro de 2025  
**Próxima revisão sugerida:** Após conclusão de VAL-MANUAL-001 e VAL-VISUAL-001
