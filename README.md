# Gestor de Clientes v1.0.15

## Como executar
1. Crie e ative um ambiente virtual (exemplo no Windows PowerShell):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Instale as dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Execute a aplicacao desktop:
   ```bash
   python app_gui.py
   ```

## Smoke test
Valide o bootstrap basico da interface:
```bash
python scripts/smoke_test.py
```

### Build
Requer PyInstaller instalado.
Execute:
```bash
pyinstaller build/rc_gestor.spec --onefile
```

## Arquitetura
A camada de aplicacao (`application/`) orquestra controladores e casos de uso expostos para a interface, enquanto `adapters/` concentra integracoes com servicos externos (por exemplo, o storage do Supabase) e `shared/` fornece utilitarios transversais de configuracao, logging e telemetria. Essa separacao permite evoluir regras de negocio sem acoplar detalhes de infraestrutura ou de UI.

A apresentacao desktop fica em `presentation/gui` (mantido no pacote `gui/` durante a migracao) e consome servicos atraves dos controladores. Rotinas de infraestrutura auxiliar (healthchecks, scripts operacionais, migracoes) residem em `infrastructure/`, preservando o espaco para assets legados em `infra/` ate a retirada definitiva.

**Cloud-only:** defina `RC_NO_LOCAL_FS=1` (padrao) para bloquear gravacao em disco local. As variaveis de ambiente sao carregadas via `shared/config/environment.py`, que concatena `.env` empacotado e externo de forma segura.

## Onde ajustar cada parte
- `config/settings.py`: configuracoes carregadas de variaveis de ambiente ou `.env`.
- `config/constants.py`: larguras de colunas e textos fixos.
- `ui/components.py`: widgets reutilizaveis, menus e helpers visuais.
- `app_gui.py`: janela principal e fluxo de inicializacao do app.
- `infra/db/`: scripts de banco (`init_db.py`, `supabase_setup.sql`).

## Estrutura resumida
```
config/
  constants.py
  logging_config.py
  paths.py
  settings.py
application/
adapters/
core/
infra/
  db/
infrastructure/
scripts/
  smoke_test.py
shared/
gui/
  components.py
  forms/
ui/
utils/
app_gui.py
```
