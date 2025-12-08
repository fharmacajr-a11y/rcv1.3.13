# Testes Arquivados (LEGACY)

Este diretório contém testes antigos que foram substituídos por versões mais recentes.

## ⚠️ NÃO EXECUTAR ESTES TESTES

Os arquivos aqui são mantidos apenas para **referência histórica** e documentação.
- **NÃO** devem ser executados em CI/CD
- **NÃO** fazem parte da suíte de regressão
- **NÃO** refletem a arquitetura atual do projeto

## Estrutura

```
tests/archived/
├── passwords/          # Testes antigos do módulo Senhas (pré-refactor v1.3.47)
├── clientes/           # Testes antigos do módulo Clientes
└── README.md           # Este arquivo
```

## Quando consultar estes arquivos?

- Arqueologia de código: entender decisões de design antigas
- Referência histórica: verificar como funcionalidades eram testadas antes
- Migração de cenários: identificar casos de teste não portados

## Testes Oficiais (Atuais)

Para testes válidos e atualizados, consulte:

### Módulo Senhas
- `tests/modules/passwords/` - Testes de integração
- `tests/unit/modules/passwords/test_passwords_controller.py` - Controller atual
- `tests/unit/modules/passwords/test_passwords_service_errors.py` - Service

### Módulo Clientes  
- `tests/modules/clientes/` - Testes de integração
- `tests/unit/modules/clientes/` - Testes unitários atuais

### Hub (substitui funcionalidade de Obrigações do Clientes)
- `tests/unit/modules/hub/views/test_dashboard_center.py`

## Configuração pytest

O arquivo `pytest.ini` está configurado para **ignorar** este diretório:

```ini
norecursedirs = .venv venv build dist .git __pycache__ tests/archived
```

Executar `pytest tests` ou `pytest tests --cov` **NÃO** incluirá estes arquivos.

---

**Data de arquivamento**: 7 de dezembro de 2025  
**FASE 6**: Revisão de arquivos LEGACY (qa/fixpack-04)
