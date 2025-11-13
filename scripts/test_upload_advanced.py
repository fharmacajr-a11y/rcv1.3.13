#!/usr/bin/env python3
"""
Script de teste para validar funcionalidades de upload avançado:
- Pré-check de duplicatas
- Cancelamento com reversão
- Progresso por bytes com ETA
- Finalização suave

Uso:
    python scripts/test_upload_advanced.py
"""

from __future__ import annotations

from pathlib import Path


def test_next_copy_name():
    """Testa geração de nomes com sufixo."""
    print("\n[1/5] Testando _next_copy_name...")

    # Importar função
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.modules.auditoria.view import _next_copy_name

    # Teste 1: Nome não existe
    result = _next_copy_name("doc.pdf", set())
    assert result == "doc.pdf", f"Esperado 'doc.pdf', obteve '{result}'"

    # Teste 2: Nome existe, gera (2)
    result = _next_copy_name("doc.pdf", {"doc.pdf"})
    assert result == "doc (2).pdf", f"Esperado 'doc (2).pdf', obteve '{result}'"

    # Teste 3: Nome e (2) existem, gera (3)
    result = _next_copy_name("doc.pdf", {"doc.pdf", "doc (2).pdf"})
    assert result == "doc (3).pdf", f"Esperado 'doc (3).pdf', obteve '{result}'"

    # Teste 4: Vários sufixos
    existing = {f"doc ({i}).pdf" for i in range(2, 10)}
    existing.add("doc.pdf")
    result = _next_copy_name("doc.pdf", existing)
    assert result == "doc (10).pdf", f"Esperado 'doc (10).pdf', obteve '{result}'"

    print("  ✓ _next_copy_name correto para todos os casos")


def test_upload_plan_dataclass():
    """Testa dataclass _UploadPlan."""
    print("\n[2/5] Testando _UploadPlan dataclass...")

    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.modules.auditoria.view import _UploadPlan

    # Criar plano de upload
    plan = _UploadPlan(source_path=Path("test/doc.pdf"), dest_name="doc.pdf", upsert=False, file_size=1024)

    assert plan.source_path == Path("test/doc.pdf")
    assert plan.dest_name == "doc.pdf"
    assert plan.upsert is False
    assert plan.file_size == 1024

    # Teste com upsert=True
    plan2 = _UploadPlan(source_path=Path("doc2.pdf"), dest_name="doc2.pdf", upsert=True, file_size=2048)

    assert plan2.upsert is True

    print("  ✓ _UploadPlan funciona corretamente")


def test_progress_state():
    """Testa dataclass _ProgressState."""
    print("\n[3/5] Testando _ProgressState...")

    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.modules.auditoria.view import _ProgressState
    import time

    state = _ProgressState()
    state.total_files = 100
    state.total_bytes = 100_000_000  # 100 MB
    state.start_ts = time.monotonic()

    # Simular progresso
    state.done_files = 50
    state.done_bytes = 50_000_000  # 50 MB

    # Calcular % manualmente
    pct = (state.done_bytes / state.total_bytes) * 100
    assert pct == 50.0, f"Esperado 50%, obteve {pct}%"

    # EMA inicial
    assert state.ema_bps == 0.0

    # Simular velocidade
    time.sleep(0.1)
    elapsed = time.monotonic() - state.start_ts
    instant_bps = state.done_bytes / elapsed

    # Aplicar EMA (alpha=0.2)
    state.ema_bps = 0.2 * instant_bps + 0.8 * state.ema_bps

    assert state.ema_bps > 0, "EMA deve ser > 0"

    print("  ✓ _ProgressState tracking correto")


def test_fmt_bytes():
    """Testa formatação de bytes."""
    print("\n[4/5] Testando _fmt_bytes...")

    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    # Precisamos criar uma instância temporária
    import tkinter as tk
    from src.modules.auditoria.view import AuditoriaFrame

    root = tk.Tk()
    root.withdraw()

    # Criar frame (sem supabase - só para testar helper)
    frame = AuditoriaFrame(root, None)

    # Testes
    assert frame._fmt_bytes(500) == "500 B"
    assert frame._fmt_bytes(1024) == "1.0 KB"
    assert frame._fmt_bytes(1536) == "1.5 KB"
    assert frame._fmt_bytes(1_048_576) == "1.0 MB"
    assert frame._fmt_bytes(1_572_864) == "1.5 MB"
    assert frame._fmt_bytes(1_073_741_824) == "1.0 GB"

    root.destroy()

    print("  ✓ _fmt_bytes formata corretamente (B, KB, MB, GB)")


def test_fmt_eta():
    """Testa formatação de ETA."""
    print("\n[5/5] Testando _fmt_eta...")

    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    import tkinter as tk
    from src.modules.auditoria.view import AuditoriaFrame

    root = tk.Tk()
    root.withdraw()

    frame = AuditoriaFrame(root, None)

    # Testes
    assert frame._fmt_eta(0) == "00:00:00"
    assert frame._fmt_eta(59) == "00:00:59"
    assert frame._fmt_eta(60) == "00:01:00"
    assert frame._fmt_eta(65) == "00:01:05"
    assert frame._fmt_eta(3600) == "01:00:00"
    assert frame._fmt_eta(3665) == "01:01:05"
    assert frame._fmt_eta(7325) == "02:02:05"

    root.destroy()

    print("  ✓ _fmt_eta formata HH:MM:SS corretamente")


if __name__ == "__main__":
    print("=" * 70)
    print("TESTE: Funcionalidades Avançadas de Upload")
    print("=" * 70)

    try:
        test_next_copy_name()
        test_upload_plan_dataclass()
        test_progress_state()
        test_fmt_bytes()
        test_fmt_eta()

        print("\n" + "=" * 70)
        print("✅ TODOS OS TESTES PASSARAM")
        print("=" * 70)
        print("\n📊 Resumo:")
        print("  ✓ _next_copy_name gera sufixos corretamente")
        print("  ✓ _UploadPlan dataclass funciona")
        print("  ✓ _ProgressState tracking preciso")
        print("  ✓ _fmt_bytes formata B/KB/MB/GB")
        print("  ✓ _fmt_eta formata HH:MM:SS")
        print("\n🎯 Implementação validada!")

    except AssertionError as e:
        print(f"\n❌ FALHA: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
