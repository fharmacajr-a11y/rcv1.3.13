# QA-DELTA-35: Download de pastas (Clientes)

**Data**: 2025-11-13  
**Autor**: Codex (GPT-5)

---

## Arquivos alterados
- src/ui/files_browser.py

## Comportamento final
- O botão "Baixar pasta (.zip)" exige que uma pasta esteja selecionada; se não houver seleção ou se o item for arquivo, uma mensagem orienta o usuário.
- O prefixo alvo é calculado a partir do prefixo atual (org_id/client_id/...) e validado contra a raiz do cliente antes de chamar o download.
- Todo o fluxo de download está envolto em 	ry/except: qualquer erro exibe mensagem amigável e o aplicativo permanece aberto (inclui logging via _log).

## Validações
`
Ruff   src/ui data: OK
Flake8 src/ui data: OK
Pyright src/ui data: OK
`

Execução do app (python -m src.app_gui) não realizada aqui; a validação visual ficará a cargo do usuário.
