# Build do RC-Gestor v1.0.29

## Pré-requisitos

- Python 3.13+
- PyInstaller 6.16.0+
- Todas as dependências do `requirements.txt` instaladas

## Instruções de Build

### 1. Build do Executável

```powershell
pyinstaller build/rc_gestor.spec --clean
```

O executável será gerado em: `dist/RC-Gestor/RC-Gestor.exe`

### 2. Verificação de Segurança

✅ **O arquivo `.env` NÃO é incluído no bundle**
- Apenas recursos públicos são empacotados: `rc.ico`, `rc.png`
- Segredos devem ser fornecidos via variáveis de ambiente em runtime

### 3. Deploy

Para distribuir a aplicação:

1. Copie a pasta `dist/RC-Gestor/` completa para o ambiente de destino
2. Crie um arquivo `.env` no mesmo diretório do executável com as configurações necessárias:

```env
# .env (criar manualmente no ambiente de produção)
SUPABASE_URL=sua_url_aqui
SUPABASE_KEY=sua_chave_aqui
# ... outras variáveis
```

3. Execute `RC-Gestor.exe`

## Estrutura do Bundle

```
dist/RC-Gestor/
├── RC-Gestor.exe          # Executável principal
└── _internal/             # Bibliotecas e recursos
    ├── rc.ico             # Ícone da aplicação
    ├── rc.png             # Logo da aplicação
    ├── python313.dll      # Runtime Python
    ├── base_library.zip   # Biblioteca padrão Python
    └── [dependências...]  # Bibliotecas third-party
```

## Segurança

### Gestão de Segredos

- ❌ **NUNCA** inclua `.env` no `datas=[]` do spec
- ✅ Forneça segredos via:
  - Arquivo `.env` externo (runtime)
  - Variáveis de ambiente do sistema
  - Configuração de deployment

### Logs Seguros

O filtro `RedactSensitiveData` está ativo e redacta automaticamente:
- `apikey`, `api_key`
- `authorization`
- `token`, `access_token`
- `password`
- `secret`, `private_key`

## Troubleshooting

### Build falha com "module not found"

Adicione o módulo em `hiddenimports` no `build/rc_gestor.spec`:

```python
hiddenimports=[
    'tkinter',
    'ttkbootstrap',
    'seu_modulo_aqui',
],
```

### Executável não inicia

1. Verifique se o arquivo `.env` está presente no diretório do executável
2. Execute via PowerShell para ver mensagens de erro:
   ```powershell
   .\dist\RC-Gestor\RC-Gestor.exe
   ```

### Tamanho do executável muito grande

Revise `excludes` no spec para remover bibliotecas desnecessárias:

```python
excludes=[
    'matplotlib',
    'numpy',
    'pandas',
    # ... adicione outras
],
```

## Referências

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
