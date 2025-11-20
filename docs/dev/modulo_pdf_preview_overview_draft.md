# Módulo PDF Preview – Visão Inicial (draft)

## 1. Responsabilidades desejadas do módulo
- Exibir arquivos PDF (e imagens) em uma janela dedicada com zoom, navegação por páginas e rolagem fluida.
- Permitir alternar entre ajuste de largura/100%, zoom incremental e pan sem travar a UI.
- Disponibilizar download/export do arquivo original (PDF) ou da imagem renderizada, preservando nomes e pastas padrão do usuário.
- Exibir/alternar visualização de texto/OCR associado ao documento e suportar busca incremental no texto exibido.
- Oferecer atalhos e mouse-wheel para navegação/zoom e respeitar integrações com o app principal (modal, focus/close).

## 2. Situação atual (antes da modularização)
- `src/ui/pdf_preview_native.py` (~1k linhas) concentra toda a UI e a lógica de carregamento/rasterização: cria a janela `PdfViewerWin` (Tk.Toplevel), manipula zoom/scroll, renderiza páginas via PyMuPDF (fitz) e trata fallback de imagem com Pillow ou PhotoImage.
- O arquivo também cuida de OCR/texto (ScrolledText + SearchNavigator), download de PDF/imagem, bindings de teclado e wheel, cache LRU de imagens e cálculo manual de posições no canvas.
- O módulo `src/modules/pdf_preview/view.py` apenas reexporta `PdfViewerWin`/`open_pdf_viewer` para o shell principal; não há camadas intermediárias de serviço ou viewmodel.

### Arquivos inspecionados (inventário)
- `src/ui/pdf_preview_native.py`: janela principal `PdfViewerWin`, renderização de páginas via fitz, cache LRU, zoom/pan/scroll, toggles de texto, download (PDF/Imagem), atalhos de teclado e binds de mouse.
- `src/modules/pdf_preview/view.py`: shim que reexporta `PdfViewerWin`/`open_pdf_viewer` para o módulo de preview.
- `src/modules/pdf_preview/__init__.py`: expõe `PdfPreviewFrame`/`open_pdf_viewer` para o restante do app.

### Entrypoints e comandos de UI
- Entry principal: `open_pdf_viewer(...)` (reexportado por `src/modules/pdf_preview/view.py`) é chamado por clientes externos para abrir a janela como modal.
- Comandos/controles: botões de zoom (-, 100%, +), “Largura”, label de página/zoom, toggle “Texto”, downloads (PDF/Imagem), busca de texto (SearchNavigator, atalhos F3/Shift+F3), atalhos de navegação (PgUp/PgDn/Home/End, Ctrl+MouseWheel para zoom), e wheel para rolagem.
- OCR/Text: painel de texto oculto/mostrado via checkbox; carregado on-demand a partir de buffer gerado pelo fitz (quando disponível).

## 3. Acoplamentos fortes identificados
- UI mistura diretamente chamadas ao fitz (PyMuPDF) para abrir e rasterizar páginas, incluindo matrizes de zoom e extração de texto.
- Depende de Pillow para converter pixmap em PhotoImage e manter referências vivas; fallback para tk.PhotoImage ppm.
- Manipula filesystem direto: determina pasta Downloads via chamadas ctypes/WinAPI, salva PDF ou imagem manualmente, escolhe nomes exclusivos.
- Lida com bytes ou paths em `_pdf_bytes`/`_pdf_path`, cacheando páginas e imagens no mesmo arquivo gigante.
- Atalhos, binds de mouse e atualização de labels/estados estão acoplados à renderização e ao modelo de dados interno (zoom/page_count) sem camada de viewmodel/controlador.

## 4. Estrutura proposta para o módulo PDF Preview
- Criar um `PreviewViewModel/Controller` para estado (página atual, zoom, fit mode, cache de pixmaps, status de texto/OCR, fonte bytes vs path).
- Separar UI em componentes:
  - `views/toolbar.py`: botões de zoom, fit, downloads, toggle texto e labels de página/zoom.
  - `views/canvas.py` ou `views/page_view.py`: canvas com scroll, renderização de páginas/imagens/cálculo de scrollregion.
  - `views/text_panel.py`: painel de texto/OCR e navegação de busca (SearchNavigator).
  - `views/shortcuts.py` ou controller para binds de teclado/mouse.
- Infra/serviço:
  - módulo para carregar PDF/imagem, rasterizar páginas (fitz/Pillow), gerar buffers de texto/OCR e cuidar de cache/handles.
  - helper para downloads/salvar em Downloads com fallback multiplataforma.
- Mapping legado → destino:
  - `_render_page_image/_reflow_pages/_render_visible_pages` → serviço de raster + viewmodel de layout.
  - Atalhos/binds/on_wheel → controlador de input.
  - `_download_pdf/_download_img/_get_downloads_dir` → helper/infra dedicado.
  - `_toggle_text`/`_populate_ocr_text` → viewmodel + painel de texto.

## 5. Riscos e pontos de atenção
- Performance/memória em PDFs grandes: rasterização pode ser pesada; risco de travar UI se feito inline.
- Dependência de PyMuPDF e Pillow (podem não estar disponíveis); precisa de fallbacks claros.
- Salvamento e resolução de paths em Windows via ctypes pode quebrar em outros SOs; considerar abstração multiplataforma.
- Manutenção de referências de PhotoImage para evitar GC; risco de vazamento se cache não for gerenciado.
- Estado compartilhado de zoom/pan entre PDF e imagem pode ocultar bugs ao alternar modos.

## 6. Próximas etapas sugeridas
- Etapa 1: criar viewmodel/controlador de estado (página/zoom/cache) com pequenos testes unitários para cálculo de labels/zoom-fit.
- Etapa 2: extrair toolbar/footer e painel de texto para `views/` separados, preservando UX/atalhos atuais.
- Etapa 3: mover rasterização/carregamento (fitz/Pillow) para serviço/infra dedicado com fallbacks e testes de conversão básica.
- Etapa 4: encapsular downloads/salvamento (PDF/imagem) em helper multiplataforma e injetar no controller.
- Etapa 5: revisar atalhos/binds e isolar um controlador de inputs para facilitar futuras evoluções sem afetar renderização.

## Etapa 1 – Controller/ViewModel de estado (página/zoom/cache)

**Objetivo**
- Introduzir um controller/viewmodel para gerenciar o estado de
  navegação e zoom do preview (página atual, total, zoom, fit e
  cache de pixmaps), reduzindo a responsabilidade da view
  `pdf_preview_native.py`.

**Implementado nesta etapa**
- Criação de `src/modules/pdf_preview/controller.py` com a classe
  `PdfPreviewController` e o tipo `PageRenderData`, responsáveis
  por:
  - abrir o documento (bytes ou path) via PyMuPDF;
  - manter `current_page`, `page_count`, `zoom`, `fit_mode` e
    flag de texto;
  - fornecer `get_page_pixmap()` para a UI renderizar a página;
  - gerar labels de página/zoom para a toolbar.
- `src/ui/pdf_preview_native.py` passou a instanciar e usar o
  controller em vez de manipular o `fitz.Document` e o estado de
  página/zoom diretamente.
- Labels de página/zoom e os métodos de navegação/zoom da UI
  agora delegam a lógica para o controller, mantendo a UX
  inalterada.

**Próximos passos**
- Etapa 2: extrair toolbar/painel de texto e canvas principal para
  `views/toolbar.py`, `views/page_view.py` e `views/text_panel.py`,
  mantendo os atalhos e binds e reaproveitando o controller de
  estado.


## Etapa 2 ? Toolbar, PageView e TextPanel em views/

**Objetivo**
- Extrair a toolbar, o canvas principal de p?ginas e o painel de
  texto/OCR de `pdf_preview_native.py` para componentes dedicados
  em `src/modules/pdf_preview/views/`, mantendo a mesma UX e
  atalhos.

**Implementado nesta etapa**
- Cria??o de:
  - `views/toolbar.py` com `PdfToolbar` (bot?es de zoom/fit,
    labels de p?gina/zoom, toggle de texto e downloads).
  - `views/page_view.py` com `PdfPageView` (canvas + scrollbars e
    l?gica de `show_image`).
  - `views/text_panel.py` com `PdfTextPanel` (texto/OCR e
    integra??o com SearchNavigator).
- `PdfViewerWin` passou a instanciar esses componentes em vez de
  criar widgets diretamente, delegando callbacks para o
  `PdfPreviewController` e para as fun??es de download.
- Mantidos textos, atalhos e comportamento de zoom/navega??o
  inalterados.

**Pr?ximos passos**
- Etapa 3: mover rasteriza??o/carregamento (PyMuPDF/Pillow) para
  um m?dulo de servi?o/infra dedicado, reaproveitado pelo
  controller.

## Etapa 3 - Servi�o de rasteriza��o/carregamento (PyMuPDF)

**Objetivo**
- Extrair de `pdf_preview_native.py`/`PdfPreviewController` a
  l�gica de abertura de documentos e rasteriza��o de p�ginas,
  centralizando em um servi�o dedicado baseado em PyMuPDF.

**Implementado nesta etapa**
- Cria��o de `src/modules/pdf_preview/raster_service.py` com:
  - `PdfRasterService`: respons�vel por abrir o documento,
    expor `page_count`, rasterizar p�ginas via `get_page_pixmap`
    e manter um cache simples de Pixmaps.
  - `RasterResult`: tipo de dados para encapsular o resultado
    da rasteriza��o (�ndice da p�gina, zoom, Pixmap, tamanho).
- `PdfPreviewController` passou a usar `PdfRasterService` em vez
  de manipular `fitz.Document` diretamente, mantendo a API
  p�blica para a view (`get_page_pixmap`, labels, navega��o).
- `PdfViewerWin` continua recebendo apenas `PageRenderData` para
  renderizar as imagens via `PdfPageView`, sem conhecer PyMuPDF.

**Pr�ximos passos**
- Etapa 4: extrair a l�gica de download/salvamento (PDF/imagem)
  para um helper/servi�o multiplataforma, deixando o preview
  focado em visualiza��o.


## Etapa 4 - Servi?o/helper de download/salvamento

**Objetivo**
- Remover de `pdf_preview_native.py` a l?gica de salvar PDF e
  imagem, centralizando em um helper/servi?o dedicado que cuida
  de diret?rios padr?o, nomes de arquivo e escrita em disco.

**Implementado nesta etapa**
- Cria??o de `src/modules/pdf_preview/download_service.py` com:
  - fun??es para obter o diret?rio padr?o de downloads,
    montar caminhos ?nicos e salvar PDF/imagens;
  - `DownloadContext` descrevendo nome base, diret?rio e extens?o.
- M?todos `_download_pdf` e `_download_img` de `PdfViewerWin`
  passaram a delegar para o servi?o, mantendo a mesma UX
  (mensagens, nomes, diret?rio).
- A l?gica de convers?o Pixmap?imagem permaneceu na view ou em
  um helper pr?ximo, sem mudan?as vis?veis para o usu?rio.

**Pr?ximos passos**
- Etapa 5 (poss?vel): revisar atalhos/binds de teclado/mouse e
  extrair um controlador de inputs, preparando o m?dulo para
  futuras evolu??es sem tocar na l?gica de renderiza??o.


## Etapa 5 ? Split final e shim `pdf_preview_native.py`

**Objetivo**
- Reduzir o tamanho de `src/ui/pdf_preview_native.py` movendo a
  janela principal (`PdfViewerWin`) para o m?dulo `modules`, e
  deixar o arquivo de UI apenas como shim/entrypoint.

**Implementado nesta etapa**
- Cria??o de `src/modules/pdf_preview/views/main_window.py`
  concentrando a classe `PdfViewerWin` e os tipos auxiliares de
  callbacks Tkinter.
- `src/ui/pdf_preview_native.py` passou a importar `PdfViewerWin`
  desse m?dulo e a expor apenas:
    - a fun??o `open_pdf_viewer(...)` (entrypoint p?blico);
    - o helper `_center_modal(...)` utilizado para centralizar a
      janela.
- O tamanho de `pdf_preview_native.py` foi reduzido
  significativamente, aproximando-o do padr?o de shim adotado em
  Auditoria/Clientes, sem alterar API ou UX.

**Pr?ximos passos**
- (Opcional) Etapa 6: checkpoint do m?dulo PDF Preview e foco em
  limpeza de helpers/imports globais no projeto.

## Etapa 6 - Checkpoint de modularizacao do PDF Preview

**Objetivo**
- Registrar o estado atual do modulo PDF Preview apos as
  etapas de modularizacao, marcando uma baseline estavel
  para futuras features e correcoes.

**Estado atual**
- `PdfPreviewController` em `src/modules/pdf_preview/controller.py`
  centraliza o estado de navegacao (pagina atual, total),
  zoom/fit, flag de texto e integracao com os servicos de
  rasterizacao e download.
- Servico de rasterizacao em
  `src/modules/pdf_preview/raster_service.py` (`PdfRasterService`)
  e responsavel por abrir o documento via PyMuPDF, expor
  `page_count`, gerar Pixmaps por pagina/zoom e manter um
  cache simples de rasterizacao.
- UI dividida em componentes em `src/modules/pdf_preview/views/`:
  - `main_window.py` com `PdfViewerWin` (janela principal),
    orquestrando controller + servicos + subcomponentes.
  - `toolbar.py` com `PdfToolbar` (zoom/fit, labels, toggle
    de texto, botoes de download).
  - `page_view.py` com `PdfPageView` (canvas + scroll e
    desenho da imagem).
  - `text_panel.py` com `PdfTextPanel` (texto/OCR e busca
    integrada ao SearchNavigator).
- Servico/helper de download em
  `src/modules/pdf_preview/download_service.py` encapsula
  resolucao de diretorio padrao, nomes unicos e escrita em
  disco de PDF/imagens, reutilizado pela view.
- Arquivo `src/ui/pdf_preview_native.py` foi reduzido a um
  shim leve que apenas:
    - importa `PdfViewerWin` do modulo de views;
    - mantem o helper `_center_modal`;
    - expoe a funcao publica `open_pdf_viewer(...)` usada
      pelo restante do app.
- Tipagem para callbacks Tkinter (`TkBindReturn`, `TkCallback`)
  ajustada para aceitar eventos opcionais e retornos "break"
  sem conflitos com o Pylance, mantendo a semantica do Tk.

**Notas**
- Os comandos `python -m compileall`, `pytest -q` e
  `ruff check` estao passando para este modulo.
- Nenhuma mudanca funcional esta prevista nesta Etapa 6; o
  foco e apenas registrar o estado e servir de referencia
  para futuras evolucoes.

**Proximos passos sugeridos**
- Iniciar a modularizacao de outro arquivo grande da UI
  (ex.: `src/ui/main_window.py`, atualmente com ~878 linhas),
  reaplicando o mesmo padrao de split em controller + views +
  servicos.
