# Devlog — Bump de versão para 1.3.92

- Versão anterior detectada: v1.3.61 definida em `src/version.py`.
- Pontos atualizados para 1.3.92:
  - `src/version.py`: fonte única de verdade da versão (consumida por splash, MainWindow e `rcgestor.spec`).
  - `installer/rcgestor.iss`: `MyAppVersion` e nome do executável ajustados.
  - `version_file.txt`: metadados do executável (FileVersion/ProductVersion/OriginalFilename).
  - `README.md`: badge, caminho do executável gerado e seção "Última versão".
  - `requirements.txt` e `requirements-dev.txt`: cabeçalhos de referência de versão.
- Conferência: não alterei `docs/` nem pastas de backup/legado; referências antigas a 1.3.61 permanecem apenas em documentos históricos e comentários legados.
