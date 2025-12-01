# COV-SEC-001 / SEG-004 – Aumento de cobertura em security/crypto.py

**Data:** 23 de novembro de 2025  
**Projeto:** RC Gestor de Clientes v1.2.55  
**Branch:** qa/fixpack-04  
**Responsável:** Teste automatizado (fase 33)

---

## 1. Resumo

Foram criados **21 novos testes unitários** para o módulo `security/crypto.py`, cobrindo todos os fluxos principais de criptografia/descriptografia Fernet, tratamento de erros, validação de entradas e casos de uso reais da aplicação.

**Resultado:**
- **Cobertura anterior:** ~19,5% (apenas 2 das 3 funções tinham testes indiretos)
- **Cobertura atual:** **95,1%** (35 statements, apenas 2 linhas não cobertas)
- **Meta atingida:** ✅ Sim (meta era ≥ 80%, alcançamos 95,1%)
- **Impacto no App Core:** Cobertura total aumentou de **38,17%** para **38,64%** (+0,47pp)

Nenhum comportamento público foi alterado. O módulo `security/crypto.py` não sofreu modificações - apenas foi criado o arquivo de testes `tests/test_security_crypto_fase33.py`.

---

## 2. Análise do Módulo

### Estrutura do módulo `security/crypto.py`

O módulo contém **3 funções**:

1. **`_get_encryption_key() -> bytes`** (privada)
   - Obtém a chave de criptografia da variável de ambiente `RC_CLIENT_SECRET_KEY`
   - Valida que a chave existe e retorna em formato bytes
   - Levanta `RuntimeError` se a chave não for encontrada

2. **`encrypt_text(plain: str) -> str`** (pública)
   - Criptografa texto usando Fernet (symmetric encryption)
   - Retorna token em base64 (string)
   - Retorna string vazia se `plain` for vazio/None
   - Levanta `RuntimeError` em caso de erro

3. **`decrypt_text(token: str) -> str`** (pública)
   - Descriptografa token Fernet
   - Retorna texto original
   - Retorna string vazia se `token` for vazio/None
   - Levanta `RuntimeError` em caso de erro

### Pontos de uso no app

- **`data/supabase_repo.py`:** importa `encrypt_text` e `decrypt_text` para criptografar senhas de clientes no banco
- **`src/modules/passwords/controller.py`:** importa `decrypt_text` para exibir senhas descriptografadas na UI

---

## 3. Cenários de Teste Implementados

### 3.1) Round-trip (encrypt → decrypt) - Casos felizes

✅ **`test_encrypt_decrypt_roundtrip_texto_simples`**
- Testa que texto ASCII simples (`"senha-teste"`) é criptografado e depois recuperado corretamente

✅ **`test_encrypt_decrypt_roundtrip_unicode`**
- Testa que caracteres acentuados (`"áéíóú ç ãõ ÀÈÌÒÙ ñ €"`) são preservados

✅ **`test_encrypt_decrypt_roundtrip_texto_longo`**
- Testa texto longo com múltiplas linhas e emoji (🔐)

✅ **`test_encrypt_decrypt_roundtrip_string_vazia`**
- Testa que string vazia retorna vazia sem erro

✅ **`test_encrypt_text_nao_retorna_valor_original`**
- Garante que o texto criptografado é diferente do original e não vazio

### 3.2) Entradas inválidas

✅ **`test_encrypt_text_com_none_retorna_vazio`**
- Verifica que `encrypt_text(None)` retorna `""` sem erro

✅ **`test_decrypt_text_com_none_retorna_vazio`**
- Verifica que `decrypt_text(None)` retorna `""` sem erro

✅ **`test_encrypt_text_sem_chave_no_env_levanta_runtime_error`**
- Testa que sem `RC_CLIENT_SECRET_KEY` no ambiente, levanta `RuntimeError`

✅ **`test_decrypt_text_sem_chave_no_env_levanta_runtime_error`**
- Idem para `decrypt_text`

✅ **`test_get_encryption_key_com_chave_invalida_levanta_runtime_error`**
- Testa que chave Fernet inválida (não base64) causa `RuntimeError`

### 3.3) Chave errada / dados corrompidos

✅ **`test_decrypt_with_wrong_key_levanta_runtime_error`**
- Criptografa com uma chave, tenta descriptografar com outra → erro

✅ **`test_decrypt_token_corrompido_levanta_runtime_error`**
- Modifica bytes no meio do token criptografado → erro ao descriptografar

✅ **`test_decrypt_token_base64_invalido_levanta_runtime_error`**
- Token que não é base64 válido → erro

### 3.4) Compatibilidade com API usada no app

✅ **`test_encrypt_text_formato_usado_em_data_supabase_repo`**
- Valida que `encrypt_text` retorna string conforme esperado pelo repositório

✅ **`test_decrypt_text_formato_usado_em_passwords_controller`**
- Valida que `decrypt_text` retorna string conforme esperado pelo controller

✅ **`test_encrypt_decrypt_com_espacos_e_caracteres_especiais`**
- Testa que senhas com espaços, tabs e quebras de linha são preservadas

### 3.5) Testes de funções internas e logging

✅ **`test_get_encryption_key_retorna_bytes`**
- Testa diretamente `_get_encryption_key()` para garantir que retorna bytes válidos

✅ **`test_encrypt_text_com_exception_no_fernet_e_capturada`**
- Mock de `Fernet.encrypt` para levantar exceção → verifica que é capturada e re-levantada como `RuntimeError`

✅ **`test_decrypt_text_com_exception_no_fernet_e_capturada`**
- Idem para `Fernet.decrypt`

✅ **`test_encrypt_text_loga_exception_em_caso_de_erro`**
- Verifica que exceções são logadas (usando `caplog`)

✅ **`test_decrypt_text_loga_exception_em_caso_de_erro`**
- Idem para `decrypt_text`

---

## 4. Comandos Executados

### 4.1) Rodar testes específicos do módulo

```powershell
python -m pytest tests/test_security_crypto_fase33.py -v
```

**Resultado:**
```
========================== test session starts ==========================
platform win32 -- Python 3.13.7, pytest-8.4.2, pluggy-1.6.0
collected 21 items

tests\test_security_crypto_fase33.py .....................         [100%]

========================== 21 passed in 0.25s ===========================
```

✅ **21 testes passaram** sem erros.

---

### 4.2) Medir cobertura específica de `security/crypto.py`

```powershell
python -m pytest --cov=security --cov-report=term-missing tests/test_security_crypto_fase33.py -q
```

**Resultado:**
```
Name                   Stmts   Miss Branch BrPart  Cover   Missing
------------------------------------------------------------------
security\__init__.py       0      0      0      0 100.0%
security\crypto.py        35      2      6      0  95.1%   24-25
------------------------------------------------------------------
TOTAL                     35      2      6      0  95.1%
```

**Análise:**
- **95,1% de cobertura** do módulo `security/crypto.py` ✅
- Apenas **2 linhas não cobertas** (24-25):
  - Linhas 24-25 são o bloco `except Exception` dentro de `_get_encryption_key()` que captura erro ao fazer `key_str.encode("utf-8")`
  - Esse erro é praticamente impossível de ocorrer (`.encode()` em string sempre funciona)
  - Para cobrir seria necessário mock muito artificial (não vale o esforço)

**Meta atingida:** ✅ Sim (meta era ≥ 80%, alcançamos **95,1%**)

---

### 4.3) Validar com suite completa (App Core coverage)

```powershell
python -m pytest --cov --cov-report=term-missing --cov-fail-under=25 -q
```

**Resultado (resumido):**
```
security\crypto.py        35      2      6      0  95.1%   24-25
...
TOTAL                  15886   9420   3500    241  38.6%
Required test coverage of 25% reached. Total coverage: 38.64%
```

**Análise:**
- ✅ Todos os **1105 testes** passaram (21 novos + 1084 existentes)
- ✅ Nenhum teste quebrou
- ✅ Cobertura do App Core aumentou de **38,17%** (baseline) para **38,64%** (+0,47pp)

**Detalhamento do aumento:**
- `security/crypto.py`: 19,5% → **95,1%** (+75,6pp)
- Pacote `security/` como um todo agora tem cobertura muito superior

---

## 5. Impacto no Checklist

### Tarefas Relacionadas

**P0 - SEG-004:** Aumentar cobertura do módulo de criptografia (`security/crypto.py`)
- **Status:** ✅ **CONCLUÍDO**
- **Meta:** Garantir testes robustos para módulo crítico de segurança
- **Resultado:** 21 testes criados, 95,1% de cobertura

**P1 - COV-SEC-001:** Aumentar cobertura de `security/crypto.py` (19,5% → ≥ 80%)
- **Status:** ✅ **CONCLUÍDO**
- **Meta:** ≥ 80% de cobertura
- **Resultado:** **95,1%** (superou a meta em 15,1pp)

### Próximos Passos

Após a conclusão de **COV-SEC-001**, as próximas tarefas de coverage do App Core são:

1. **COV-DATA-001** (P1): Aumentar cobertura de `data/supabase_repo.py` (16,2% → ≥ 50%)
   - Esforço estimado: 4-6h
   - Prioridade: ALTA (repositório principal de dados)

2. **COV-INFRA-001** (P1): Aumentar cobertura de `infra/settings.py` (~0% → ≥ 50%) e `infra/storage_client.py` (~14% → ≥ 50%)
   - Esforço estimado: 4-6h
   - Prioridade: ALTA

3. **COV-ADAPTERS-001** (P1): Aumentar cobertura de `adapters/storage/supabase_storage.py` (36,8% → ≥ 70%)
   - Esforço estimado: 3-4h
   - Prioridade: MÉDIA

---

## 6. Arquivos Criados/Modificados

### 6.1) Arquivos Criados

✅ **`tests/test_security_crypto_fase33.py`** (334 linhas)
- 21 funções de teste
- 3 fixtures (`valid_fernet_key`, `mock_env_key`, `mock_env_key_missing`)
- Cobertura completa de cenários felizes, erros, casos extremos e uso real no app

✅ **`dev/cov_sec_crypto.md`** (este documento)
- Documentação completa da tarefa COV-SEC-001 / SEG-004

### 6.2) Arquivos NÃO Modificados

- `security/crypto.py` - **sem alterações** (contrato público preservado)
- `.coveragerc` - sem alterações
- `pytest.ini` - sem alterações
- Nenhum código de produção foi alterado

---

## 7. Observações Técnicas

### Uso de Fixtures

- **`valid_fernet_key`:** Gera chave Fernet válida para testes (usando `Fernet.generate_key()`)
- **`mock_env_key`:** Mock da variável `RC_CLIENT_SECRET_KEY` com chave válida (usando `monkeypatch`)
- **`mock_env_key_missing`:** Remove a variável do ambiente para testar erros

### Uso de Mocks

- **`patch("security.crypto.Fernet")`:** Para simular exceções internas do Fernet
- **`monkeypatch.setenv/delenv`:** Para controlar variáveis de ambiente
- **`caplog`:** Para verificar que exceções são logadas

### Tratamento de None

Os testes validam que `encrypt_text(None)` e `decrypt_text(None)` retornam `""` (string vazia) sem erro, conforme o comportamento atual do código (`if not plain: return ""`). Isso garante compatibilidade com chamadas do app que podem passar valores None.

---

## 8. Recomendações Futuras

### 8.1) Coverage Completo (100%)

Para atingir 100% de cobertura, seria necessário cobrir as linhas 24-25 de `security/crypto.py`:

```python
except Exception as e:
    raise RuntimeError(f"Erro ao processar RC_CLIENT_SECRET_KEY: {e}")
```

Esse bloco só seria executado se `str.encode("utf-8")` levantasse exceção, o que é praticamente impossível em Python moderno. Para cobrir, seria necessário:
- Mock extremamente artificial de `str.encode`
- Ou introduzir um tipo que não é string mas passa no `if not key_str`

**Recomendação:** Não vale o esforço. 95,1% é excelente para um módulo de segurança.

### 8.2) Testes de Integração

Considerar criar testes de integração que:
- Usem `data/supabase_repo.py` para salvar/recuperar senha criptografada
- Validem o fluxo completo UI → controller → crypto → repo → banco

Esses testes já existem parcialmente em:
- `tests/test_clientes_integration.py`
- `tests/test_clientes_forms_upload.py`

### 8.3) Rotação de Chaves

O módulo atual não suporta rotação de chaves. Se a `RC_CLIENT_SECRET_KEY` mudar, todos os dados criptografados anteriormente se tornam irrecuperáveis.

**Recomendação futura:** Considerar implementar versionamento de chaves ou usar AWS KMS / Azure Key Vault para gerenciamento centralizado.

---

## 9. Conclusão

✅ **SEG-004 / COV-SEC-001 - CONCLUÍDO COM SUCESSO**

- **21 novos testes** criados
- **95,1% de cobertura** alcançada (meta era ≥ 80%)
- **Nenhum código de produção alterado**
- **Todos os 1105 testes passam** (incluindo os 21 novos)
- **App Core coverage:** 38,17% → 38,64% (+0,47pp)

O módulo de criptografia `security/crypto.py` agora possui testes robustos cobrindo:
- ✅ Fluxos felizes (round-trip encrypt/decrypt)
- ✅ Tratamento de erros (chave ausente, chave inválida, token corrompido)
- ✅ Casos extremos (None, string vazia, unicode, texto longo)
- ✅ Compatibilidade com uso real no app (supabase_repo, passwords controller)
- ✅ Logging de exceções

**Próximo passo recomendado:** Iniciar **COV-DATA-001** (cobertura de `data/supabase_repo.py`).

---

## 10. Atualização de Type Hints

**Data:** 23/11/2025 (após conclusão da fase 33)

Os type hints das funções públicas `encrypt_text` e `decrypt_text` foram ajustados para refletir o comportamento real do código:

**Antes:**
```python
def encrypt_text(plain: str) -> str:
def decrypt_text(token: str) -> str:
```

**Depois:**
```python
def encrypt_text(plain: str | None) -> str:
def decrypt_text(token: str | None) -> str:
```

**Motivo:** Ambas as funções já tratavam `None` corretamente (retornando string vazia via `if not plain: return ""`), mas os type hints não refletiam isso, causando warnings `reportArgumentType` no Pylance quando os testes passavam `None` explicitamente (casos de teste `test_encrypt_text_com_none_retorna_vazio` e `test_decrypt_text_com_none_retorna_vazio`).

**Impacto:**
- ✅ Warnings do Pylance eliminados em `tests/test_security_crypto_fase33.py`
- ✅ Nenhuma mudança na lógica de execução
- ✅ Cobertura mantida em **95,1%**
- ✅ Todos os 21 testes continuam passando

As docstrings também foram atualizadas para documentar explicitamente que `None` ou string vazia retornam string vazia.

---

**Atualizado em:** 23/11/2025  
**Documento gerado automaticamente após conclusão de fase 33**
