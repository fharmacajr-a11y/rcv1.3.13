# Guia rápido — aplicar patches no Windows (v1.0.14)

## 1) Confirmar cabeçalhos e normalizar EOL (CRLF → LF)
```powershell
Select-String "^diff --git" .\patch-v1.0.14-rollup-phase1-4.diff -List
(Get-Content .\patch-v1.0.14-rollup-phase1-4.diff -Raw) -replace "`r`n","`n" | Set-Content .\patch-v1.0.14-rollup-phase1-4.diff -NoNewline -Encoding utf8
```
> Patches com CRLF podem falhar com “patch fragment without header”.

## 2) Dry-run e aplicar com tolerância (se necessário)
```powershell
git apply --stat .\patch-v1.0.14-rollup-phase1-4.diff
git apply --check .\patch-v1.0.14-rollup-phase1-4.diff
git apply --reject --ignore-space-change --whitespace=nowarn .\patch-v1.0.14-rollup-phase1-4.diff
# alternativa via commit/3-way:
# git add -A && git commit -m "savepoint antes do patch"
# git am --3way --signoff < .\patch-v1.0.14-rollup-phase1-4.diff
```

## 3) Conferir rejeições
```powershell
Get-ChildItem -Recurse -Filter *.rej
```
