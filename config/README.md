# Configuração do ChatGPT

Esta pasta contém configurações para integração com a API da OpenAI.

## Como configurar a chave da API OpenAI

O módulo ChatGPT do RC suporta duas formas de configuração da chave:

### Opção 1: Arquivo de configuração (Recomendado para Windows)

1. Copie o arquivo `openai_key.example.txt` e renomeie para `openai_key.txt`
2. Abra `openai_key.txt` em um editor de texto
3. Cole sua chave da API OpenAI (formato `sk-proj-...` ou `sk-...`)
4. Salve o arquivo

**Importante:** O arquivo `openai_key.txt` está no `.gitignore` e não será versionado.

### Opção 2: Variável de ambiente

Configure a variável de ambiente `OPENAI_API_KEY` antes de iniciar o aplicativo:

```powershell
# PowerShell
$env:OPENAI_API_KEY = "sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXX"
python -m src.app_gui
```

### Prioridade

Se ambas as configurações existirem, a **variável de ambiente** tem prioridade sobre o arquivo.

## Obtendo uma chave da API

1. Acesse https://platform.openai.com/api-keys
2. Faça login na sua conta OpenAI
3. Clique em "Create new secret key"
4. Copie a chave gerada (começa com `sk-proj-` ou `sk-`)
5. **Importante:** Guarde a chave em local seguro, ela só é exibida uma vez

## Troubleshooting

- Se o ChatGPT mostrar "biblioteca 'openai' não está instalada":
  - Certifique-se de que está com o venv ativado
  - Execute: `python -m pip install --upgrade "openai>=1.40.0"`

- Se mostrar "variável de ambiente OPENAI_API_KEY não está definida...":
  - Configure a chave usando uma das opções acima

- Se der erro de autenticação:
  - Verifique se a chave está correta
  - Confirme que sua conta OpenAI tem créditos disponíveis
