# 📦 Release Notes - RC Gestor

**Histórico consolidado de releases do projeto**

---

## v1.5.62 - FASE 4-6: CI/CD Robusto (Jan 2026)

**Data:** 2026-01-24  
**Tags:** `v1.5.62-fase4.3`  
**Status:** ✅ Produção

### Destaques

- 🔒 **Security hardening** com Bandit
- 🧹 **Dead code cleanup** com Vulture  
- 🔄 **CI/CD completo** (Windows + Linux)
- 📝 **UTF-8 encoding** garantido
- ✅ **Pre-commit hooks** (20 validações)

### Mudanças Principais

**FASE 4.3: Limpeza e Segurança**
- Vulture scan: 16 issues corrigidos
- Bandit: 0 security issues (todos tratados)
- Whitelist criada para false positives
- 19 legacy forms identificados

**FASE 5: Release + UTF-8**
- Fix de encoding no Windows (cp1252 → UTF-8)
- Hook Bandit UTF-8 safe
- Tag anotada criada
- Documentação atualizada

**FASE 6: CI/CD**
- GitHub Actions configurado
- Matrix testing (multi-OS)
- Release automatizada
- Staging checklist completo

### Validações

- ✅ Pre-commit: 20/20 hooks passing
- ✅ Pytest: 113/113 passing
- ✅ Ruff: 0 errors  
- ✅ Bandit: 0 issues

### Arquivos Modificados

- `.pre-commit-config.yaml` - Bandit UTF-8 safe
- `.bandit` - Configuração otimizada
- `vulture_whitelist.py` - Whitelist de false positives
- `docs/FASE_*.md` - Documentação das fases
- `docs/QUICK_REFERENCE_CI.md` - Guia rápido
- `docs/STAGING_CHECKLIST.md` - Roteiro de smoke test

**Documentação detalhada:**
- [../ROADMAP.md](../ROADMAP.md#fase-4-limpeza-e-segurança-jan-2026)
- [../_archive/FASE_4.3_RESUMO.md](../_archive/FASE_4.3_RESUMO.md)
- [../_archive/FASE_5_RELEASE.md](../_archive/FASE_5_RELEASE.md)
- [../_archive/FASE_6_CI_RELEASE.md](../_archive/FASE_6_CI_RELEASE.md)

---

## v1.5.61 - Migração CustomTkinter

**Data:** 2025-12  
**Status:** ✅ Produção

### Destaques

- 🎨 **Migração completa** de ttkbootstrap → CustomTkinter
- 📦 **53 microfases** documentadas
- 🧪 **Testes estáveis** (112+ passing)
- 📐 **Type safety** melhorado

### Principais Módulos Migrados

- `src/modules/clientes_v2/` - Módulo principal de clientes
- `src/ui/` - Componentes UI reutilizáveis
- `src/modules/hub/` - Dashboard principal

**Documentação:**
- [../customtk/MIGRATION_SUMMARY.md](../customtk/MIGRATION_SUMMARY.md)
- [../customtk/_archive/](../customtk/_archive/) - 53 microfases

---

## v1.5.60 - Refatoração Estrutural

**Data:** 2025-11  
**Status:** ✅ Produção

### Destaques

- 📁 **Src-layout** implementado
- 🔧 **Separação de concerns** (adapters, infra, core)
- 🧪 **Testes unitários** básicos
- 📝 **Documentação** inicial

**Documentação:**
- [../refactor/v1.5.35/](../refactor/v1.5.35/)

---

## Releases Anteriores

### v1.5.x Series (2025)

- v1.5.35 - Estrutura base refatorada
- v1.5.30 - Primeiros módulos de testes
- v1.5.20 - Implementação de adapters

### v1.4.x Series (2024)

- v1.4.10 - Base ttkbootstrap estável
- v1.4.0 - Primeira versão com UI moderna

---

## 📊 Sumário de Releases

| Versão | Data | Destaques | Status |
|--------|------|-----------|--------|
| 1.5.62 | 2026-01 | CI/CD + Security | ✅ Produção |
| 1.5.61 | 2025-12 | Migração CTK | ✅ Produção |
| 1.5.60 | 2025-11 | Refatoração | ✅ Produção |
| 1.5.35 | 2025-10 | Src-layout | ✅ Produção |

---

## 🔮 Roadmap Futuro

### v1.6.0 (Q1 2026)

- Migração completa CustomTkinter
- Remoção de ttkbootstrap
- Python 3.13 oficial no PyInstaller
- Cobertura de testes >90%

### v2.0.0 (Q2 2026)

- Arquitetura modular completa
- Plugins externos
- API REST
- Multi-tenant support

---

**Para mais detalhes:**
- [STATUS.md](../STATUS.md) - Estado atual
- [ROADMAP.md](../ROADMAP.md) - Histórico completo
- [TEMPLATES.md](TEMPLATES.md) - Templates de release/PR
