#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Quickcheck do módulo de clientes: validação rápida de performance e leaks.

Uso:
    python scripts/clients_quickcheck.py           # Apenas perf (5000 linhas)
    python scripts/clients_quickcheck.py --stress  # Perf + stress test (50 ciclos)

Exit codes:
    0 = OK
    1 = Falha de performance ou leak detectado
    2 = Erro de execução (exceção não tratada)
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
import tkinter as tk
import tracemalloc

# Adiciona raiz do projeto ao path
sys.path.insert(0, str(__file__).rsplit("scripts", 1)[0].rstrip("\\/"))

# Limites de aceite
RENDER_LIMIT_5K = 0.5  # segundos (margem de segurança)
STRESS_MEMORY_LIMIT_MB = 10.0  # MB de delta máximo
STRESS_CYCLES = 50

# Status global
_errors: list[str] = []


def _log_error(msg: str) -> None:
    """Registra erro para relatório final."""
    _errors.append(msg)
    print(f"  ✗ FAIL: {msg}")


def _log_ok(msg: str) -> None:
    """Registra sucesso."""
    print(f"  ✓ OK: {msg}")


def run_perf_test(n_rows: int = 5000) -> bool:
    """Executa teste de performance com N linhas. Retorna True se passou."""
    print(f"\n[PERF] Testando render de {n_rows} linhas...")

    try:
        import ttkbootstrap as tb
        from src.modules.clientes.viewmodel import ClienteRow
        from src.modules.clientes.controllers.rendering_adapter import build_row_tags
        from src.ui.components.lists import create_clients_treeview
    except ImportError as e:
        _log_error(f"Import falhou: {e}")
        return False

    # Gerar dados mock
    from datetime import datetime

    now = datetime.now().isoformat()
    rows: list[ClienteRow] = []
    for i in range(n_rows):
        obs = "[ATIVO] Obs" if i % 3 == 0 else ""
        rows.append(
            ClienteRow(
                id=str(i + 1),
                razao_social=f"Empresa {i + 1} Ltda",
                cnpj=f"{i:014d}",
                nome=f"Contato {i + 1}",
                whatsapp=f"11999{i:06d}",
                observacoes=obs,
                status="Ativo" if i % 2 == 0 else "Inativo",
                ultima_alteracao=now[:10],
                raw={"id": i + 1},
            )
        )

    # Criar janela e treeview
    root = tb.Window(themename="flatly")
    root.withdraw()

    container = tk.Frame(root)
    container.pack(expand=True, fill="both")

    tree = create_clients_treeview(
        container,
        on_double_click=None,
        on_select=None,
        on_delete=None,
        on_click=None,
    )
    tree.pack(expand=True, fill="both")
    root.update_idletasks()

    # Medir render
    t0 = time.perf_counter()
    for idx, row in enumerate(rows):
        zebra_tag = "even" if idx % 2 == 0 else "odd"
        base_tags = build_row_tags(row)
        tags = base_tags + (zebra_tag,)
        values = (
            row.id,
            row.razao_social,
            row.cnpj,
            row.nome,
            row.whatsapp,
            row.observacoes,
            row.status,
            row.ultima_alteracao,
        )
        tree.insert("", "end", values=values, tags=tags)
    render_time = time.perf_counter() - t0

    # Cleanup
    try:
        container.destroy()
        root.destroy()
    except Exception:
        pass

    # Avaliar
    passed = render_time <= RENDER_LIMIT_5K
    if passed:
        _log_ok(f"Render {n_rows} linhas em {render_time:.3f}s (limite: {RENDER_LIMIT_5K}s)")
    else:
        _log_error(f"Render {n_rows} linhas em {render_time:.3f}s excedeu limite de {RENDER_LIMIT_5K}s")

    return passed


def run_stress_test(n_cycles: int = STRESS_CYCLES, n_rows: int = 1000) -> bool:
    """Executa stress test. Retorna True se passou."""
    print(f"\n[STRESS] Testando {n_cycles} ciclos de criar/destruir ({n_rows} rows cada)...")

    try:
        import ttkbootstrap as tb
        from src.modules.clientes.viewmodel import ClienteRow
        from src.modules.clientes.controllers.rendering_adapter import build_row_tags
        from src.ui.components.lists import create_clients_treeview
    except ImportError as e:
        _log_error(f"Import falhou: {e}")
        return False

    # Gerar dados mock (reutilizados em todos os ciclos)
    from datetime import datetime

    now = datetime.now().isoformat()
    rows: list[ClienteRow] = []
    for i in range(n_rows):
        rows.append(
            ClienteRow(
                id=str(i + 1),
                razao_social=f"Empresa {i + 1}",
                cnpj=f"{i:014d}",
                nome=f"Contato {i + 1}",
                whatsapp="",
                observacoes="",
                status="Ativo",
                ultima_alteracao=now[:10],
                raw={"id": i + 1},
            )
        )

    tracemalloc.start()
    initial_mem = tracemalloc.get_traced_memory()[0]
    gc.collect()

    # Janela raiz única (evita bug do ttkbootstrap)
    root = tb.Window(themename="flatly")
    root.withdraw()

    for i in range(n_cycles):
        container = tk.Frame(root)
        container.pack(expand=True, fill="both")

        tree = create_clients_treeview(
            container,
            on_double_click=None,
            on_select=None,
            on_delete=None,
            on_click=None,
        )
        tree.pack(expand=True, fill="both")

        # Renderizar
        for idx, row in enumerate(rows):
            zebra_tag = "even" if idx % 2 == 0 else "odd"
            base_tags = build_row_tags(row)
            tags = base_tags + (zebra_tag,)
            tree.insert("", "end", values=(row.id, row.razao_social), tags=tags)

        root.update_idletasks()

        # Limpar
        children = tree.get_children()
        if children:
            tree.delete(*children)
        try:
            container.destroy()
        except Exception:
            pass

    # Cleanup final
    # Nota: mensagens "can't invoke event" do ttkbootstrap são noise interno
    # do framework (bug ao destruir janela após chamar Style múltiplas vezes)
    # e não afetam a funcionalidade - podem ser ignoradas.
    try:
        root.destroy()
    except Exception:
        pass

    gc.collect()
    final_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    delta_mb = (final_mem - initial_mem) / (1024 * 1024)

    # Avaliar
    passed = delta_mb <= STRESS_MEMORY_LIMIT_MB
    if passed:
        _log_ok(f"Stress delta: {delta_mb:.2f}MB (limite: {STRESS_MEMORY_LIMIT_MB}MB)")
    else:
        _log_error(f"Stress delta: {delta_mb:.2f}MB excedeu limite de {STRESS_MEMORY_LIMIT_MB}MB")

    return passed


def main() -> int:
    """Entry point. Retorna exit code."""
    parser = argparse.ArgumentParser(description="Quickcheck do módulo de clientes")
    parser.add_argument("--stress", action="store_true", help="Incluir stress test")
    args = parser.parse_args()

    print("=" * 60)
    print("CLIENTS QUICKCHECK")
    print("=" * 60)

    all_passed = True

    try:
        # Sempre roda perf
        if not run_perf_test(5000):
            all_passed = False

        # Stress opcional
        if args.stress:
            if not run_stress_test():
                all_passed = False

    except Exception as e:
        _log_error(f"Exceção não tratada: {e}")
        import traceback

        traceback.print_exc()
        return 2

    # Resumo
    print("\n" + "=" * 60)
    if all_passed:
        print("RESULTADO: ✓ PASS")
        return 0
    else:
        print("RESULTADO: ✗ FAIL")
        print("\nErros encontrados:")
        for err in _errors:
            print(f"  - {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
