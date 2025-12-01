# Analise do Escopo de Coverage (pytest-cov) - RC Gestor

## Configuracao atual
- Arquivos revisados: `pytest.ini` (addopts=-q; pythonpath inclui src, infra, adapters), `pyproject.toml` (sem configuracao de pytest-cov), nenhum `.coveragerc`, `tox.ini` ou `setup.cfg` presente.
- Cobertura e disparada pelo comando de referencia:
  ```bash
  python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q
  ```
- O `--cov=src` mede somente o codigo em `src/` (app principal). Tests/ e pastas fora de `src/` ficam fora da metrica, por isso o ~37% historico reflete apenas o codigo de aplicacao.

## Estrutura de pastas de codigo
| Pasta            | Codigo Python? | Exemplo(s)                                 | Observacao                                      |
| ---------------- | -------------- | ------------------------------------------ | ----------------------------------------------- |
| src/             | Sim            | `src/app_status.py`                        | Ja incluida no escopo atual (`--cov=src`).      |
| tests/           | Sim (testes)   | `tests/test_app_status_fase26.py`          | Nao deve contar na cobertura de produto.        |
| adapters/        | Sim            | `adapters/storage/supabase_storage.py`     | Adaptadores de storage; fora da cobertura hoje. |
| infra/           | Sim            | `infra/net_status.py`, `infra/settings.py` | Utilitarios/servicos de infra; fora hoje.       |
| data/            | Sim            | `data/auth_bootstrap.py`                   | Tipos/dados de dominio; fora hoje.              |
| devtools/        | Sim            | `devtools/qa/analyze_linters.py`           | Ferramentas/diagnosticos internos; fora hoje.   |
| scripts/         | Sim            | `scripts/dev_smoke.py`                     | Scripts de demo/experimentacao; fora hoje.      |
| security/        | Sim            | `security/crypto.py`                       | Utilitarios de seguranca; fora hoje.            |
| helpers/         | Sim (minimo)   | `helpers/__init__.py`                      | Placeholder/helper package; fora hoje.          |
| Arquivos avulsos | Sim            | `main.py`, `sitecustomize.py`              | Fora do escopo atual.                           |

Diretorios sem Python relevante (nao candidatos imediatos): `assets/` (midias), `docs/` (documentacao), `migrations/` (SQL), `third_party/7zip` (binarios), `typings/` (stubs).

## Opcoes de escopo de cobertura
**a) Manter como esta (so src)**  
- Indicador focado no codigo de aplicacao.  
- Evita ruido de scripts de suporte ou testes.  
- Alinhado ao layout src/ comum.

**b) Incluir outras pastas de produto**  
- Exemplo: `python -m pytest --cov=src --cov=infra --cov-report=term-missing --cov-fail-under=25 -q`.  
- Pode reduzir o percentual se houver codigo nao testado em infra/ ou similares.  
- Exige decidir se essas pastas fazem parte da meta oficial de qualidade.

**c) Centralizar o escopo em um .coveragerc (futuro, nao aplicado)**  
```ini
[run]
source =
    src
    infra

[report]
omit =
    tests/*
    .venv/*
    venv/*
```
- Facilita padronizar o escopo sem depender da linha de comando.  
- A lista de `source` e `omit` pode ser ajustada para incluir outras pastas (ex.: adapters, data, security) conforme decidido.

Nenhuma mudanca foi aplicada; este documento apenas registra o estado atual e alternativas.

## Proximos passos sugeridos
- Se decidir incluir infra (ou outras pastas) na cobertura, abrir tarefa para ajustar pytest.ini e/ou criar `.coveragerc` alinhado ao escopo escolhido.
- Se quiser relatorio visual, adicionar `--cov-report=html` ao comando ou futura config.
- Se quiser metas diferentes por tipo de codigo, considerar manter src/ separado e medir pastas auxiliares com comandos dedicados.
