"""Testes unitários para utilitários de PDF Preview (src/modules/pdf_preview/utils.py)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from src.modules.pdf_preview.utils import LRUCache, pixmap_to_photoimage


class TestLRUCache:
    """Testes para a classe LRUCache."""

    def test_basic_set_and_get(self):
        """Testa operações básicas de put() e get()."""
        cache = LRUCache(capacity=3)

        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)

        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_get_returns_none_for_missing_key(self):
        """Testa que get() retorna None para chave inexistente."""
        cache = LRUCache(capacity=2)

        cache.put("a", 1)

        assert cache.get("missing") is None

    def test_evicts_least_recently_used(self):
        """Testa que o cache evita o item menos recentemente usado quando atinge capacidade."""
        cache = LRUCache(capacity=2)

        cache.put("a", 1)
        cache.put("b", 2)

        # Acessa "a" para torná-lo recente
        _ = cache.get("a")

        # Adiciona "c" - deve eviccionar "b" (LRU)
        cache.put("c", 3)

        assert cache.get("a") == 1  # Ainda existe
        assert cache.get("c") == 3  # Recém adicionado
        assert cache.get("b") is None  # Foi eviccionado

    def test_updating_existing_key_moves_to_end(self):
        """Testa que atualizar chave existente a move para o final (mais recente)."""
        cache = LRUCache(capacity=2)

        cache.put("a", 1)
        cache.put("b", 2)

        # Atualiza "a"
        cache.put("a", 10)

        # Adiciona "c" - deve eviccionar "b" (LRU)
        cache.put("c", 3)

        assert cache.get("a") == 10  # Atualizado e ainda presente
        assert cache.get("c") == 3
        assert cache.get("b") is None  # Foi eviccionado

    def test_clear_removes_all_entries(self):
        """Testa que clear() remove todas as entradas do cache."""
        cache = LRUCache(capacity=3)

        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)

        cache.clear()

        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.get("c") is None

    def test_capacity_enforcement(self):
        """Testa que o cache nunca excede sua capacidade."""
        cache = LRUCache(capacity=3)

        # Adiciona 5 itens
        for i in range(5):
            cache.put(f"key{i}", i)

        # Verifica que apenas os 3 mais recentes estão presentes
        assert cache.get("key4") == 4  # Mais recente
        assert cache.get("key3") == 3
        assert cache.get("key2") == 2
        assert cache.get("key1") is None  # Eviccionado
        assert cache.get("key0") is None  # Eviccionado

    def test_get_with_default_value(self):
        """Testa comportamento quando chave não existe (retorna None por padrão)."""
        cache = LRUCache(capacity=2)

        cache.put("exists", "value")

        # get() sem chave retorna None
        result = cache.get("missing")
        assert result is None

    def test_zero_capacity_cache(self):
        """Testa comportamento de cache com capacidade zero."""
        cache = LRUCache(capacity=0)

        cache.put("a", 1)

        # Com capacidade 0, nada deve ser armazenado
        assert cache.get("a") is None

    def test_single_capacity_cache(self):
        """Testa cache com capacidade de apenas 1 item."""
        cache = LRUCache(capacity=1)

        cache.put("a", 1)
        assert cache.get("a") == 1

        cache.put("b", 2)
        assert cache.get("b") == 2
        assert cache.get("a") is None  # Eviccionado


class TestPixmapToPhotoImage:
    """Testes para a função pixmap_to_photoimage."""

    def test_returns_none_when_pixmap_is_none(self):
        """Testa que retorna None quando pixmap é None."""
        result = pixmap_to_photoimage(None)
        assert result is None

    @patch("src.modules.pdf_preview.utils.Image")
    @patch("src.modules.pdf_preview.utils.ImageTk")
    def test_converts_rgb_pixmap_with_pil(self, mock_imagetk, mock_image):
        """Testa conversão de pixmap RGB quando PIL está disponível."""
        # Mock do pixmap
        mock_pixmap = MagicMock()
        mock_pixmap.n = 3  # RGB (menos que 4 canais)
        mock_pixmap.width = 100
        mock_pixmap.height = 200
        mock_pixmap.samples = b"fake_image_data"

        # Mock da imagem PIL
        mock_pil_image = MagicMock()
        mock_image.frombytes.return_value = mock_pil_image

        # Mock do PhotoImage
        mock_photo = MagicMock()
        mock_imagetk.PhotoImage.return_value = mock_photo

        result = pixmap_to_photoimage(mock_pixmap)

        # Verifica que Image.frombytes foi chamado com parâmetros corretos
        mock_image.frombytes.assert_called_once_with("RGB", (100, 200), b"fake_image_data")

        # Verifica que ImageTk.PhotoImage foi chamado
        mock_imagetk.PhotoImage.assert_called_once_with(mock_pil_image)

        # Resultado deve ser o PhotoImage mockado
        assert result == mock_photo

    @patch("src.modules.pdf_preview.utils.Image")
    @patch("src.modules.pdf_preview.utils.ImageTk")
    def test_converts_rgba_pixmap_with_pil(self, mock_imagetk, mock_image):
        """Testa conversão de pixmap RGBA quando PIL está disponível."""
        # Mock do pixmap com alpha
        mock_pixmap = MagicMock()
        mock_pixmap.n = 4  # RGBA (4 canais)
        mock_pixmap.width = 100
        mock_pixmap.height = 200
        mock_pixmap.samples = b"fake_rgba_data"

        mock_pil_image = MagicMock()
        mock_image.frombytes.return_value = mock_pil_image

        mock_photo = MagicMock()
        mock_imagetk.PhotoImage.return_value = mock_photo

        result = pixmap_to_photoimage(mock_pixmap)

        # Deve usar modo RGBA
        mock_image.frombytes.assert_called_once_with("RGBA", (100, 200), b"fake_rgba_data")

        assert result == mock_photo

    @patch("src.modules.pdf_preview.utils.Image", None)
    @patch("src.modules.pdf_preview.utils.ImageTk", None)
    @patch("src.modules.pdf_preview.utils.tk.PhotoImage")
    def test_fallback_to_ppm_when_pil_unavailable(self, mock_photoimage):
        """Testa fallback para formato PPM quando PIL não está disponível."""
        # Mock do pixmap
        mock_pixmap = MagicMock()
        mock_pixmap.tobytes.return_value = b"ppm_data"

        mock_photo = MagicMock()
        mock_photoimage.return_value = mock_photo

        result = pixmap_to_photoimage(mock_pixmap)

        # Deve usar tobytes("ppm")
        mock_pixmap.tobytes.assert_called_once_with("ppm")

        # Deve criar tk.PhotoImage com dados PPM
        mock_photoimage.assert_called_once_with(data=b"ppm_data")

        assert result == mock_photo

    def test_returns_none_on_exception(self):
        """Testa que retorna None quando ocorre exceção durante conversão."""
        # Mock de pixmap que levanta exceção
        mock_pixmap = MagicMock()
        mock_pixmap.n = 3
        mock_pixmap.width = 100
        mock_pixmap.height = 200
        # Forçar exceção ao acessar samples
        type(mock_pixmap).samples = property(lambda self: (_ for _ in ()).throw(RuntimeError("Test error")))

        result = pixmap_to_photoimage(mock_pixmap)

        # Deve retornar None em caso de erro
        assert result is None
