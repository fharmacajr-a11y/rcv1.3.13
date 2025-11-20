# Modulo Senhas - Overview

## Responsabilidades
- Gerenciar senhas (listar, filtrar por texto/serviço, ordenar, copiar senha) para a organização logada.
- Permitir criação/edição via diálogo modal (seleção de cliente, serviço, login, senha, anotações).
- Integrar com Supabase para identificar usuário/org e persistir senhas via repositório de senhas.

## Situacao atual
- Código principal vive em `src/modules/passwords/`:
  - `controller.py` centraliza operações de dados (carregar/filtrar, criar/atualizar/excluir, decrypt, buscar clientes).
  - `views/passwords_screen.py` contém `PasswordsScreen` e `PasswordDialog`, usando o `PasswordsController` para chamadas de domínio.
  - `view.py` expõe `PasswordsFrame` como alias compatível.
  - `service.py` reexporta o repositório de senhas legado.
- Pacote `src/ui/passwords_screen.py` foi reduzido a shim que reexporta `PasswordDialog`/`PasswordsScreen`, preservando os imports legados.

## Arquivos principais
- `src/modules/passwords/views/passwords_screen.py`: UI completa (tabela, filtros, botões, diálogos) delegando operações ao controller.
- `src/modules/passwords/controller.py`: chamadas de dados (supabase picker de clientes, create/update/delete, decrypt, filtros em memória).
- `src/modules/passwords/view.py`: alias `PasswordsFrame` para compatibilidade com main window/router.
- `src/ui/passwords_screen.py`: shim mínimo para manter API pública anterior.

## Riscos / pontos de atencao
- Dependência direta do cliente Supabase para recuperar `org_id`/`user_id` permanece na view.
- Controller mantém cache em memória de senhas; mudanças no ciclo de vida do screen podem exigir refresh explícito.
- Diálogo de senha ainda manipula strings sensíveis na memória/clipboard; não houve alteração de UX/security além da movimentação de código.
