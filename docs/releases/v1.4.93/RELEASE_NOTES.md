# RC-Gestor de Clientes - Release Notes v1.4.93

**Data de Lançamento:** 26 de dezembro de 2025

## 📋 Resumo

Atualização de versão 1.4.79 → 1.4.93 com foco em **segurança**, incluindo correção de vulnerabilidades críticas (P0), migração para armazenamento seguro de credenciais (P1) e documentação completa do modelo de segurança.

## 🔐 Segurança (Prioridade)

### Correções Críticas (P0)

#### P0-001: OpenAI Key Exposta
- ✅ Removida recomendação de arquivo `config/openai_key.txt`
- ✅ Configuração via `OPENAI_API_KEY` agora é **obrigatória**
- ✅ Documentação atualizada com avisos de segurança
- ✅ `.gitignore` já protegia o arquivo (confirmado)

#### P0-002: PyInstaller Inclui .env no Build
- ✅ Removida linha `add_file(BASE / ".env", ".")` do `rcgestor.spec`
- ✅ Build não distribui mais credenciais (`RC_CLIENT_SECRET_KEY`, `SUPABASE_KEY`, etc.)
- ✅ Comentário de segurança adicionado ao spec file
- ✅ Documentação clara sobre uso de variáveis de ambiente em produção

### Melhorias de Segurança (P1)

#### P1-001: Migração para Keyring (DPAPI)
- ✅ Tokens Supabase agora armazenados via **Windows Credential Manager**
- ✅ Migração automática de `auth_session.json` para keyring
- ✅ Dependência `keyring>=25.0.0` adicionada
- ✅ Novos helpers em `src/utils/prefs.py`:
  - `_keyring_get_session_json()`
  - `_keyring_set_session_json()`
  - `_keyring_clear_session()`
- ✅ PyInstaller: hiddenimports para `keyring.backends.Windows`
- ✅ Compatibilidade com testes (desabilita keyring em pytest)

**Benefícios:**
| Antes | Depois |
|-------|--------|
| ❌ Tokens em JSON texto plano | ✅ Tokens criptografados via DPAPI |
| ❌ Qualquer processo pode ler | ✅ Protegido pelo Windows Credential Manager |
| ❌ Fácil exfiltração | ✅ Requer credenciais do usuário Windows |

#### P1-002: Modelo de Segurança para Chave Fernet
- ✅ Criado documento técnico `docs/SECURITY_MODEL.md`
- ✅ Dois modelos de gestão de chave documentados:
  - **Modelo 1 (Padrão):** Chave única por instalação via keyring
  - **Modelo 2 (Avançado):** Chave gerenciada via variável de ambiente
- ✅ Integração com keyring no `security/crypto.py`
- ✅ Ordem de precedência implementada:
  1. Variável de ambiente `RC_CLIENT_SECRET_KEY`
  2. Keyring (Windows Credential Manager)
  3. Geração automática e armazenamento no keyring
- ✅ Trade-offs documentados:
  - Segurança vs Portabilidade
  - Perda de acesso vs Comprometimento
  - Recuperação de dados

## 📝 Documentação

### Novos Documentos
- **`docs/SECURITY_MODEL.md`**: Documentação completa do modelo de segurança
  - Conceitos de criptografia simétrica (Fernet)
  - Análise de riscos e trade-offs
  - Recomendações e anti-padrões
  - Cenários de perda e comprometimento

### Documentos Atualizados
- **`config/README.md`**: Práticas de segurança para configuração OpenAI
- **`README.md`**: Avisos de segurança e configuração de produção
- **`rcgestor.spec`**: Comentários sobre segurança no build

### Relatórios de Auditoria
Documentação completa em `reports/_qa_codex_tests_smoke_001/`:
- `P0_FIXES_COMPLETED.md` - Correções críticas
- `P1-001_IMPLEMENTED.md` - Migração para keyring
- `P1-002_IMPLEMENTED.md` - Modelo de segurança Fernet

## 🔧 Mudanças Técnicas

### Atualizações de Versão
- ✅ `src/version.py`: `__version__ = "1.4.93"`
- ✅ `version_file.txt`: FileVersion e ProductVersion atualizados
- ✅ `installer/rcgestor.iss`: AppVersion atualizado
- ✅ `README.md`: Badge e referências atualizados
- ✅ Link BUILD.md corrigido: `docs/reports/BUILD.md`

### Dependências
```diff
+ keyring>=25.0.0           # Armazenamento seguro de credenciais (DPAPI no Windows)
```

## 📦 Instalação

1. Download: `RC-Gestor-Clientes-1.4.93.exe`
2. Execute o instalador
3. Siga as instruções na tela

## ⚠️ Notas Importantes

### Para Usuários Existentes
- ✅ **Migração Automática:** Tokens serão migrados automaticamente para keyring no primeiro login
- ✅ **Sem Ação Necessária:** Arquivo `auth_session.json` será removido após migração
- ⚠️ **Backup Recomendado:** Faça backup antes da atualização (precaução padrão)

### Para Novos Usuários
- ✅ Credenciais armazenadas de forma segura por padrão
- ✅ Configuração via variáveis de ambiente (`.env` em dev, variáveis do SO em produção)
- ⚠️ **Não distribua o `.env`** - Contém credenciais sensíveis

### Requisitos
- Windows 10 ou superior (64-bit)
- Credenciais válidas do Supabase
- Conexão com internet

## 📚 Documentação Adicional

- [CHANGELOG.md](../../../CHANGELOG.md) - Histórico completo de mudanças
- [SECURITY_MODEL.md](../../SECURITY_MODEL.md) - Modelo de segurança detalhado
- [README.md](../../../README.md) - Documentação geral do projeto

---

**Versão:** 1.4.93  
**Build:** 26 de dezembro de 2025  
**Plataforma:** Windows (x64)  
**Foco:** Segurança e Conformidade
