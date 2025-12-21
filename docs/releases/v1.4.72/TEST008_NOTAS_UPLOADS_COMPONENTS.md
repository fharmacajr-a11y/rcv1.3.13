# TEST-008 — Uploads Components Helpers

**Data**: 2025-12-20  
**Fase**: 65 (v1.4.72)

## Alvo Selecionado

**Arquivo**: `src/modules/uploads/components/helpers.py`

O arquivo existe e contém funções "headless" (sem GUI) para:
- Formatação de CNPJ
- Manipulação de strings (strip CNPJ da razão social)
- Construção de prefixos de cliente
- Obtenção de org_id via Supabase

## Funções Mapeadas

1. `_cnpj_only_digits(text: str) -> str` - Wrapper para only_digits
2. `format_cnpj_for_display(cnpj: str) -> str` - Formata CNPJ para exibição
3. `strip_cnpj_from_razao(razao: str, cnpj: str) -> str` - Remove CNPJ do fim da razão social
4. `get_clients_bucket() -> str` - Retorna nome do bucket
5. `client_prefix_for_id(client_id: int, org_id: str) -> str` - Delega para build_client_prefix
6. `get_current_org_id(sb) -> str` - Busca org_id via Supabase

## Estratégia de Teste

### Funções Puras (A)
- `_cnpj_only_digits`: None, string vazia, com/sem dígitos
- `format_cnpj_for_display`: 14 dígitos, menos/mais dígitos
- `strip_cnpj_from_razao`: com/sem CNPJ no fim, variações de separadores
- `get_clients_bucket`: retorno constante

### Delegação/Builders (C)
- `client_prefix_for_id`: delega para build_client_prefix

### Integração Supabase (B)
- `get_current_org_id`: mock de cliente Supabase (success/fail)

## Arquivo de Teste

`tests/unit/modules/uploads/test_uploads_components_helpers_fase65.py`

## Comando de Execução

```bash
pytest -q tests/unit/modules/uploads/test_uploads_components_helpers_fase65.py
```
