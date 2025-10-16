# Gestor de Clientes v1.0.7

## Como executar
1. Crie e ative um ambiente virtual (exemplo no Windows PowerShell):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Execute a aplicação desktop:
   ```bash
   python app_gui.py
   ```

## Smoke test
Valide o bootstrap básico da interface:
```bash
python scripts/smoke_test.py
```

## Onde ajustar cada parte
- `config/settings.py`: configurações carregadas de variáveis de ambiente/.env.
- `config/constants.py`: larguras de colunas e textos fixos.
- `ui/components.py`: widgets reutilizáveis, menus e helpers visuais.
- `app_gui.py`: janela principal e fluxo de inicialização do app.
- `infra/db/`: scripts de banco (`init_db.py`, `supabase_setup.sql`).

## Estrutura resumida
```
config/
  constants.py
  logging_config.py
  paths.py
  settings.py
core/
infra/
  db/
scripts/
  smoke_test.py
ui/
  components.py
  forms/
utils/
app_gui.py
```
