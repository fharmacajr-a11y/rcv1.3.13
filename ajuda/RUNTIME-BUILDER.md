# Runtime Builder - Documentação

## 📦 Visão Geral

O **Runtime Builder** é um sistema para criar uma versão limpa e otimizada do projeto contendo apenas os arquivos necessários para execução, sem testes, documentação, scripts de build, etc.

## 🎯 Objetivo

Facilitar a distribuição e teste do aplicativo sem carregar arquivos desnecessários, mantendo o projeto original intacto.

## 📁 Arquivos Criados

### 1. `config/runtime_manifest.yaml`

Manifesto que define o que entra e o que fica fora do runtime.

**Estrutura:**
- `include`: Lista de globs indicando o que deve ser incluído
- `exclude`: Lista de globs indicando o que deve ser excluído
- `whitelist_scripts`: Scripts que não devem ser copiados para o runtime

**Principais inclusões:**
- Arquivos principais (`app_*.py`)
- Módulos essenciais (`application/`, `gui/`, `ui/`, `core/`, `infra/`)
- Utilitários (`utils/`, `adapters/`, `shared/`)
- Assets e configurações (`assets/`, `config/`)
- Detectores e infraestrutura (`detectors/`, `infrastructure/`)

**Principais exclusões:**
- Documentação (`ajuda/`, `docs/`)
- Testes (`tests/`)
- Scripts (`scripts/` exceto whitelist)
- Build artifacts (`build/`, `dist/`, `__pycache__/`)
- Arquivos sensíveis (`.env`)
- Arquivos de configuração de desenvolvimento

### 2. `scripts/make_runtime.py`

Script Python que lê o manifesto e monta a pasta `runtime/`.

**Funcionalidades:**
- ✅ **Dry-run por padrão**: mostra o que seria copiado sem fazer alterações
- ✅ **Aplicação com `--apply`**: copia os arquivos de verdade
- ✅ **Suporte a globs**: usa fnmatch para patterns flexíveis
- ✅ **Estatísticas**: mostra quantidade e tamanho dos arquivos
- ✅ **Geração de README**: cria documentação automática no runtime
- ✅ **Preserva timestamps**: usa `shutil.copy2` para manter metadados

**Uso:**

```powershell
# Ver o que seria copiado (dry-run)
python scripts/make_runtime.py

# Aplicar a cópia
python scripts/make_runtime.py --apply
```

## 📊 Resultado da Execução

### Estatísticas (v1.0.33)

- **95 arquivos** copiados
- **420.3 KB** de código Python e assets
- **Estrutura limpa** sem testes, docs ou build artifacts

### Estrutura do Runtime

```
runtime/
├── README-RUNTIME.txt          # Documentação gerada automaticamente
├── app_gui.py                  # Entry point principal
├── app_core.py                 # Core do aplicativo
├── app_status.py               # Monitor de status
├── app_utils.py                # Utilitários principais
├── adapters/                   # Adaptadores (storage, etc.)
├── application/                # Camada de aplicação
├── assets/                     # Ícones e recursos visuais
├── config/                     # Configurações não sensíveis
├── core/                       # Domínio e lógica de negócio
├── detectors/                  # Detectores (CNPJ, etc.)
├── gui/                        # Interfaces gráficas
├── infra/                      # Infraestrutura (Supabase, healthcheck)
├── infrastructure/             # Scripts de infraestrutura
├── shared/                     # Código compartilhado
├── ui/                         # Componentes de UI
└── utils/                      # Utilitários gerais
```

## 🔒 Regras de Segurança

### ✅ O que o script FAZ

- Copia apenas arquivos listados no manifesto
- Preserva a estrutura de diretórios
- Mantém timestamps originais
- Gera documentação automática

### ❌ O que o script NÃO FAZ

- **Não apaga** nada do projeto original
- **Não altera** código de produção
- **Não move** o arquivo `.env`
- **Não toca** no arquivo `.spec`
- **Não modifica** arquivos existentes

## 🧪 Testando o Runtime

Depois de gerar o runtime, você pode testá-lo:

```powershell
# Navegue até a pasta runtime
cd runtime

# Execute o aplicativo
python app_gui.py
```

⚠️ **IMPORTANTE**: Configure o arquivo `.env` na **raiz do projeto** antes de executar. O runtime usa as configurações do projeto principal.

## 🔧 Manutenção

### Adicionar novos arquivos ao runtime

Edite `config/runtime_manifest.yaml` e adicione o pattern na seção `include`:

```yaml
include:
  - novo_modulo/**
  - arquivo_especial.py
```

### Excluir arquivos do runtime

Adicione o pattern na seção `exclude`:

```yaml
exclude:
  - modulo_temporario/**
  - "**/*.backup"
```

### Regenerar o runtime

Basta executar novamente:

```powershell
python scripts/make_runtime.py --apply
```

## 📈 Comparação com o Projeto Completo

| Métrica | Projeto Completo | Runtime |
|---------|------------------|---------|
| Diretórios | 42 | ~17 |
| Arquivos | 175 | 95 |
| Tamanho (código) | ~14K LOC | ~420 KB |
| Inclui testes | ✅ | ❌ |
| Inclui docs | ✅ | ❌ |
| Inclui build | ✅ | ❌ |

## 🎓 Referências

- **Manifesto YAML**: Formato padrão para configuração ([YAML.org](https://yaml.org/))
- **fnmatch**: Pattern matching Python ([Docs](https://docs.python.org/3/library/fnmatch.html))
- **shutil.copy2**: Cópia preservando metadados ([Docs](https://docs.python.org/3/library/shutil.html#shutil.copy2))

## 💡 Próximos Passos

1. **Validar imports**: Verificar se todos os imports necessários estão incluídos
2. **Testar isoladamente**: Executar o runtime em um ambiente limpo
3. **Smoke test completo**: Testar todas as funcionalidades principais
4. **Documentar dependências**: Garantir que `requirements.txt` está correto

---

**Gerado em**: 18 de outubro de 2025  
**Versão do projeto**: v1.0.33  
**Branch**: integrate/v1.0.29
