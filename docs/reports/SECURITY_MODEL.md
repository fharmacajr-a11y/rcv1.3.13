# 🔐 Modelo de Segurança - RC Gestor de Clientes

**Versão:** 1.0  
**Data:** 26 de dezembro de 2025  
**Escopo:** Criptografia de senhas e gestão de chaves

---

## 📋 Visão Geral

Este documento descreve o modelo de segurança para criptografia de senhas de clientes no RC Gestor. O sistema utiliza **Fernet (criptografia simétrica)** para proteger credenciais armazenadas localmente.

---

## 🔑 Criptografia Fernet - Conceitos Básicos

### O que é Fernet?

- **Algoritmo:** AES-128 em modo CBC com autenticação HMAC
- **Tipo:** Criptografia simétrica (mesma chave para criptografar e descriptografar)
- **Biblioteca:** `cryptography` (padrão da indústria, auditada)
- **Formato da chave:** Base64 de 44 caracteres (32 bytes de entropia)

### Princípio Fundamental

⚠️ **CRÍTICO:** Quem possui a chave Fernet consegue descriptografar todos os dados protegidos por ela.

```
Chave Fernet → Criptografa senha → Token criptografado
Token criptografado + Chave Fernet → Descriptografa → Senha original
```

---

## 🏗️ Modelo de Armazenamento de Chaves

O RC Gestor oferece **dois modelos** de gestão da chave Fernet:

### Modelo 1: Chave Única por Instalação (Padrão Recomendado)

**Como funciona:**

1. Na primeira execução, o sistema gera uma chave Fernet única
2. A chave é armazenada no **Windows Credential Manager** (via DPAPI)
3. Cada máquina/usuário tem sua própria chave
4. A chave **NÃO é distribuída** com o executável ou backups

**Vantagens:**

✅ Chave nunca exposta em arquivos de configuração  
✅ Protegida pelo Windows DPAPI (criptografia por usuário)  
✅ Não há risco de vazamento em repositórios Git ou backups  
✅ Isolamento entre instalações/usuários

**Desvantagens:**

❌ **Perda da chave = perda permanente dos dados criptografados**  
❌ Senhas não são portáveis entre máquinas  
❌ Reset do Windows ou mudança de usuário perde acesso  
❌ Não há backup automático da chave

**Quando usar:**

- ✅ Instalação em máquina única e permanente
- ✅ Usuário não precisa migrar dados entre computadores
- ✅ Segurança é prioridade máxima

### Modelo 2: Chave Gerenciada pelo Usuário (Variável de Ambiente)

**Como funciona:**

1. Usuário define `RC_CLIENT_SECRET_KEY` como variável de ambiente
2. Sistema usa essa chave ao invés de gerar/buscar no keyring
3. Usuário é responsável por backup e segurança da chave

**Vantagens:**

✅ Portabilidade: mesma chave em múltiplas máquinas  
✅ Backup controlado pelo usuário  
✅ Senhas acessíveis após reinstalação (se chave for preservada)

**Desvantagens:**

❌ Chave pode ser exposta em arquivos `.env` ou scripts  
❌ Risco de commit acidental em repositórios  
❌ Usuário assume responsabilidade pela segurança  
❌ Se chave vazar, todas as senhas estão comprometidas

**Quando usar:**

- ✅ Múltiplas instalações que precisam compartilhar senhas
- ✅ Ambiente corporativo com gestão centralizada de chaves
- ✅ Usuário tem expertise em segurança e backup

**Como configurar:**

```bash
# Gerar chave Fernet
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Definir variável de ambiente (Windows PowerShell)
$env:RC_CLIENT_SECRET_KEY = "chave-gerada-acima"

# Ou adicionar ao .env (NUNCA commitar este arquivo)
echo "RC_CLIENT_SECRET_KEY=chave-gerada-acima" >> .env
```

---

## ⚠️ Análise de Riscos e Trade-offs

### Cenário 1: Perda de Acesso à Chave

| Causa | Modelo 1 (Keyring) | Modelo 2 (Env Var) |
|-------|-------------------|-------------------|
| Reset do Windows | ❌ Perda total | ✅ OK (se chave em backup) |
| Mudança de usuário Windows | ❌ Perda total | ✅ OK (se chave em backup) |
| Reinstalação do sistema | ❌ Perda total | ✅ OK (se chave em backup) |
| Migração para novo PC | ❌ Perda total | ✅ OK (se chave transportada) |

### Cenário 2: Comprometimento da Chave

| Ameaça | Modelo 1 (Keyring) | Modelo 2 (Env Var) |
|--------|-------------------|-------------------|
| Malware com privilégios do usuário | ⚠️ Vulnerável | ⚠️ Vulnerável |
| Acesso físico ao PC (logado) | ⚠️ Vulnerável | ⚠️ Vulnerável |
| Backup não criptografado | ✅ Chave não incluída | ❌ Chave pode estar no backup |
| Commit acidental no Git | ✅ Chave nunca em arquivo | ❌ Risco alto se .env commitado |
| Compartilhamento de executável | ✅ Chave não incluída | ❌ Se .env empacotado (P0-002) |

---

## 🛡️ Recomendações de Segurança

### Para Instalações Individuais (Recomendado)

1. ✅ **Use o Modelo 1 (keyring)** - padrão do sistema
2. ✅ **NÃO defina** `RC_CLIENT_SECRET_KEY` no ambiente
3. ✅ Entenda que perda do acesso Windows = perda das senhas
4. ✅ Mantenha backup das senhas em formato texto seguro (ex: KeePass) como contingência

### Para Instalações Corporativas/Multi-máquina

1. ✅ Gere uma chave Fernet forte e armazene em cofre corporativo (ex: Azure Key Vault, HashiCorp Vault)
2. ✅ Distribua via variável de ambiente do sistema (não arquivo)
3. ✅ Implemente rotação periódica de chaves (requer re-criptografia)
4. ✅ Monitore acesso e uso da chave

### Práticas Proibidas (❌)

- ❌ **NUNCA** commite `RC_CLIENT_SECRET_KEY` no Git
- ❌ **NUNCA** compartilhe a chave por email/chat
- ❌ **NUNCA** empacote `.env` com chave no executável distribuído (corrigido em P0-002)
- ❌ **NUNCA** use a mesma chave para múltiplos clientes/organizações sem motivo

---

## 🔄 Ordem de Precedência (Implementação Técnica)

O sistema busca a chave nesta ordem:

1. **Variável de ambiente `RC_CLIENT_SECRET_KEY`** (prioridade máxima)
   - Se definida: usa essa chave
   - Valida formato (base64, 44 caracteres)
   - **NÃO salva no keyring** (respeita escolha do usuário)

2. **Keyring do sistema** (Windows Credential Manager)
   - Service: `RC-Gestor-Clientes`
   - Username: `rc_client_secret_key`
   - Se encontrar: usa essa chave
   - Se não encontrar: gera nova chave e salva no keyring

3. **Fallback em caso de erro**
   - Se keyring indisponível: levanta `RuntimeError` com instrução para definir variável de ambiente

---

## 📊 Comparativo de Modelos

| Aspecto | Modelo 1 (Keyring) | Modelo 2 (Env Var) |
|---------|-------------------|-------------------|
| **Segurança padrão** | ⭐⭐⭐⭐⭐ Alta | ⭐⭐⭐ Média |
| **Portabilidade** | ⭐ Baixa | ⭐⭐⭐⭐⭐ Alta |
| **Facilidade de uso** | ⭐⭐⭐⭐⭐ Simples | ⭐⭐⭐ Requer config |
| **Risco de vazamento** | ⭐⭐⭐⭐⭐ Baixo | ⭐⭐ Alto (se mal gerido) |
| **Recuperação de desastre** | ⭐ Impossível | ⭐⭐⭐⭐⭐ Total (se backup) |
| **Complexidade para usuário** | ⭐⭐⭐⭐⭐ Zero | ⭐⭐ Média |

---

## 🚨 Cenários de Perda de Dados

### Situações onde senhas criptografadas se tornam irrecuperáveis:

1. **Modelo 1 (Keyring):**
   - Reset do Windows (formatação, reinstalação)
   - Mudança de conta de usuário Windows
   - Corrupção do Windows Credential Manager
   - Migração para novo PC (sem exportar keyring)

2. **Modelo 2 (Env Var):**
   - Perda do arquivo com a chave
   - Chave sobrescrita/deletada sem backup
   - Backup corrompido

### Mitigação:

✅ **Estratégia recomendada:** Manter **backup secundário** das senhas em gerenciador de senhas dedicado (KeePass, Bitwarden, 1Password)

⚠️ **Não confie APENAS na criptografia local** para dados críticos sem backup alternativo

---

## 📚 Referências Técnicas

- [Fernet Specification](https://github.com/fernet/spec/blob/master/Spec.md)
- [Cryptography Library Documentation](https://cryptography.io/en/latest/fernet/)
- [Windows DPAPI](https://docs.microsoft.com/en-us/windows/win32/api/dpapi/)
- [OWASP Key Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html)

---

## 🔄 Histórico de Mudanças

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0 | 2025-12-26 | Criação inicial do documento (P1-002) |

---

*Este documento é parte do sistema de segurança do RC Gestor de Clientes e deve ser revisado a cada mudança no modelo de criptografia.*
