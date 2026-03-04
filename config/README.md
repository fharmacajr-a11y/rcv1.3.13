# Configuração do ChatGPT

Esta pasta contém configurações para integração com a API da OpenAI.

## Como configurar a chave da API OpenAI

⚠️ **IMPORTANTE**: A chave OpenAI é lida **exclusivamente** da variável de
ambiente `OPENAI_API_KEY`.  Nenhum arquivo local é consultado.

### Configuração via Variável de Ambiente

```powershell
# PowerShell (sessão)
$env:OPENAI_API_KEY = "sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXX"
python -m src.app_gui
```

```bash
# Linux/macOS
export OPENAI_API_KEY="sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXX"
python -m src.app_gui
```

Ou adicione ao arquivo `.env` na raiz do projeto (já listado no `.gitignore`).

## Obtendo uma chave da API

1. Acesse https://platform.openai.com/api-keys
2. Faça login na sua conta OpenAI
3. Clique em "Create new secret key"
4. Copie a chave gerada (começa com `sk-proj-` ou `sk-`)
5. **Importante:** Guarde a chave em local seguro, ela só é exibida uma vez

## Troubleshooting

- **"biblioteca 'openai' não está instalada"** — ative o venv e execute:
  `python -m pip install --upgrade "openai>=1.40.0"`

- **"variável de ambiente OPENAI_API_KEY não está definida"** — defina a
  variável conforme instruções acima.

- **Erro de autenticação** — verifique se a chave está correta e se a conta
  OpenAI tem créditos disponíveis.
