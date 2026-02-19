# Binários do 7-Zip

Este diretório contém os binários do 7-Zip **embarcados no repositório** para extração de arquivos RAR.

## Arquivos Incluídos

- `7z.exe` - Executável principal do 7-Zip (x64, ~550 KB)
- `7z.dll` - Biblioteca de suporte do 7-Zip (x64, ~1.9 MB)

## Versão

- **7-Zip**: 24.09 (2024-11-25)
- **Arquitetura**: 64-bit x64
- **Origem**: https://www.7-zip.org/download.html

## Funcionalidade

Os binários são usados para:
- Extração de arquivos `.rar` (incluindo RAR5)
- Alternativa para `.zip` (embora o projeto use `zipfile` do Python para ZIP)

## Licença

7-Zip é software livre sob licença **GNU LGPL** + unRAR restriction.

Veja a licença completa em: `third_party/7zip/LICENSE.txt`

**Importante**: O código de descompressão RAR não pode ser usado para criar compactadores RAR (restrição do unRAR).

## Build/PyInstaller

Os binários são incluídos automaticamente no build via `rcgestor.spec`:

```python
Analysis(
    binaries=[
        ('infra/bin/7zip/7z.exe', '7z'),
        ('infra/bin/7zip/7z.dll', '7z'),
    ],
    ...
)
```

No executável final, os binários ficam em `<_MEIPASS>/7z/` e são encontrados pela função `find_7z()` em `infra/archive_utils.py`.

## Nota para Desenvolvedores

**Estes binários estão commitados no repositório** para que os usuários finais não precisem instalar nada.

Se você estiver desenvolvendo localmente:
- Os binários já estão incluídos (não precisa baixar)
- O código também busca 7-Zip no PATH do sistema como fallback
- Para testar extração RAR: `pytest tests/test_archives.py -v`
