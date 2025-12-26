# Configuração do ChatGPT

Esta pasta contém configurações para integração com a API da OpenAI.

## Como configurar a chave da API OpenAI

⚠️ **IMPORTANTE - SEGURANÇA**: Por razões de segurança, a chave OpenAI deve ser configurada APENAS via variável de ambiente. Não armazene chaves em arquivos que possam ser distribuídos com o aplicativo.

### Configuração via Variável de Ambiente (OBRIGATÓRIA)

Configure a variável de ambiente `OPENAI_API_KEY` antes de iniciar o aplicativo:

```powershell
# PowerShell
$env:OPENAI_API_KEY = "sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXX"
python -m src.app_gui
```

```bash
# Linux/macOS
export OPENAI_API_KEY="sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXX"
python -m src.app_gui
```

### ⛔ Opção DESCONTINUADA: Arquivo de configuração

**NÃO use mais** `config/openai_key.txt` para armazenar chaves. Esta opção foi removida por questões de segurança (risco de distribuição acidental da chave no executável).

O arquivo `openai_key.example.txt` é mantido apenas como referência de formato.

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
