# Devlog – Clients Picker Refactor (All Contexts)

## Problema
- APIs antigas (`navigate_to("clients_picker")`, `App.open_clients_picker`) caíam sempre no mesmo fluxo de retorno (Senhas), o que permitia mistura de contextos.
- O banner do modo seleção era fixo, impedindo mensagens específicas para Senhas, Obrigações e outros módulos.
- Precisávamos garantir que todo fluxo passasse obrigatoriamente pela nova API `start_client_pick_mode`, com callback e `return_to` explícitos.

## Solução Implementada
- Centralizei `_open_clients_picker` como wrapper **deprecated** que apenas delega para `start_client_pick_mode` com banner legado e fallback para Senhas.
- Atualizei `App.open_clients_picker` para usar a nova API com parâmetros opcionais e mensagem padrão, evitando chamadas diretas ao router antigo.
- `start_client_pick_mode` agora repassa o `banner_text` para a tela de clientes; `MainScreenFrame.start_pick` e `PickModeController` recebem o parâmetro e atualizam o banner dinamicamente, revertendo para o texto padrão quando não informado.
- Fluxos já migrados (Senhas e Obrigações) continuam usando `start_client_pick_mode`, mas agora a UI realmente reflete o texto fornecido.
- Testes unitários cobrindo controller e PickMode foram expandidos para garantir que:
  - `_open_clients_picker` sempre delega para a nova API com `return_to` correto;
  - `start_client_pick_mode` chama `frame.start_pick` com o banner recebido;
  - `PickModeController.start_pick` aplica o texto customizado e restaura o padrão quando necessário.

## Testes Executados
- `pytest tests/unit/modules/clientes/views/ -q --tb=short -k "not LEGACY"`
- `pytest tests/unit/modules/main_window/test_main_window_controller_fase12.py -q --tb=short`
- `python -m ruff check src/modules/main_window/controller.py src/modules/main_window/views/main_window.py src/modules/clientes/views/main_screen.py src/modules/clientes/views/pick_mode.py tests/unit/modules/main_window/test_main_window_controller_fase12.py tests/unit/modules/clientes/views/test_pick_mode_round8.py --fix`

## Orientações de Verificação Manual
1. **Senhas**: abrir “Nova senha” ⇒ banner deve mencionar criação de senha e, após cancelar ou confirmar, retornar à tela de Senhas.
2. **Hub > Obrigações**: clicar em “Nova obrigação” ⇒ banner deve mencionar obrigações e, ao cancelar, voltar ao Hub.
3. **Fluxo legado/App**: qualquer atalho que ainda invoque `App.open_clients_picker` deve cair no banner padrão e voltar ao contexto original especificado.
