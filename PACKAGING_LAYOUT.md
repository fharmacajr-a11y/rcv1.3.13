# Layout para empacotamento (onefile)

## Pastas runtime (entram no executável)
- src/ -> código principal (UI, módulos e serviços)
- infra/ -> clientes Supabase, integrações e utilitários de infraestrutura
- security/ -> componentes de segurança usados em runtime
- data/ -> dados auxiliares necessários em execução
- adapters/ -> adaptadores de armazenamento/IO usados pelo app
- assets/ -> ícones/recursos estáticos referenciados (ex.: `rc.ico`)
- third_party/ -> dependências vendorizadas (se/ quando existirem)
- runtime_docs/ (se presente) -> docs exibidas in-app, como changelog

## Pastas dev/test/doc (ficam fora do executável)
- docs/ -> documentação
- tests/ -> testes automatizados
- devtools/ (arch/, qa/, relatórios JSON/TXT) -> ferramentas e análises de QA
- migrations/ -> scripts de migração de banco
- scripts/ -> helpers de desenvolvimento/ops
- __pycache__/ , .pytest_cache , .ruff_cache -> caches
- INSTALACAO.md, CHANGELOG.md, config.yml -> texto/configuração externa, não usados em runtime

## Itens estáticos/ opcionais
- *.md (exceto runtime_docs) -> documentação apenas
- .vscode/, .github/, pyproject.toml, ruff.toml, pytest.ini -> tooling/dev, não entram no bundle
- rc.ico -> incluir para manter ícone do executável e janelas

## Notas para PyInstaller/onefile
- Incluir: src/, infra/, security/, data/, adapters/, assets/ (e runtime_docs/ se usado in-app), além de rc.ico.
- Excluir: docs/, tests/, devtools/, migrations/, scripts/, caches (__pycache__, .pytest_cache, .ruff_cache), arquivos *.md (exceto se consumidos em runtime) e diretórios de tooling (.github, .vscode).
- Verificar paths de recursos via `resource_path` para garantir que ícones/arquivos necessários sejam coletados.
