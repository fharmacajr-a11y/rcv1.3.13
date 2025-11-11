# Binários do 7-Zip

Este diretório deve conter os binários do 7-Zip para extração de arquivos RAR:

- `7z.exe` - Executável principal do 7-Zip (x64)
- `7z.dll` - Biblioteca de suporte do 7-Zip (x64)

## Download

Baixe o 7-Zip em: https://www.7-zip.org/download.html

1. Baixe a versão **64-bit x64** (7-Zip Extra ou 7-Zip Standalone)
2. Extraia `7z.exe` e `7z.dll` para este diretório
3. Os arquivos serão incluídos automaticamente no build via PyInstaller

## Versão Recomendada

- 7-Zip 24.xx ou superior (suporte completo a RAR5)

## Build/PyInstaller

Os binários são incluídos no build através do arquivo `rcgestor.spec`:

```python
Analysis(
    binaries=[
        ('infra/bin/7zip/7z.exe', '7z'),
        ('infra/bin/7zip/7z.dll', '7z'),
    ],
    ...
)
```

Ou via linha de comando:
```bash
pyinstaller --add-binary "infra/bin/7zip/7z.exe;7z" --add-binary "infra/bin/7zip/7z.dll;7z" ...
```

## Licença

7-Zip é software livre sob licença GNU LGPL.
Veja: https://www.7-zip.org/license.txt
