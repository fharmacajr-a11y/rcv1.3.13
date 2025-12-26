# Arquitetura de Testes - RC Gestor de Clientes

**Projeto:** RC - Gestor de Clientes  
**Versão:** v1.3.92  
**Branch:** qa/fixpack-04  
**Última atualização:** 7 de dezembro de 2025 (FASE 12 - Fechamento Final)

---

## 📋 Visão Geral

O projeto RC - Gestor de Clientes mantém uma **suíte de testes robusta e bem organizada** seguindo as melhores práticas da comunidade Python e pytest ([docs.pytest.org](https://docs.pytest.org)).

**Princípios fundamentais:**

- ✅ **Separação clara:** Testes unitários vs. funcionais/integração
- ✅ **Cobertura abrangente:** Core, módulos, adapters e UI
- ✅ **Execução seletiva:** Uso de markers e filtros para testes rápidos ou completos
- ✅ **Histórico preservado:** Testes legados arquivados para referência

**Ferramentas utilizadas:**

- **pytest** 8.4.2 - Framework de testes
- **pytest-cov** 7.0.0 - Cobertura de código
- **ruff** - Linting (PEP 8, imports não usados, etc.)
- **pyright** - Type checking estático

---

## 📁 Estrutura de Pastas

```
tests/
├── unit/                    # Testes unitários (funções/classes isoladas)
│   ├── core/               # Lógica de negócio central
│   ├── utils/              # Utilitários genéricos
│   ├── modules/            # Módulos de interface (clientes, senhas, hub)
│   ├── adapters/           # Adapters (Supabase, storage)
│   ├── helpers/            # Formatadores e helpers
│   ├── infra/              # Infraestrutura (HTTP, repos)
│   └── security/           # Segurança e criptografia
│
├── modules/                # Testes funcionais/integração por módulo
│   ├── passwords/          # Fluxos de senhas
│   ├── clientes/           # Fluxos de clientes
│   ├── hub/                # Dashboard e navegação
│   ├── uploads/            # Upload de arquivos
│   ├── lixeira/            # Lixeira (arquivados)
│   └── auditoria/          # Auditoria de mudanças
│
├── integration/            # Testes de integração (componentes reais)
│   ├── passwords/          # Integração com storage/crypto
│   └── uploads/            # Integração com Supabase Storage
│
├── archived/               # ⚠️ Testes LEGACY (NÃO executados)
│   ├── passwords/          # 6 arquivos antigos de senhas
│   ├── clientes/           # 1 arquivo antigo de obrigações
│   ├── README.md           # Documentação do diretório
│   └── INDEX.md            # Índice detalhado dos arquivos
│
├── tools/                  # Testes de ferramentas (PDF, converters)
├── adapters/               # Testes de adapters externos
├── helpers/                # Testes de formatadores/helpers
├── shared/                 # Testes de código compartilhado
├── ui/                     # Testes de componentes UI
├── data/                   # Testes de camada de dados
├── core/                   # Testes de lógica de negócio
└── conftest.py             # Fixtures globais
```

### **Níveis de Teste**

| Nível | Localização | Foco | Velocidade | Exemplo |
|-------|-------------|------|------------|---------|
| **Unit** | `tests/unit/` | Funções/classes isoladas, sem I/O | ⚡ Rápido | Testar `only_digits("123-ABC")` retorna `"123"` |
| **Functional** | `tests/modules/` | Fluxos de módulos, mocks leves | 🏃 Médio | Testar criação de senha do início ao fim |
| **Integration** | `tests/integration/` | Componentes reais (DB, storage) | 🐢 Lento | Upload real para Supabase Storage |
| **Archived** | `tests/archived/` | Histórico, não executados | ❌ N/A | Testes pré-refatoração |

---

## 🔍 Descoberta e Execução de Testes

### **Configuração (pytest.ini)**

```ini
[pytest]
pythonpath = ["src", "infra", "adapters"]
testpaths = tests
norecursedirs = .venv venv build dist .git __pycache__ tests/archived
addopts = -q --cov --cov-report=term-missing --cov-fail-under=25
```

**Pontos-chave:**

- ✅ **testpaths:** pytest varre apenas o diretório `tests/`
- ✅ **norecursedirs:** Ignora `tests/archived/` (testes LEGACY)
- ✅ **addopts:** Cobertura ativada por padrão (mínimo 25%)

### **Padrões de Nomenclatura**

| Padrão | Descrição | Exemplo |
|--------|-----------|---------|
| `test_*.py` | Arquivos de teste | `test_passwords_service.py` |
| `Test*` | Classes de teste | `class TestPasswordsController:` |
| `test_*` | Métodos de teste | `def test_create_password_success():` |

### **Comandos Comuns**

```bash
# Executar todos os testes
pytest tests -v

# Testes unitários apenas
pytest tests/unit -v

# Testes de um módulo específico
pytest tests/modules/passwords -v

# Testes por palavra-chave (CNPJ, senhas, etc.)
pytest tests -k "cnpj" -v
pytest tests -k "password" -v

# Testes com cobertura detalhada
pytest tests --cov --cov-report=html

# Coletar testes sem executar (validação)
pytest tests --collect-only -q

# Executar apenas testes rápidos (unitários)
pytest tests/unit --maxfail=1 -x
```

### **Execução Seletiva por Marker**

```python
# Marcar teste como lento
@pytest.mark.slow
def test_large_batch_processing():
    ...

# Marcar teste de integração
@pytest.mark.integration
def test_real_database_connection():
    ...

# Pular teste (método obsoleto)
@pytest.mark.skip(reason="Método _delete_selected não existe mais")
def test_legacy_delete_method():
    ...
```

**Executar apenas testes NÃO marcados como lentos:**
```bash
pytest tests -m "not slow" -v
```

---

## 📐 Padrões de Especificação

### **Convenções de Nomes**

#### **Classes de Teste**

```python
class TestNomeDaFuncionalidade:
    """Testes para [módulo/função/classe específica]."""

    def test_quando_condicao_entao_resultado(self):
        """Deve [comportamento esperado] quando [condição]."""
        ...
```

**Exemplos reais:**
- `class TestFmtDatetimeBr:` - Testes de formatação de data
- `class TestPasswordsController:` - Testes do controller de senhas
- `class TestCnpjValidation:` - Testes de validação de CNPJ

#### **Métodos de Teste**

**Padrão recomendado:** `test_<ação>_<condição>_<resultado>`

```python
# ✅ BOM - Descritivo e autoexplicativo
def test_format_cnpj_returns_empty_for_none():
    assert format_cnpj(None) == ""

def test_is_valid_cnpj_rejects_invalid_dv():
    assert not is_valid_cnpj("11222333000181")  # DV incorreto

# ❌ EVITAR - Genérico demais
def test_cnpj():
    ...

def test_validation():
    ...
```

### **Estrutura AAA (Arrange-Act-Assert)**

```python
def test_strip_diacritics_removes_accents():
    # Arrange (Preparar)
    input_text = "José da Silva"
    expected = "Jose da Silva"

    # Act (Agir)
    result = strip_diacritics(input_text)

    # Assert (Verificar)
    assert result == expected
```

### **Uso de Fixtures**

```python
# Fixture em conftest.py
@pytest.fixture
def sample_client_data():
    """Dados de exemplo de um cliente."""
    return {
        "nome": "Empresa ABC",
        "cnpj": "11222333000165",
        "whatsapp": "11987654321"
    }

# Uso no teste
def test_create_client_success(sample_client_data):
    client = create_client(sample_client_data)
    assert client["nome"] == "Empresa ABC"
```

---

## 🗂️ Arquivos Arquivados (tests/archived/)

### **O que são?**

Testes antigos de versões anteriores do projeto que foram **substituídos por versões mais recentes** após refatorações estruturais.

### **Por que existem?**

1. **Referência histórica:** Entender decisões de design antigas
2. **Arqueologia de código:** Consultar como funcionalidades eram testadas antes
3. **Documentação implícita:** Cenários de teste podem revelar comportamentos não documentados

### **Por que NÃO são executados?**

- ❌ **Arquitetura desatualizada:** Baseados em estrutura pré-refatoração (REF-001)
- ❌ **Imports quebrados:** Referências a pacotes que não existem mais (`passwords.test_*`)
- ❌ **Substituídos completamente:** Testes oficiais atuais cobrem os mesmos cenários
- ❌ **Marcados com skip:** Todos têm `pytest.skip(allow_module_level=True)`

### **Como consultar?**

1. **Índice completo:** Ver `tests/archived/INDEX.md`
2. **Documentação:** Ver `tests/archived/README.md`
3. **Mapeamento:** Cada arquivo LEGACY tem referência ao teste oficial substituto

**Exemplo de arquivo arquivado:**

```python
# tests/archived/passwords/LEGACY_test_passwords_service.py

pytest.skip(
    "Legacy tests de Senhas (pré-refactor). Mantidos apenas como referência. "
    "Senhas agora é coberto por testes em tests/modules/passwords e "
    "tests/integration/passwords.",
    allow_module_level=True,
)
```

### **Configuração**

O `pytest.ini` garante que `tests/archived/` **não seja varrido**:

```ini
norecursedirs = .venv venv build dist .git __pycache__ tests/archived
```

**Validação:**
```bash
# Deve retornar 0 itens
pytest tests -k "LEGACY" --collect-only -q
```

---

## 🔗 Relação com as Fases 1–6

Esta arquitetura de testes é resultado de **6 fases de consolidação e limpeza**:

| Fase | Foco | Impacto em Testes |
|------|------|-------------------|
| **FASE 1** | `only_digits` canônico | Testes criados em `tests/unit/core/test_string_utils.py` |
| **FASE 2** | `format_cnpj` canônico | Testes criados em `tests/unit/helpers/test_format_cnpj_canonical_fase2.py` |
| **FASE 3** | CNPJ (normalize + DV) | Testes criados em `tests/unit/core/test_cnpj_norm_canonical_fase3.py` |
| **FASE 4** | Normalização de texto | Testes criados em `tests/unit/core/test_text_normalization_canonical_fase4.py` |
| **FASE 5** | Formatação de datas | Testes criados em `tests/unit/helpers/test_formatters_datetime_fase5.py` |
| **FASE 6** | Arquivamento LEGACY | 7 arquivos movidos para `tests/archived/` |

**Para o histórico completo das refatorações, consulte:** [`docs/CLEANUP_HISTORY.md`](./CLEANUP_HISTORY.md)

---

## 📊 Cobertura de Código

### **Meta Atual**

- **Mínimo:** 25% (configurado em `pytest.ini`)
- **Recomendado:** > 70% para módulos críticos (senhas, clientes, CNPJ)

### **Gerar Relatório HTML**

```bash
pytest tests --cov --cov-report=html
# Abrir: htmlcov/index.html
```

### **Áreas Críticas de Cobertura**

| Módulo | Importância | Meta de Cobertura |
|--------|-------------|-------------------|
| `src/core/cnpj_norm.py` | 🔴 Crítico | > 90% |
| `src/modules/passwords/` | 🔴 Crítico | > 80% |
| `src/helpers/formatters.py` | 🟡 Alto | > 75% |
| `src/utils/validators.py` | 🟡 Alto | > 70% |
| `adapters/storage/` | 🟢 Médio | > 60% |

---

## 🚀 Boas Práticas

### **✅ O que fazer**

1. **Testes rápidos:** Prefira mocks para I/O (DB, API, filesystem)
2. **Testes isolados:** Cada teste deve ser independente
3. **Nomenclatura clara:** Nome do teste deve documentar comportamento
4. **Fixtures compartilhadas:** Use `conftest.py` para reutilização
5. **Arrange-Act-Assert:** Estrutura clara de preparação → ação → verificação

### **❌ O que evitar**

1. **Testes genéricos:** `test_validation()` sem contexto
2. **Dependências entre testes:** Ordem de execução não é garantida
3. **Hardcoded paths:** Use fixtures com paths temporários
4. **Ignorar falhas:** Investigate `pytest.mark.skip` antes de usar
5. **Testes longos:** > 50 linhas → considere quebrar em múltiplos testes

---

## 📚 Recursos Adicionais

- **pytest oficial:** [docs.pytest.org](https://docs.pytest.org)
- **Histórico de refatorações:** [docs/CLEANUP_HISTORY.md](./CLEANUP_HISTORY.md)
- **Arquivos LEGACY:** [tests/archived/INDEX.md](../tests/archived/INDEX.md)
- **Configuração:** [pytest.ini](../pytest.ini)

---

## 🔄 Manutenção

### **Quando adicionar novos testes:**

1. **Identifique o nível:** Unit, functional ou integration?
2. **Escolha o diretório:** `tests/unit/`, `tests/modules/` ou `tests/integration/`
3. **Nomeie adequadamente:** `test_<módulo>_<funcionalidade>.py`
4. **Documente:** Docstring na classe/método explicando o que testa
5. **Execute:** Garanta que passou antes de commitar

### **Quando arquivar testes:**

1. **Confirme substituto:** Certifique-se que teste novo cobre os cenários
2. **Mova para archived:** `tests/archived/<módulo>/LEGACY_test_*.py`
3. **Atualize INDEX.md:** Adicione entrada em `tests/archived/INDEX.md`
4. **Documente:** Adicione referência ao teste substituto

### **Quando refatorar código:**

1. **Execute testes antes:** Baseline de funcionalidade
2. **Execute testes durante:** Validação contínua
3. **Execute testes depois:** Confirmação de não-regressão
4. **Atualize testes:** Se comportamento mudou intencionalmente

---

## 📚 Documentação Complementar

Boa parte da consolidação e limpeza de duplicações/helpers foi realizada entre versões v1.3.92+ através das **FASES 1-11** de refatoração técnica.

Para contexto completo:
- **[CLEANUP_HISTORY.md](./CLEANUP_HISTORY.md)** - Histórico detalhado das FASES 1-11
- **[CLEANUP_STATUS_FINAL.md](./CLEANUP_STATUS_FINAL.md)** - Estado final consolidado
- **[NAMING_GUIDELINES.md](./NAMING_GUIDELINES.md)** - Convenções de nomes

---

**Última revisão:** 7 de dezembro de 2025 (FASE 12 - Fechamento Final)  
**Responsáveis:** Equipe de Qualidade - RC Gestor
