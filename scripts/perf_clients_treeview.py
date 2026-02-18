#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Performance smoke test para Treeview de clientes.

Uso:
    python scripts/perf_clients_treeview.py [N_ROWS]
    python scripts/perf_clients_treeview.py 2000
    python scripts/perf_clients_treeview.py 5000
    python scripts/perf_clients_treeview.py --stress  # Stress test: 50 ciclos de abertura/fechamento

Mede: render inicial, refresh parcial, limpeza. Não depende de banco real.
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
import tkinter as tk
import tracemalloc
from datetime import datetime
from typing import Any, Sequence

# Adiciona raiz do projeto ao path
sys.path.insert(0, str(__file__).rsplit("scripts", 1)[0].rstrip("\\/"))

import ttkbootstrap as tb  # noqa: E402

from src.modules.clientes.core.viewmodel import ClienteRow  # noqa: E402
from src.modules.clientes.controllers.rendering_adapter import build_row_tags  # noqa: E402
from src.ui.components.lists import create_clients_treeview  # noqa: E402


def generate_fake_rows(n: int) -> list[ClienteRow]:
    """Gera N clientes fake para teste."""
    rows: list[ClienteRow] = []
    now = datetime.now().isoformat()

    for i in range(n):
        obs = "[ATIVO] Observação de teste" if i % 3 == 0 else ""
        status = "Ativo" if i % 2 == 0 else "Inativo"
        raw = {
            "id": i + 1,
            "razao_social": f"Empresa Teste {i + 1} Ltda",
            "cnpj": f"{i:014d}",
            "nome": f"Contato {i + 1}",
            "whatsapp": f"11999{i:06d}",
            "observacoes": obs,
            "status": status,
            "updated_at": now,
        }
        row = ClienteRow(
            id=str(i + 1),
            razao_social=f"Empresa Teste {i + 1} Ltda",
            cnpj=f"{i:014d}",
            nome=f"Contato {i + 1}",
            whatsapp=f"11999{i:06d}",
            observacoes=obs,
            status=status,
            ultima_alteracao=now[:10],
            raw=raw,
        )
        rows.append(row)
    return rows


def render_rows(tree: tb.Treeview, rows: Sequence[ClienteRow]) -> None:
    """Simula _render_clientes (delete all + insert all)."""
    children = tree.get_children()
    if children:
        tree.delete(*children)

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


def refresh_rows_partial(tree: tb.Treeview, rows: Sequence[ClienteRow], n_changes: int = 50) -> None:
    """Simula _refresh_rows com N mudanças (update in-place)."""
    items = list(tree.get_children())
    if len(items) != len(rows):
        # Fallback: re-render completo
        render_rows(tree, rows)
        return

    # Atualiza apenas os primeiros n_changes
    for idx in range(min(n_changes, len(items))):
        item_id = items[idx]
        row = rows[idx]
        zebra_tag = "even" if idx % 2 == 0 else "odd"
        base_tags = build_row_tags(row)
        tags = base_tags + (zebra_tag,)
        values = (
            row.id,
            row.razao_social + " (updated)",  # Simula mudança
            row.cnpj,
            row.nome,
            row.whatsapp,
            row.observacoes,
            row.status,
            row.ultima_alteracao,
        )
        tree.item(item_id, values=values, tags=tags)


def measure(label: str, func: Any, *args: Any) -> float:
    """Mede tempo de execução de func(*args) e imprime."""
    t0 = time.perf_counter()
    func(*args)
    elapsed = time.perf_counter() - t0
    print(f"  {label}: {elapsed:.3f}s")
    return elapsed


class PerfTestRunner:
    """Runner de testes de performance usando uma única instância Tk."""

    def __init__(self) -> None:
        self._root: tb.Window | None = None
        self._results: list[dict[str, Any]] = []

    def _ensure_root(self) -> tb.Window:
        """Cria ou retorna a janela raiz."""
        if self._root is None or not self._safe_winfo_exists(self._root):
            self._root = tb.Window(themename="flatly")
            self._root.title("Perf Test")
            self._root.geometry("1200x600")
            self._root.withdraw()  # Esconde inicialmente
        return self._root

    def _safe_winfo_exists(self, widget: tk.Misc) -> bool:
        """Verifica se widget existe sem lançar exceção."""
        try:
            return widget.winfo_exists()
        except Exception:
            return False

    def run_single_test(self, n_rows: int, visible: bool = False) -> dict[str, float]:
        """Executa teste com N linhas, retorna métricas."""
        root = self._ensure_root()

        print(f"\n{'=' * 60}")
        print(f"Performance Test: {n_rows} linhas")
        print("=" * 60)

        if visible:
            root.deiconify()
        else:
            root.withdraw()

        # Limpar filhos anteriores
        for child in root.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass

        # Criar frame container
        container = tk.Frame(root)
        container.pack(expand=True, fill="both", padx=10, pady=10)

        # Criar Treeview
        tree = create_clients_treeview(
            container,
            on_double_click=None,
            on_select=None,
            on_delete=None,
            on_click=None,
        )
        tree.pack(expand=True, fill="both")

        # Gerar dados mock
        print("\nGerando dados mock...")
        t0 = time.perf_counter()
        rows = generate_fake_rows(n_rows)
        gen_time = time.perf_counter() - t0
        print(f"  Geração de {n_rows} rows: {gen_time:.3f}s")

        # Processar eventos pendentes
        root.update_idletasks()

        # Teste 1: Render inicial
        print("\nTeste 1: Render inicial (delete all + insert all)")
        render_time = measure("Render", render_rows, tree, rows)
        root.update()

        # Teste 2: Refresh parcial (50 mudanças)
        print("\nTeste 2: Refresh parcial (50 mudanças in-place)")
        refresh_time = measure("Refresh", refresh_rows_partial, tree, rows, 50)
        root.update()

        # Teste 3: Re-render completo
        print("\nTeste 3: Re-render completo")
        rerender_time = measure("Re-render", render_rows, tree, rows)
        root.update()

        # Teste 4: Limpar tudo
        print("\nTeste 4: Limpar Treeview")
        t0 = time.perf_counter()
        children = tree.get_children()
        if children:
            tree.delete(*children)
        clear_time = time.perf_counter() - t0
        print(f"  Clear: {clear_time:.3f}s")

        # Cleanup do container
        try:
            container.destroy()
        except Exception:
            pass

        # Resumo
        results = {
            "n_rows": n_rows,
            "render": render_time,
            "refresh": refresh_time,
            "rerender": rerender_time,
            "clear": clear_time,
        }

        print(f"\n{'=' * 60}")
        print("RESUMO:")
        print(f"  Render inicial:   {render_time:.3f}s")
        print(f"  Refresh parcial:  {refresh_time:.3f}s")
        print(f"  Re-render:        {rerender_time:.3f}s")
        print(f"  Clear:            {clear_time:.3f}s")

        # Critérios de aceite
        print(f"\nCRITÉRIOS (n={n_rows}):")
        render_ok = render_time < 3.0  # < 3s para render inicial
        refresh_ok = refresh_time < 0.5  # < 500ms para refresh parcial
        print(f"  Render < 3s: {'✓ PASS' if render_ok else '✗ FAIL'}")
        print(f"  Refresh < 0.5s: {'✓ PASS' if refresh_ok else '✗ FAIL'}")

        self._results.append(results)
        return results

    def run_stress_test(self, n_cycles: int = 50, n_rows: int = 1000) -> None:
        """Stress test: cria/destrói frames N vezes, monitora memória.

        Usa uma única janela raiz para evitar bugs do ttkbootstrap
        relacionados a ttk::ThemeChanged ao destruir janelas.
        """
        print(f"\n{'#' * 60}")
        print(f"STRESS TEST: {n_cycles} ciclos, {n_rows} rows cada")
        print("#" * 60)

        tracemalloc.start()
        initial_mem = tracemalloc.get_traced_memory()[0]

        # Limpar referências
        gc.collect()

        # Usar uma única janela raiz (evita bug do ttkbootstrap com múltiplas janelas)
        root = tb.Window(themename="flatly")
        root.title("Stress Test")
        root.geometry("800x400")
        root.withdraw()  # Não mostrar

        for i in range(n_cycles):
            # Criar container e treeview (simula abertura de tela de clientes)
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

            # Gerar e renderizar
            rows = generate_fake_rows(n_rows)
            render_rows(tree, rows)
            root.update_idletasks()

            # Limpar
            children = tree.get_children()
            if children:
                tree.delete(*children)

            # Destruir container (simula fechamento de tela de clientes)
            try:
                container.destroy()
            except Exception:
                pass

            # Coletar lixo e verificar memória a cada 10 ciclos
            if (i + 1) % 10 == 0:
                gc.collect()
                current_mem = tracemalloc.get_traced_memory()[0]
                delta_mb = (current_mem - initial_mem) / (1024 * 1024)
                print(f"  Ciclo {i + 1:3d}: memória delta = {delta_mb:+.2f} MB")

        # Destruir janela raiz após todos os ciclos
        try:
            root.destroy()
        except Exception:
            pass

        # Resultado final
        gc.collect()
        final_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        delta_mb = (final_mem - initial_mem) / (1024 * 1024)
        peak_mb = peak_mem / (1024 * 1024)

        print(f"\n{'=' * 60}")
        print("RESULTADO STRESS TEST:")
        print(f"  Ciclos completados: {n_cycles}")
        print(f"  Memória inicial:    {initial_mem / (1024 * 1024):.2f} MB")
        print(f"  Memória final:      {final_mem / (1024 * 1024):.2f} MB")
        print(f"  Delta:              {delta_mb:+.2f} MB")
        print(f"  Pico:               {peak_mb:.2f} MB")

        # Critério: delta < 10MB após GC
        leak_ok = delta_mb < 10.0
        print(f"\nLeak < 10MB: {'✓ PASS' if leak_ok else '✗ FAIL (possível leak)'}")

    def cleanup(self) -> None:
        """Destrói a janela raiz."""
        if self._root is not None:
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Performance test para Treeview de clientes")
    parser.add_argument("n_rows", nargs="?", type=int, default=2000, help="Número de linhas para teste")
    parser.add_argument("--stress", action="store_true", help="Executar stress test (50 ciclos)")
    parser.add_argument("--stress-cycles", type=int, default=50, help="Número de ciclos para stress test")
    args = parser.parse_args()

    runner = PerfTestRunner()

    try:
        if args.stress:
            runner.run_stress_test(n_cycles=args.stress_cycles, n_rows=args.n_rows)
        else:
            runner.run_single_test(args.n_rows)

            # Rodar também com 5000 se pedido 2000 (teste duplo)
            if args.n_rows == 2000:
                runner.run_single_test(5000)
    finally:
        runner.cleanup()


if __name__ == "__main__":
    main()
