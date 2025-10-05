from __future__ import annotations
import os
import shutil
import logging
from typing import Iterable, Tuple, Optional, Literal
from config.paths import DOCS_DIR
from core import db_manager
from utils.file_utils import ensure_subpastas, write_marker
from .path_resolver import resolve_cliente_path, resolve_unique_path, TRASH_DIR

logger = logging.getLogger(__name__)

def _unique_dest(base_dir: str, name: str) -> str:
    dst = os.path.join(base_dir, name)
    if not os.path.exists(dst):
        return dst
    root, ext = os.path.splitext(name)
    k = 1
    while True:
        cand = os.path.join(base_dir, f"{root}_{k}{ext}")
        if not os.path.exists(cand):
            return cand
        k += 1

def _merge_folders(src: str, dst: str) -> tuple[int, int]:
    if not os.path.isdir(src):
        return (0, 0)
    os.makedirs(dst, exist_ok=True)
    moved = failed = 0
    for name in os.listdir(src):
        s = os.path.join(src, name)
        d = os.path.join(dst, name)
        try:
            if os.path.isdir(s):
                m2, f2 = _merge_folders(s, d)
                moved += m2
                failed += f2
                try:
                    if not os.listdir(s):
                        os.rmdir(s)
                except Exception as e:
                    logger.warning("Lixeira: erro ignorado: %s", e)
            else:
                if os.path.exists(d):
                    root, ext = os.path.splitext(name)
                    k = 1
                    nd = os.path.join(dst, f"{root}_{k}{ext}")
                    while os.path.exists(nd):
                        k += 1
                        nd = os.path.join(dst, f"{root}_{k}{ext}")
                    shutil.move(s, nd)
                else:
                    shutil.move(s, d)
                moved += 1
        except Exception:
            logger.exception("merge fail: %s -> %s", s, d)
            failed += 1
    try:
        if not os.listdir(src):
            os.rmdir(src)
    except Exception as e:
        logger.warning("Lixeira: erro ignorado: %s", e)
    return (moved, failed)

def trash_find_folder_by_pk(pk: int) -> str | None:
    # marker-based detection in the trash, independent of folder name
    path, loc = resolve_unique_path(int(pk), prefer="trash")
    return path

def enviar_para_lixeira(ids: Iterable[int]) -> tuple[list[int], list[int]]:
    """
    Move clientes para a Lixeira.
    Regras:
      - Só aplica soft delete no BD após mover a pasta com sucesso.
      - Se não encontrar a pasta ativa (nem por marker), registra em 'falhas' e NÃO altera o BD.
    """
    ok_list: list[int] = []
    falhas: list[int] = []
    os.makedirs(TRASH_DIR, exist_ok=True)

    for raw_pk in ids:
        pk = int(raw_pk)

        # Pre-flight: resolver caminho ativo por marker/slug
        active_path, loc = resolve_unique_path(pk, prefer="active")
        if not active_path or not os.path.isdir(active_path):
            # não cria pasta vazia na lixeira; sinaliza falha para feedback e possível rollback
            logger.warning("Lixeira: pasta ativa não encontrada para PK=%s", pk)
            falhas.append(pk)
            continue

        # Nome de destino preserva o basename atual
        base_name = os.path.basename(active_path)
        dest = _unique_dest(TRASH_DIR, base_name)

        try:
            # Move físico
            shutil.move(active_path, dest)
            # Pós-move: garantir estrutura e marcador
            try:
                ensure_subpastas(dest)
                write_marker(dest, pk)
            except Exception:
                logger.exception("Falha ao garantir subpastas/escrever marcador na Lixeira para PK=%s", pk)

            # BD somente após sucesso do move
            db_manager.soft_delete_clientes([pk])
            ok_list.append(pk)
            logger.info("Lixeira: movido PK=%s %s -> %s", pk, active_path, dest)
        except Exception:
            logger.exception("Falha no enviar_para_lixeira PK=%s", pk)
            falhas.append(pk)
            # Nenhuma mutação no BD em caso de falha

    return ok_list, falhas

def restore_ids(ids: Iterable[int]) -> tuple[int, int, int]:
    """
    Restaura clientes da Lixeira.
    Regras:
      - Trabalha por marker (independe do nome do diretório).
      - NÃO reativa no BD antes da operação de arquivo.
      - Coleta as falhas e só chama restore_clientes() para os que moveram com sucesso.
      - Não cria pasta ativa vazia quando a pasta na Lixeira não existe; isso vira 'falha'.
    Retorna: (ok_db, processadas, falhas)
    """
    success_ids: list[int] = []
    falha_ids: list[int] = []
    processadas = 0

    for raw_pk in ids:
        pk = int(raw_pk)

        # Localizar na lixeira
        trash_path, loc = resolve_unique_path(pk, prefer="trash")
        if not trash_path or not os.path.isdir(trash_path):
            logger.warning("Restore: pasta na Lixeira não encontrada para PK=%s", pk)
            falha_ids.append(pk)
            processadas += 1
            continue

        # Determinar destino ativo
        r = resolve_cliente_path(pk)
        # se já existe ativa (ex.: resíduo de operação anterior), vamos mesclar
        dst_active = r.active or _unique_dest(DOCS_DIR, os.path.basename(trash_path))

        try:
            if r.active and os.path.abspath(dst_active) != os.path.abspath(trash_path):
                _merge_folders(trash_path, dst_active)
                # remove a pasta da lixeira se ficar vazia
                try:
                    if os.path.isdir(trash_path) and not os.listdir(trash_path):
                        os.rmdir(trash_path)
                except Exception as e:
                    logger.warning("Lixeira: erro ignorado: %s", e)
            else:
                shutil.move(trash_path, dst_active)

            # Pós-move: garantir estrutura e marker
            try:
                ensure_subpastas(dst_active)
                write_marker(dst_active, pk)
            except Exception:
                logger.exception("Falha ao garantir subpastas/escrever marcador no Ativo para PK=%s", pk)

            success_ids.append(pk)
            processadas += 1
            logger.info("Restore: movido PK=%s %s -> %s", pk, trash_path, dst_active)
        except Exception:
            logger.exception("Falha ao restaurar PK=%s", pk)
            falha_ids.append(pk)
            processadas += 1
            # Não altera BD em caso de falha

    ok_db = 0
    if success_ids:
        try:
            db_manager.restore_clientes(success_ids)
            ok_db = len(success_ids)
        except Exception:
            logger.exception("Falha no restore_clientes para IDs=%s", success_ids)

    return ok_db, processadas, len(falha_ids)

import time

def purge_ids(ids: Iterable[int]) -> tuple[int, int]:
    started = time.perf_counter()
    ok_db = removidas = 0
    ids = list(map(int, ids))
    logger.info("Purge iniciar: %d id(s) -> %s", len(ids), ids)
    for pk in ids:
        r = resolve_cliente_path(pk)
        trash_path = r.trash
        if trash_path and os.path.isdir(trash_path):
            try:
                shutil.rmtree(trash_path, ignore_errors=False)
                removidas += 1
                logger.info("Purge: pasta removida PK=%s (%s)", pk, trash_path)
            except Exception:
                logger.exception("Falha ao remover definitivamente PK=%s", pk)
        try:
            db_manager.purge_clientes([pk])
            ok_db += 1
            logger.info("Purge: removido do banco PK=%s", pk)
        except Exception:
            logger.exception("Falha no purge_clientes para PK=%s", pk)
    logger.info("Purge fim: ok_db=%s, pastas=%s, tempo=%.3fs", ok_db, removidas, time.perf_counter()-started)
    return ok_db, removidas
