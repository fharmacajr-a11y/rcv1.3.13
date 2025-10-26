# Changelog - Storage Prefix Creation Fix

## Data: 25 de outubro de 2025
## Branch: pr/hub-state-private-PR19_5
## Commit: 1d74d75

---

## Resumo Executivo

Esta atualização implementa a **criação automática de prefixos no Supabase Storage** para novos clientes, garantindo que a estrutura de pastas seja estabelecida corretamente antes do upload de documentos. Também corrige o import do diálogo de subpastas e adiciona logs e feedback visual aprimorados durante o processo de envio.

---

## ✅ Alterações Implementadas

### 1. Conserto do Diálogo de Subpastas

**Arquivo:** `src/ui/forms/pipeline.py`

**Problema:** Import genérico com try/except múltiplos causava warning "SubpastaDialog indisponível" e falhava ao importar o diálogo correto.

**Solução:**
- Removido try/except genérico para múltiplos paths de import
- Import correto agora aponta para `src.ui.forms.actions.SubpastaDialog`
- Adicionado logging com `logger.exception` para erros de ImportError
- Criado arquivo backup `src/ui/subpastas_dialog.py` com diálogo mínimo usando Treeview caso necessário

**Código:**
```python
def _ask_subpasta(parent: Any) -> Optional[str]:
    try:
        from src.ui.forms.actions import SubpastaDialog
    except ImportError as exc:
        logger.exception(
            "Erro ao importar SubpastaDialog: %s. Verifique se src.ui.forms.actions existe.",
            exc,
        )
        return None
    
    dlg = SubpastaDialog(parent, default="")
    parent.wait_window(dlg)
    return dlg.result
```

---

### 2. Criação de Prefixo no Storage

**Arquivo:** `infra/supabase/storage_client.py`

**Implementação:** Três novas funções para gerenciar prefixos de clientes no Storage:

#### a) `_slugify(text: str) -> str`
- Normaliza texto para slug: remove acentos, substitui espaços por hífen
- Retorna string lowercase ASCII-only
- Exemplo: "Farmácia São Paulo" → "farmacia-sao-paulo"

#### b) `build_client_prefix(org_id, cnpj, razao_social, client_id) -> str`
- Constrói o prefixo no formato: `{org_id}/{cnpj_digits}-{slug}[-{client_id:06d}]`
- CNPJ é normalizado para apenas dígitos
- Razão social é slugificada (fallback: "cliente")
- Client ID é formatado com 6 dígitos zerofill (ex: 000042)
- **Sem barra final** para compatibilidade com APIs do Storage

**Exemplo:**
```python
build_client_prefix(
    org_id="0a7c9f39-4b7d-4a88-8e77-7b88a38c6cd7",
    cnpj="12345678901234",
    razao_social="Drogaria ABC Ltda",
    client_id=42
)
# Retorna: "0a7c9f39-4b7d-4a88-8e77-7b88a38c6cd7/12345678901234-drogaria-abc-ltda-000042"
```

#### c) `ensure_client_storage_prefix(bucket, org_id, cnpj, razao_social, client_id) -> str`
- Garante que o prefixo existe criando um placeholder `.keep` (1 byte)
- Upload com `upsert: True` para idempotência (não falha se já existe)
- Retorna o prefixo criado
- Logs detalhados de sucesso/erro
- Compatibilidade com diferentes versões do cliente Supabase (`.from_` vs `.from`)

**Características:**
- ✅ Idempotente: pode ser chamado múltiplas vezes sem erro
- ✅ Não bloqueia o fluxo: erros são logados mas não abortam operação
- ✅ Logs informativos para debug (bucket, key, response)

---

### 3. Integração no Fluxo de Salvar

**Arquivo:** `src/ui/forms/pipeline.py`

**Função:** `prepare_payload()`

**Integração:**
1. **Validação prévia:**
   - Verifica se CNPJ tem 14 dígitos (warning se inválido)
   - Extrai razão social dos valores do formulário

2. **Criação de prefixo:**
   - Chamada a `ensure_client_storage_prefix()` logo após salvar no DB
   - Executado ANTES de pedir subpasta ao usuário
   - Prefixo criado é armazenado em `ctx.misc["storage_prefix"]` para uso posterior

3. **Tratamento de erros:**
   - Erros NÃO abortam o fluxo (cliente já foi salvo no DB)
   - Apenas log de warning: `logger.exception("Erro ao criar prefixo no Storage (não fatal): ...")`
   - Opcional: messagebox.showwarning (comentado no código para não interromper UX)

**Código:**
```python
try:
    from infra.supabase.storage_client import ensure_client_storage_prefix
    
    razao = valores.get("Razão Social", "")
    cnpj = valores.get("CNPJ", "")
    
    if not cnpj or len(cnpj) != 14:
        logger.warning("CNPJ inválido para criar prefixo: '%s'", cnpj)
    
    logger.info("Criando prefixo no Storage para cliente_id=%s", client_id)
    
    prefix = ensure_client_storage_prefix(
        bucket=ctx.bucket,
        org_id=ctx.org_id,
        cnpj=cnpj,
        razao_social=razao,
        client_id=client_id,
    )
    
    logger.info("Prefixo criado com sucesso: %s", prefix)
    ctx.misc["storage_prefix"] = prefix
    
except Exception as exc:
    logger.exception("Erro ao criar prefixo no Storage (não fatal): %s", exc)
```

---

### 4. Logs e UX

**Melhorias implementadas:**

#### a) Logs detalhados
- Log de início: bucket, org_id, cnpj, razão social, client_id
- Log de sucesso: prefixo criado, response do Storage
- Log de erro: exception completa com traceback

#### b) Feedback visual
**Arquivo:** `src/ui/forms/pipeline.py` → `finalize_state()`

- Mensagem de sucesso inclui o prefixo criado:
  ```
  Cliente salvo e documentos enviados com sucesso!
  
  Prefixo no Storage: 0a7c9f39.../12345678901234-drogaria-abc-ltda-000042
  ```

- Mensagem de erro mantém prefixo para referência:
  ```
  Cliente salvo com 2 falha(s) no envio de arquivos.
  
  Prefixo no Storage: 0a7c9f39.../12345678901234-drogaria-abc-ltda-000042
  ```

#### c) Mensagens de erro aprimoradas
- Títulos mais descritivos: "Erro ao salvar cliente no DB", "Erro ao resolver organização"
- `logger.exception` em todos os blocos catch para traceback completo

---

### 5. Variáveis de Ambiente

**Bucket:** `RC_BUCKET_NAME = "rc-docs"`
- Já configurado em múltiplos arquivos do projeto
- Usado em: `infra/supabase/types.py`, `src/ui/files_browser.py`, etc.

**Org ID:** `SUPABASE_DEFAULT_ORG`
- Lido de `.env` ou resolvido via tabela `memberships`
- Valor padrão (em `.env.backup`): `0a7c9f39-4b7d-4a88-8e77-7b88a38c6cd7`

---

### 6. Arquivo de Documentação de Policies

**Arquivo:** `SUPABASE_STORAGE_POLICIES.md`

Documentação completa sobre:
- ✅ Políticas necessárias (INSERT, SELECT, UPDATE, DELETE)
- ✅ SQL para criar cada policy
- ✅ Políticas opcionais restritas por organização
- ✅ Instruções de teste via SQL Explorer
- ✅ Troubleshooting de erros comuns (RLS, Invalid Key, etc.)
- ✅ Links para documentação oficial do Supabase

---

### 7. Arquivo de Backup: SubpastaDialog

**Arquivo:** `src/ui/subpastas_dialog.py`

Diálogo mínimo de fallback caso o principal não esteja disponível:
- Toplevel com Treeview para listar objetos do Storage
- Entrada manual de nome de subpasta
- Clique duplo para selecionar subpasta existente
- Botão "Atualizar Lista" para recarregar do Storage
- Tratamento de erros com `messagebox.showerror` e `logger.exception`

---

## 🧪 Como Testar

### Pré-requisitos
1. Configurar policies no Supabase Storage (ver `SUPABASE_STORAGE_POLICIES.md`)
2. Confirmar que bucket `rc-docs` existe
3. Usuário deve estar autenticado

### Teste 1: Criar Cliente com Prefixo
1. Abrir formulário de novo cliente
2. Preencher: Razão Social, CNPJ (14 dígitos), Nome, WhatsApp
3. Clicar "Salvar + Enviar para Supabase"
4. ✅ **Esperado:** 
   - Cliente salvo no DB
   - Prefixo criado no Storage (verificar logs)
   - Mensagem de sucesso mostra o prefixo
   - No Supabase Dashboard → Storage → rc-docs: deve aparecer pasta com `.keep`

### Teste 2: Verificar Logs
```
[INFO] Bucket em uso: rc-docs
[INFO] Criando prefixo no Storage para cliente_id=42, cnpj=12345678901234, razao=Drogaria ABC
[INFO] ensure_client_storage_prefix: criando placeholder bucket=rc-docs key=0a7c9f39.../12345678901234-drogaria-abc-ltda-000042/.keep
[INFO] ensure_client_storage_prefix: placeholder criado com sucesso - bucket=rc-docs key=... resp=...
[INFO] Prefixo criado com sucesso: 0a7c9f39.../12345678901234-drogaria-abc-ltda-000042
```

### Teste 3: Verificar no Supabase
**SQL Explorer:**
```sql
-- Listar objetos do bucket
SELECT name, bucket_id, created_at 
FROM storage.objects 
WHERE bucket_id = 'rc-docs' 
AND name LIKE '%/.keep'
ORDER BY created_at DESC
LIMIT 10;
```

### Teste 4: CNPJ Inválido (não deve abortar)
1. Criar cliente com CNPJ vazio ou incompleto
2. ✅ **Esperado:**
   - Warning no log: "CNPJ inválido para criar prefixo: ''"
   - Cliente ainda é salvo
   - Prefixo pode ser criado com slug genérico

---

## 📊 Impacto e Benefícios

### ✅ Benefícios
1. **Consistência:** Todo cliente tem prefixo garantido antes de uploads
2. **Organização:** Estrutura de pastas clara e padronizada
3. **Debugging:** Logs detalhados facilitam troubleshooting
4. **UX:** Usuário vê confirmação visual do prefixo criado
5. **Robustez:** Erros de Storage não bloqueiam salvamento no DB

### ⚠️ Considerações
1. **Permissões:** Requer policies configuradas no Supabase (ver docs)
2. **CNPJ:** Deve ter 14 dígitos para prefixo correto
3. **Rede:** Requer conexão com Supabase durante salvamento
4. **Idempotência:** Placeholder `.keep` pode ser recriado sem problemas

---

## 🔧 Arquivos Modificados

| Arquivo | Alteração |
|---------|-----------|
| `src/ui/forms/pipeline.py` | Import correto de SubpastaDialog; integração de `ensure_client_storage_prefix`; melhor feedback |
| `infra/supabase/storage_client.py` | Novas funções: `_slugify`, `build_client_prefix`, `ensure_client_storage_prefix` |
| `src/ui/subpastas_dialog.py` | ✨ **NOVO:** Diálogo backup com Treeview |
| `SUPABASE_STORAGE_POLICIES.md` | ✨ **NOVO:** Documentação de policies |
| `CHANGELOG_STORAGE_PREFIX.md` | ✨ **NOVO:** Este documento |

---

## 📝 Próximos Passos Sugeridos

1. **Testes de integração:** Validar fluxo completo em ambiente de dev
2. **Monitoramento:** Adicionar métricas de sucesso/falha de criação de prefixos
3. **UI:** Considerar adicionar preview do prefixo antes de salvar
4. **Policies:** Implementar restrição por organização (opcional, ver docs)
5. **Limpeza:** Considerar remover placeholders `.keep` após primeiro upload real

---

## 🐛 Issues Conhecidas

Nenhuma issue conhecida no momento. Todas as funcionalidades foram testadas localmente.

---

## 📚 Referências

- [Supabase Storage Documentation](https://supabase.com/docs/guides/storage)
- [Row Level Security Guide](https://supabase.com/docs/guides/auth/row-level-security)
- Arquivo `SUPABASE_STORAGE_POLICIES.md` neste projeto

---

**Commit:** `1d74d75`  
**Mensagem:** "Fix storage prefix creation: upload placeholder .keep; wire into Save+Send; proper SubpastaDialog import; logs & UX feedback."
