# CHANGELOG - Robustez de Rede e Diagnóstico

## Data: 18 de outubro de 2025

### 🎯 Objetivo
Adicionar diagnóstico Supabase, reforçar chamadas de rede com retry e auto-refresh, tratar offline/401 sem travar UI, e fazer faxina segura de código legado.

---

## ✨ Novidades

### 1. **Diagnóstico Supabase (Auth + Storage)**
- **Arquivo novo:** `infra/healthcheck.py`
- **Função:** `healthcheck(bucket)` - Verifica sessão e acesso ao Storage
- **Retorna:** Dict com status detalhado de cada componente
- **Uso:** Menu "Ajuda → Diagnóstico…"

### 2. **Retry Automático com Auto-Refresh**
- **Arquivo novo:** `utils/net_retry.py`
- **Função:** `run_cloud_op(op, retries, base_delay)` - Executa operação com retry + backoff
- **Features:**
  - Tenta renovar sessão entre tentativas
  - Backoff exponencial (0.5s, 1s, 2s...)
  - Levanta última exceção se falhar

### 3. **Menu de Diagnóstico**
- **Menu:** Ajuda → Diagnóstico…
- **Mostra:**
  - Status da sessão (OK/Falhou)
  - Status do Storage com contagem de itens
  - Mensagens de erro detalhadas

### 4. **Login Robusto**
- Valida acesso ao Storage após autenticação
- Mensagens de erro específicas (rede vs credenciais)
- Não trava UI durante login
- Overlay animado "Conectando..."

### 5. **Script de Limpeza Segura**
- **Arquivo novo:** `scripts/cleanup.py`
- Remove código legado APENAS após verificar referências
- Modo dry-run primeiro
- Confirmação antes de remover

---

## 🔧 Alterações Técnicas

### Arquivos Criados (5 novos)

1. **`infra/healthcheck.py`**
   ```python
   - healthcheck(bucket="rc-docs") -> Dict[str, Any]
   - DEFAULT_BUCKET = "rc-docs"
   ```

2. **`utils/net_retry.py`**
   ```python
   - run_cloud_op(op, retries=2, base_delay=0.5) -> T
   - Retry com backoff exponencial
   - Auto-refresh de sessão
   ```

3. **`scripts/cleanup.py`**
   - Verificação segura de referências
   - Remoção de core/auth/, infrastructure/, rc.ico duplicado
   - Modo dry-run + confirmação

4. **`scripts/test_robustness.py`**
   - Teste de healthcheck
   - Teste de net_retry
   - Validação de melhorias no login
   - Verificação de menu diagnóstico

5. **`docs/PROMPT-4-CHANGES.md`** (este arquivo)

### Arquivos Modificados (3)

#### `ui/login/login.py`
- ✅ Valida Storage após login bem-sucedido
- ✅ Mensagens de erro mais específicas (rede vs conexão)
- ✅ Tratamento de timeout/network errors

#### `gui/menu_bar.py`
- ✅ Parâmetro `on_diagnostico` adicionado
- ✅ Menu "Diagnóstico…" no menu Ajuda
- ✅ Separador antes de "Sobre"

#### `gui/main_window.py`
- ✅ Método `_on_diagnostico()` implementado
- ✅ Executa healthcheck e mostra resultados
- ✅ Mensagens de sucesso/erro formatadas

---

## ✅ Testes Realizados

### Validação Automática
```bash
python scripts/test_robustness.py
```

**Resultados:**
```
✅ PASSOU - Healthcheck
✅ PASSOU - Net retry
✅ PASSOU - SessionGuard
✅ PASSOU - Melhorias no login
✅ PASSOU - Menu Diagnóstico
✅ PASSOU - Limpeza do código
```

### Checklist de Funcionalidades
- ✅ Healthcheck funciona (Auth + Storage)
- ✅ run_cloud_op com retry funcional
- ✅ SessionGuard renova sessão
- ✅ Login valida Storage após auth
- ✅ Menu Diagnóstico configurado
- ✅ Mensagens de erro específicas
- ✅ Script de limpeza segura

---

## 🛡️ Recursos de Robustez

### Tratamento de Erros

| Situação | Antes | Depois |
|----------|-------|--------|
| Sem internet | Erro genérico | ✅ "Erro de conexão. Verifique sua internet." |
| Credenciais inválidas | Trava UI | ✅ Mensagem clara + UI responsiva |
| Sessão expirada | Falha silenciosa | ✅ Auto-refresh + retry |
| Storage inacessível | Sem diagnóstico | ✅ Menu mostra status detalhado |

### Retry com Backoff

```python
from utils.net_retry import run_cloud_op
from infra.supabase_client import get_supabase

sb = get_supabase()
# Tenta até 3x (0 + 2 retries) com backoff 0.5s, 1s
result = run_cloud_op(lambda: sb.storage.from_("bucket").list())
```

### Diagnóstico Rápido

```python
from infra.healthcheck import healthcheck

result = healthcheck("rc-docs")
# {
#   "ok": True,
#   "items": {
#     "session": {"ok": True},
#     "storage": {"ok": True, "count": 42}
#   },
#   "bucket": "rc-docs"
# }
```

---

## 📂 Estrutura Criada

```
v1.0.29/
├── infra/
│   └── healthcheck.py              [NOVO] Diagnóstico Supabase
├── utils/
│   └── net_retry.py                [NOVO] Retry com auto-refresh
├── scripts/
│   ├── cleanup.py                  [NOVO] Limpeza segura
│   └── test_robustness.py          [NOVO] Testes de robustez
├── gui/
│   ├── menu_bar.py                 [MOD] Menu Diagnóstico
│   └── main_window.py              [MOD] Handler _on_diagnostico
└── ui/login/
    └── login.py                    [MOD] Validação Storage + erros
```

---

## 🚀 Como Usar

### Executar Diagnóstico

**Via Menu:**
1. Abrir app: `python app_gui.py`
2. Fazer login
3. Menu: **Ajuda → Diagnóstico…**

**Via Código:**
```python
from infra.healthcheck import healthcheck

result = healthcheck("rc-docs")
if result["ok"]:
    print("✅ Tudo OK!")
else:
    print("❌ Problemas:", result["items"])
```

### Usar Retry em Operações

```python
from utils.net_retry import run_cloud_op

# Operação simples
result = run_cloud_op(lambda: sb.storage.from_("bucket").list())

# Com mais retries
result = run_cloud_op(
    lambda: sb.table("users").select("*").execute(),
    retries=3,
    base_delay=1.0
)
```

### Limpeza Segura de Código

```bash
# Dry-run primeiro (não remove nada)
python scripts/cleanup.py

# Remove após confirmação
# O script pergunta antes de remover
```

---

## 🧹 Limpeza de Código Legado

### Itens a Remover (com verificação)

1. **`core/auth/`** - Autenticação local SQLite (substituído por Supabase Auth)
   - ⚠️ Ainda usado por `ui/users/users.py` (comentado para remoção futura)

2. **`infrastructure/`** - Pasta duplicada vazia
   - ✅ Seguro remover (sem referências ativas)

3. **`rc.ico`** (raiz) - Ícone duplicado
   - ✅ Seguro remover (mantém `assets/app.ico`)

### Executar Limpeza

```powershell
# Verificação primeiro
python scripts/cleanup.py

# Responder "s" quando perguntado
```

### Resultado Esperado

```
✅ 3 item(ns) removido(s)
   - infrastructure/
   - rc.ico (mantém assets/app.ico)
   - core/auth/ (se sem referências ativas)
```

---

## 📊 Métricas de Qualidade

| Métrica | Valor |
|---------|-------|
| Arquivos criados | **5** |
| Arquivos modificados | **3** |
| Testes passando | **100%** ✅ |
| Retry implementado | **Sim** ✅ |
| Auto-refresh sessão | **Sim** ✅ |
| Menu diagnóstico | **Sim** ✅ |
| Tratamento offline | **Sim** ✅ |
| Código legado | **Marcado** ⚠️ |

---

## 🔍 Diagnóstico - Casos de Uso

### 1. Verificar Conectividade
```
Menu → Ajuda → Diagnóstico

✅ Diagnóstico OK

- Sessão: OK
- Storage 'rc-docs': OK (itens: 15)
```

### 2. Sessão Expirada
```
❌ Problemas detectados:

- Sessão inválida/expirada
```

### 3. Storage Inacessível
```
❌ Problemas detectados:

- Storage: 404 Not Found: Bucket not found
```

---

## 🐛 Troubleshooting

### Diagnóstico falha

**Sintoma:** Menu Diagnóstico mostra erros

**Causas possíveis:**
1. Não está logado → Fazer login primeiro
2. Sessão expirada → Fechar e reabrir app
3. Sem internet → Verificar conexão
4. Bucket errado → Verificar `DEFAULT_BUCKET` em `infra/healthcheck.py`

**Solução:**
```python
# Alterar bucket padrão se necessário
# infra/healthcheck.py
DEFAULT_BUCKET = "seu-bucket-aqui"
```

### Retry não funciona

**Sintoma:** Operações falham na primeira tentativa

**Verificar:**
```python
# Usar run_cloud_op nas operações de rede
from utils.net_retry import run_cloud_op

# ❌ Sem retry
result = sb.storage.from_("bucket").list()

# ✅ Com retry
result = run_cloud_op(lambda: sb.storage.from_("bucket").list())
```

### Login trava

**Sintoma:** UI congela durante login

**Verificar:**
- Login deve usar `threading` (já implementado)
- `BusyOverlay` deve estar importado
- Não fazer operações pesadas na thread principal

### Limpeza remove algo importante

**Tranquilização:** Script faz dry-run primeiro e pede confirmação

**Se acidentalmente removido:**
```bash
# Restaurar via git
git restore core/auth/
git restore infrastructure/
git restore rc.ico
```

---

## 📝 Próximas Melhorias (Opcional)

1. **Cache de diagnóstico**
   - Guardar último resultado em memória
   - Mostrar status na barra inferior

2. **Diagnóstico automático no login**
   - Executar em background após login
   - Notificar se houver problemas

3. **Métricas de rede**
   - Latência das operações
   - Taxa de sucesso/retry

4. **Organizar pasta ajuda/**
   - Mover tests/, scripts/, docs/ para ajuda/
   - Manter raiz limpa

---

## 🎉 Conclusão

O RC-Gestor agora possui:
- ✅ **Diagnóstico completo** (Auth + Storage)
- ✅ **Retry automático** com backoff exponencial
- ✅ **Auto-refresh de sessão**
- ✅ **Tratamento robusto** de erros de rede
- ✅ **Login validado** com acesso ao Storage
- ✅ **Menu diagnóstico** intuitivo
- ✅ **Limpeza segura** de código legado
- ✅ **100% testado** e validado

---

**Commit sugerido:**
```bash
git add .
git commit -m "feat(app): diagnóstico Supabase (Auth+Storage) + retries/refresh; tratamento offline/401; script de limpeza segura"
```

---

## 📚 Referências Internas

- `infra/healthcheck.py` - Diagnóstico
- `utils/net_retry.py` - Retry com backoff
- `scripts/cleanup.py` - Limpeza segura
- `scripts/test_robustness.py` - Testes
- `docs/PROMPT-4-CHANGES.md` - Este documento
