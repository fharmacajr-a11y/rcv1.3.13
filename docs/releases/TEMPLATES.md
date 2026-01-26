# 📝 Templates - Release e Pull Request

**Templates padronizados para releases e PRs**

---

## 📦 Release Template

### Título

```
Release v[MAJOR].[MINOR].[PATCH] - [Nome Descritivo]
```

**Exemplos:**
- `Release v1.5.62 - CI/CD Robusto`
- `Release v1.6.0 - Migração CTK Completa`

### Corpo da Release

```markdown
# Release v[VERSION] - [TÍTULO]

**Data:** [YYYY-MM-DD]  
**Tag:** `v[VERSION]`  
**Commit:** `[hash]`

---

## 🎯 Destaques

- 🔥 [Principal feature/mudança]
- ✨ [Segunda feature importante]
- 🐛 [Principais bugs corrigidos]

---

## ✅ Mudanças Principais

### [Categoria 1] (ex: Features)

- Feature A: [descrição]
- Feature B: [descrição]

### [Categoria 2] (ex: Bug Fixes)

- Fix A: [descrição]
- Fix B: [descrição]

### [Categoria 3] (ex: Refactoring)

- Refactor A: [descrição]

---

## 🧪 Validações

- ✅ Pre-commit: [X/20] hooks passing
- ✅ Pytest: [X] tests passing
- ✅ Ruff: 0 errors
- ✅ Bandit: 0 issues
- ✅ Build: Executável gerado com sucesso

---

## 📦 Assets

- [x] `rcgestor-v[VERSION]-windows-x64.exe` (XX MB)
- [ ] `rcgestor-v[VERSION]-linux-x64` (se aplicável)

---

## 📝 Breaking Changes

⚠️ **[Se houver mudanças incompatíveis]**

- Mudança 1: [descrição + como migrar]
- Mudança 2: [descrição + como migrar]

---

## 🔗 Links

- [Milestone](https://github.com/[org]/[repo]/milestone/[N])
- [Pull Requests](https://github.com/[org]/[repo]/pulls?q=milestone%3A[VERSION])
- [Issues Fechadas](https://github.com/[org]/[repo]/issues?q=milestone%3A[VERSION])

---

## 📚 Documentação

- [CHANGELOG.md](../CHANGELOG.md)
- [ROADMAP.md](../docs/ROADMAP.md)
- [Guia de Migração](#) (se aplicável)
```

---

## 🔀 Pull Request Template

### Título

```
[tipo]: [descrição curta]
```

**Tipos:**
- `feat`: Nova funcionalidade
- `fix`: Correção de bug
- `docs`: Mudanças em documentação
- `style`: Formatação, espaços em branco
- `refactor`: Refatoração de código
- `test`: Adição/correção de testes
- `chore`: Tarefas de manutenção

**Exemplos:**
- `feat: adicionar suporte a filtros avançados`
- `fix: corrigir erro de encoding no Windows`
- `docs: consolidar documentação em docs/`

### Corpo do PR

```markdown
## 📋 Descrição

[Descrição clara e concisa das mudanças]

## 🎯 Motivação e Contexto

[Por que essa mudança é necessária? Que problema resolve?]

Closes #[issue-number]

---

## 🔧 Tipo de Mudança

- [ ] 🐛 Bug fix (mudança que corrige um issue)
- [ ] ✨ Nova feature (mudança que adiciona funcionalidade)
- [ ] 💥 Breaking change (fix ou feature que quebra compatibilidade)
- [ ] 📝 Documentação (mudanças apenas em docs)
- [ ] ♻️ Refactoring (mudança que não adiciona feature nem corrige bug)
- [ ] ✅ Testes (adição ou correção de testes)
- [ ] 🔧 Chore (manutenção, configs, dependências)

---

## ✅ Checklist

### Antes de Abrir o PR

- [ ] Código segue style guide do projeto
- [ ] Self-review realizado
- [ ] Comentários adicionados em código complexo
- [ ] Documentação atualizada (se aplicável)
- [ ] Sem warnings de pre-commit
- [ ] Testes passando localmente

### Testes

- [ ] Testes unitários adicionados/atualizados
- [ ] Testes de integração adicionados/atualizados (se aplicável)
- [ ] Smoke test manual realizado

### Validações

```bash
# Executar antes de criar PR
pre-commit run --all-files
pytest tests/modules/clientes_v2/ -v
ruff check src/ tests/
```

**Resultados:**
- [ ] Pre-commit: [X/20] hooks passing
- [ ] Pytest: [X] tests passing  
- [ ] Ruff: 0 errors

---

## 📊 Impacto

### Arquivos Modificados

- `path/to/file1.py` - [descrição da mudança]
- `path/to/file2.py` - [descrição da mudança]

### Métricas

- **Linhas adicionadas:** [+X]
- **Linhas removidas:** [-X]
- **Arquivos alterados:** [X]

---

## 🖼️ Screenshots (se aplicável)

### Antes
[imagem ou descrição]

### Depois
[imagem ou descrição]

---

## 🧪 Como Testar

1. Checkout da branch: `git checkout [branch-name]`
2. Instalar dependências: `pip install -r requirements.txt`
3. Executar testes: `pytest tests/modules/[module]/ -v`
4. Smoke test manual:
   - Passo 1: [descrição]
   - Passo 2: [descrição]
   - Resultado esperado: [descrição]

---

## 📝 Notas Adicionais

[Qualquer informação adicional relevante para revisores]

---

## 🔗 Links Relacionados

- Issue: #[number]
- Documentação: [link]
- PR dependente: #[number] (se aplicável)
```

---

## 🏷️ Label Guidelines

### Por Tipo

- `feat` → 🏷️ `enhancement`
- `fix` → 🏷️ `bug`
- `docs` → 🏷️ `documentation`
- `test` → 🏷️ `testing`
- `chore` → 🏷️ `maintenance`

### Por Prioridade

- 🔴 `priority: critical` - Bloqueador, precisa ser resolvido imediatamente
- 🟠 `priority: high` - Importante, deve ser tratado na sprint atual
- 🟡 `priority: medium` - Pode esperar próxima sprint
- 🟢 `priority: low` - Backlog, quando houver tempo

### Por Escopo

- `scope: ui` - Mudanças em interface
- `scope: backend` - Mudanças em lógica de negócio
- `scope: database` - Mudanças em schema/queries
- `scope: ci-cd` - Mudanças em pipelines
- `scope: docs` - Mudanças em documentação

---

## 📋 Review Checklist (Para Reviewers)

### Code Quality

- [ ] Código é legível e bem estruturado
- [ ] Nomes de variáveis/funções são descritivos
- [ ] Sem código duplicado
- [ ] Complexidade é apropriada
- [ ] Sem code smells óbvios

### Funcionalidade

- [ ] Mudanças atendem aos requisitos
- [ ] Edge cases estão cobertos
- [ ] Tratamento de erros apropriado
- [ ] Validações de input corretas

### Testes

- [ ] Cobertura de testes adequada
- [ ] Testes são claros e concisos
- [ ] Mocks são usados apropriadamente
- [ ] Testes passam no CI

### Documentação

- [ ] Docstrings atualizadas
- [ ] README atualizado (se necessário)
- [ ] CHANGELOG atualizado
- [ ] Comentários explicam "por quê", não "o quê"

### Segurança

- [ ] Sem hardcoded credentials
- [ ] Input sanitization apropriado
- [ ] Sem SQL injection vulnerabilities
- [ ] Sem exposição de dados sensíveis

---

**Última atualização:** 26 de janeiro de 2026
