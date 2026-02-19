# Diretório de Exports Temporários

⚠️ **Não versionar ZIPs, tar.gz ou arquivos grandes aqui.**

Este diretório é destinado a saídas temporárias de exportação (CSV, XLSX, etc.).

**Regras:**
- ✅ Exports pequenos (CSV, XLSX) podem ficar temporariamente
- ❌ Arquivos compactados grandes (ZIP, 7z, tar.gz) devem ser movidos para fora do projeto
- ♻️ Conteúdo deste diretório é local e não deve ser versionado no Git

**Limpeza:**
Arquivos grandes devem ser movidos para:
- `C:\Backups\RC_Gestor\` (ou similar)
- Unidade de rede corporativa
- Storage em nuvem

**Arquivos ignorados pelo Git:**
- `*.zip`
- `*.tar.gz`
- `*.7z`
