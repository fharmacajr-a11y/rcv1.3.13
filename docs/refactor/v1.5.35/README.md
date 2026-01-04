# Documentação de Refatoração v1.5.35

> **Baseline criado em:** 2025-01-02  
> **Última atualização:** 2025-01-03 (Fase 7 - Version Bump 1.5.40)  
> **Objetivo:** Consolidar toda a estrutura de código dentro de `src/`

---

## 🎯 Objetivo da Refatoração

Atualmente, o projeto possui código distribuído em múltiplas pastas na raiz:
- `src/` (principal)
- `infra/` (infraestrutura)
- `data/` (repositórios e tipos)
- `adapters/` (adaptadores de storage)
- `security/` (criptografia)

O objetivo é **mover todo o código para dentro de `src/`**, seguindo o padrão `src-layout` recomendado para projetos Python, o que:
1. Simplifica os imports (tudo começa com `src.`)
2. Facilita o empacotamento e distribuição
3. Evita conflitos de nome com pacotes de terceiros
4. Melhora a testabilidade (separação clara fonte/testes)

---

## 📋 Fases de Execução (Atômicas e Seguras)

A refatoração será executada de forma **incremental**, em fases atômicas. **Cada fase move E corrige imports**, garantindo que o app rode ao final.

| Fase | Descrição | Imports Afetados | Status |
|------|-----------|------------------|--------|
| 0 | Documentação baseline | - | ✅ Concluído |
| 0.1 | Correção baseline (recontagem AST) | - | ✅ Concluído |
| 1 | Mover `infra/` → `src/infra/` + corrigir imports `infra` → `src.infra` | 312→0 | ✅ Concluído |
| 2 | Mover `data/` → `src/data/` + corrigir imports `data` → `src.data` | 47→0 | ✅ Concluído |
| 3 | Mover `adapters/` → `src/adapters/` + corrigir imports `adapters` → `src.adapters` | 30→0 | ✅ Concluído |
| 4 | Corrigir imports `security` → `src.security` | 6→0 | ✅ Concluído |
| 4B | pytest stabilization (fix Tkinter `Image.__del__` no Python 3.13) | - | ✅ Concluído |
| 5 | Atualizar `sitecustomize.py` + ajustes PyInstaller | - | ✅ Concluído |
| 6 | Limpeza final (remover pastas vazias, shims legacy) | - | ✅ Concluído |
| 7 | Fix testes 7z + Bump versão 1.5.40 + cleanup configs | - | ✅ Concluído |

### ⚠️ Regras de Ouro

1. **Cada fase = 1 commit atômico**
   - Mover arquivos + corrigir imports na MESMA fase
   - Nunca deixar imports quebrados entre commits

2. **Validação obrigatória após cada fase:**
   - `python -m py_compile main.py` (sintaxe)
   - `python -c "import src"` (imports básicos)
   - Testes relevantes ao módulo movido
   - Build PyInstaller (pelo menos na Fase 5)

3. **Ordem de execução não pode ser alterada**
   - `infra/` primeiro (mais imports, base para outros)
   - `data/` segundo (depende de `security/`, mas `security/` só tem 6 imports)
   - `adapters/` terceiro
   - `security/` quarto
   - Build/cleanup por último

---

## 📊 Resumo de Impacto (via AST)

| Métrica | Valor |
|---------|-------|
| Total de imports a atualizar | **~2033** |
| Arquivos .py analisados | **1001** |
| Arquivos > 500 linhas | **30** |
| Maior arquivo | **1056 linhas** |

### Distribuição por Prefixo

| Prefixo | Imports | Fase | Status |
|---------|---------|------|--------|
| `infra.*` | ~~312~~ → 0 | Fase 1 | ✅ Migrado para `src.infra.*` |
| `data.*` | ~~47~~ → 0 | Fase 2 | ✅ Migrado para `src.data.*` |
| `adapters.*` | ~~30~~ → 0 | Fase 3 | ✅ Migrado para `src.adapters.*` |
| `security.*` | ~~6~~ → 0 | Fase 4 | ✅ Migrado para `src.security.*` |
| `src.modules.*` | 1325 | Não afetados | - |
| `src.utils.*` | 211 | Não afetados | - |
| `src.features.*` | 59 | Não afetados | - |
| `src.helpers.*` | 36 | Não afetados | - |
| `src.shared.*` | 7 | Não afetados | - |

---

## 📁 Documentos desta Pasta

| Arquivo | Descrição |
|---------|-----------|
| [00_contexto_e_regras.md](00_contexto_e_regras.md) | Regras de ouro e contexto da refatoração |
| [00b_correcao_baseline.md](00b_correcao_baseline.md) | Correção do baseline com AST |
| [01_arvore_atual.md](01_arvore_atual.md) | Estrutura de diretórios relevante |
| [02_mapa_imports_baseline.md](02_mapa_imports_baseline.md) | Levantamento de imports (ATUALIZADO) |
| [03_entrypoints_e_build.md](03_entrypoints_e_build.md) | Pontos de entrada e configuração de build |
| [04_lista_arquivos_grandes.md](04_lista_arquivos_grandes.md) | Top 30 arquivos >500 linhas (ATUALIZADO) |
| [05_fase1_infra.md](05_fase1_infra.md) | Documentação da Fase 1 |
| [06_fase2_data.md](06_fase2_data.md) | Documentação da Fase 2 |
| [07_fase3_adapters.md](07_fase3_adapters.md) | Documentação da Fase 3 |
| [08_fase4_security.md](08_fase4_security.md) | Documentação da Fase 4 |
| [09_fase4b_pytest_stabilization.md](09_fase4b_pytest_stabilization.md) | Fase 4B - Fix Tkinter pytest (Python 3.13) |
| [10_fase5_sitecustomize_pyinstaller.md](10_fase5_sitecustomize_pyinstaller.md) | Fase 5 - sitecustomize.py + PyInstaller |
| [11_fase6_cleanup_final.md](11_fase6_cleanup_final.md) | Fase 6 - Limpeza final |
| [12_fase7_version_bump_1.5.40.md](12_fase7_version_bump_1.5.40.md) | **NOVO:** Fase 7 - Fix 7z + Bump 1.5.40 |

---

## 🔗 Referências

- Código-fonte: `v1.5.35` (equivalente ao zip atual)
- Build spec: `rcgestor.spec`
- Entrypoint: `main.py` → `src.app_gui`
