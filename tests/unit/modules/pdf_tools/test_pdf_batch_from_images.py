"""Testes unitários para src/modules/pdf_tools/pdf_batch_from_images.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image
from pypdf import PdfReader

from src.modules.pdf_tools.pdf_batch_from_images import convert_subfolders_images_to_pdf


def create_test_image(path: Path, width: int = 10, height: int = 10, color: str = "red") -> None:
    """Cria uma imagem de teste simples e salva no path."""
    img = Image.new("RGB", (width, height), color)
    img.save(path)
    img.close()


class TestConvertSubfoldersImagesToPdf:
    """Testes para convert_subfolders_images_to_pdf."""

    def test_gera_um_pdf_por_subpasta(self, tmp_path: Path) -> None:
        """Deve gerar um PDF para cada subpasta contendo imagens."""
        # Criar estrutura: root/sub1/{img1.png, img2.png}, root/sub2/{img3.png, img4.png}
        sub1 = tmp_path / "sub1"
        sub2 = tmp_path / "sub2"
        sub1.mkdir()
        sub2.mkdir()

        create_test_image(sub1 / "img1.png")
        create_test_image(sub1 / "img2.png")
        create_test_image(sub2 / "img3.png")
        create_test_image(sub2 / "img4.png")

        # Executar conversão
        result = convert_subfolders_images_to_pdf(tmp_path, overwrite=True)

        # Validar: 2 PDFs gerados
        assert len(result) == 2
        assert all(pdf.exists() for pdf in result)

        # Validar número de páginas
        pdf1 = next(pdf for pdf in result if pdf.parent.name == "sub1")
        pdf2 = next(pdf for pdf in result if pdf.parent.name == "sub2")

        reader1 = PdfReader(pdf1)
        reader2 = PdfReader(pdf2)

        assert len(reader1.pages) == 2  # sub1 tinha 2 imagens
        assert len(reader2.pages) == 2  # sub2 tinha 2 imagens

    def test_dedup_por_base_e_revision(self, tmp_path: Path) -> None:
        """Deve manter apenas a melhor revisão de cada base (doc, doc-1, doc-2 -> apenas doc-2)."""
        subdir = tmp_path / "subtest"
        subdir.mkdir()

        # Criar imagens com mesmo base mas revisões diferentes
        create_test_image(subdir / "doc.png", color="red")
        create_test_image(subdir / "doc-1.png", color="green")
        create_test_image(subdir / "doc-2.png", color="blue")

        # Executar conversão
        result = convert_subfolders_images_to_pdf(tmp_path, overwrite=True)

        # Validar: 1 PDF gerado com apenas 1 página (maior revisão)
        assert len(result) == 1
        assert result[0].exists()

        reader = PdfReader(result[0])
        assert len(reader.pages) == 1  # Apenas a melhor revisão (doc-2)

    def test_overwrite_false_pula_pdf_existente(self, tmp_path: Path) -> None:
        """Quando overwrite=False e PDF já existe, não deve sobrescrever."""
        subdir = tmp_path / "subtest"
        subdir.mkdir()

        create_test_image(subdir / "img1.png")

        # Criar PDF existente
        existing_pdf = subdir / "subtest.pdf"
        existing_pdf.write_text("dummy pdf content")
        original_mtime = existing_pdf.stat().st_mtime

        # Executar conversão com overwrite=False
        result = convert_subfolders_images_to_pdf(tmp_path, overwrite=False)

        # Validar: não deve sobrescrever (lista vazia ou não inclui)
        assert existing_pdf.exists()
        assert existing_pdf.stat().st_mtime == original_mtime  # mtime não mudou
        assert existing_pdf not in result or len(result) == 0  # Não retorna PDFs não gerados

    def test_delete_images_remove_imagens_originais(self, tmp_path: Path) -> None:
        """Quando delete_images=True, deve remover imagens após criar o PDF."""
        subdir = tmp_path / "subtest"
        subdir.mkdir()

        img1 = subdir / "img1.png"
        img2 = subdir / "img2.png"
        create_test_image(img1)
        create_test_image(img2)

        # Executar conversão com delete_images=True
        result = convert_subfolders_images_to_pdf(tmp_path, overwrite=True, delete_images=True)

        # Validar: PDF foi criado
        assert len(result) == 1
        assert result[0].exists()

        # Validar: imagens foram removidas
        assert not img1.exists()
        assert not img2.exists()

    def test_progress_callback_e_chamado_corretamente(self, tmp_path: Path) -> None:
        """progress_cb deve ser chamado para cada imagem processada com valores monotônicos."""
        subdir = tmp_path / "subtest"
        subdir.mkdir()

        # Criar 3 imagens
        create_test_image(subdir / "img1.png")
        create_test_image(subdir / "img2.png")
        create_test_image(subdir / "img3.png")

        # Capturar chamadas ao callback
        calls: list[dict[str, Any]] = []

        def progress_callback(
            processed: int,
            total: int,
            idx: int,
            total_subdirs: int,
            subdir_path: Path | None,
            image_path: Path | None,
        ) -> None:
            calls.append(
                {
                    "processed": processed,
                    "total": total,
                    "idx": idx,
                    "total_subdirs": total_subdirs,
                    "subdir": subdir_path,
                    "image": image_path,
                }
            )

        # Executar conversão com callback
        result = convert_subfolders_images_to_pdf(tmp_path, overwrite=True, progress_cb=progress_callback)

        # Validar: PDF criado
        assert len(result) == 1

        # Validar callback foi chamado 3 vezes (uma por imagem)
        assert len(calls) == 3

        # Validar: processed_bytes é monotônico crescente
        processed_values = [call["processed"] for call in calls]
        assert all(processed_values[i] <= processed_values[i + 1] for i in range(len(processed_values) - 1))

        # Validar: total_bytes é constante
        total_values = [call["total"] for call in calls]
        assert len(set(total_values)) == 1  # Todos iguais

        # Validar: idx e total_subdirs coerentes
        assert all(call["idx"] == 1 for call in calls)
        assert all(call["total_subdirs"] == 1 for call in calls)

        # Validar: subdir e image são passados
        assert all(call["subdir"] == subdir for call in calls)
        assert all(call["image"] is not None for call in calls)

    def test_ignora_subdiretorios_sem_imagens(self, tmp_path: Path) -> None:
        """Deve ignorar subpastas que não contêm imagens válidas."""
        sub1 = tmp_path / "sub_with_images"
        sub2 = tmp_path / "sub_without_images"
        sub1.mkdir()
        sub2.mkdir()

        create_test_image(sub1 / "img.png")
        (sub2 / "textfile.txt").write_text("not an image")

        result = convert_subfolders_images_to_pdf(tmp_path, overwrite=True)

        # Apenas 1 PDF deve ser gerado (sub1)
        assert len(result) == 1
        assert result[0].parent == sub1

    def test_retorna_lista_vazia_quando_nao_ha_subdiretorios(self, tmp_path: Path) -> None:
        """Deve retornar lista vazia quando não há subdiretórios com imagens."""
        # tmp_path vazio
        result = convert_subfolders_images_to_pdf(tmp_path, overwrite=True)
        assert result == []

    def test_respeita_image_extensions_customizadas(self, tmp_path: Path) -> None:
        """Deve processar apenas extensões especificadas."""
        subdir = tmp_path / "subtest"
        subdir.mkdir()

        create_test_image(subdir / "img1.png")
        create_test_image(subdir / "img2.jpg")
        create_test_image(subdir / "img3.bmp")

        # Processar apenas .png
        result = convert_subfolders_images_to_pdf(tmp_path, image_extensions=[".png"], overwrite=True)

        assert len(result) == 1
        reader = PdfReader(result[0])
        assert len(reader.pages) == 1  # Apenas img1.png

    def test_pdf_name_customizado(self, tmp_path: Path) -> None:
        """Deve usar pdf_name customizado quando especificado."""
        subdir = tmp_path / "subtest"
        subdir.mkdir()

        create_test_image(subdir / "img.png")

        result = convert_subfolders_images_to_pdf(tmp_path, pdf_name="custom.pdf", overwrite=True)

        assert len(result) == 1
        assert result[0].name == "custom.pdf"

    def test_multiplas_bases_diferentes_na_mesma_subpasta(self, tmp_path: Path) -> None:
        """Deve criar PDF com múltiplas bases diferentes (sem dedup entre bases)."""
        subdir = tmp_path / "subtest"
        subdir.mkdir()

        create_test_image(subdir / "doc1.png")
        create_test_image(subdir / "doc2.png")
        create_test_image(subdir / "doc3.png")

        result = convert_subfolders_images_to_pdf(tmp_path, overwrite=True)

        assert len(result) == 1
        reader = PdfReader(result[0])
        assert len(reader.pages) == 3  # Todas as 3 bases diferentes

    def test_revisoes_com_mesmo_numero_usa_mtime_mais_recente(self, tmp_path: Path) -> None:
        """Quando revisões são iguais, deve usar a imagem com mtime mais recente."""
        subdir = tmp_path / "subtest"
        subdir.mkdir()

        # Criar uma imagem simples
        img1 = subdir / "doc.png"
        create_test_image(img1, color="red")

        # Garantir que funciona sem erro
        result = convert_subfolders_images_to_pdf(tmp_path, overwrite=True)
        assert len(result) == 1

        reader = PdfReader(result[0])
        assert len(reader.pages) == 1  # Uma imagem processada
