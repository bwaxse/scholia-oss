import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import * as pdfjsLib from 'pdfjs-dist';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.js?url';
import type { TextSelection } from '../../types/pdf.ts';

// Use local worker asset — avoids CDN dependency and version drift
pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

// WeakMap to track per-element mouseup handlers — type-safe and GC-friendly
const mouseupHandlers = new WeakMap<Element, EventListener>();

@customElement('pdf-viewer')
export class PdfViewer extends LitElement {
  @property({ type: String }) pdfUrl = '';
  @property({ type: Number }) scale = 1.5;

  @state() private pdf?: PDFDocumentProxy;
  @state() private numPages = 0;
  @state() private loading = true;
  @state() private error = '';
  @state() private currentPage = 1;
  @state() private isPanning = false;

  private renderingPages = new Set<number>();
  private renderTasks = new Map<number, any>(); // Track active render tasks
  private intersectionObserver?: IntersectionObserver;
  private visiblePages = new Set<number>(); // tracks currently intersecting pages

  // Pan state
  private panStart = { x: 0, y: 0 };
  private scrollStart = { x: 0, y: 0 };

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      width: 100%;
      min-width: 0;
      background: #525659;
    }

    .toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      background: #323639;
      color: white;
      border-bottom: 1px solid #000;
      min-width: 0;
      flex-shrink: 0;
    }

    .toolbar-section {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .toolbar button {
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: white;
      padding: 6px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
    }

    .toolbar button:hover {
      background: rgba(255, 255, 255, 0.2);
    }

    .toolbar button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .page-info {
      font-size: 14px;
    }

    .toolbar button {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .desktop-page-info {
      display: inline;
    }

    .mobile-page-info {
      display: none;
    }

    /* Mobile toolbar styles */
    @media (max-width: 768px) {
      .toolbar {
        display: none; /* Hide toolbar entirely on mobile */
      }
    }

    .pdf-container {
      flex: 1;
      overflow-y: auto;
      overflow-x: auto;
      padding: 20px;
      cursor: grab;
      user-select: none;
      /* Allow native vertical scroll and pinch-to-zoom on mobile */
      touch-action: pan-x pan-y pinch-zoom;
    }

    .pdf-container.panning {
      cursor: grabbing;
    }

    .pages {
      display: flex;
      flex-direction: column;
      gap: 20px;
      align-items: center;
      margin: 0 auto;
      width: fit-content;
      min-width: 100%;
    }

    .page {
      position: relative;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
      background: white;
    }

    .page canvas {
      display: block;
    }

    .textLayer {
      position: absolute;
      left: 0;
      top: 0;
      right: 0;
      bottom: 0;
      overflow: hidden;
      line-height: 1.0;
      user-select: text;
      pointer-events: none;
    }

    .textLayer > span {
      color: transparent;
      -webkit-text-fill-color: transparent;
      -webkit-font-smoothing: none;
      position: absolute;
      white-space: pre;
      cursor: text;
      transform-origin: 0% 0%;
      pointer-events: auto;
    }

    .textLayer ::selection {
      color: transparent;
      background: rgba(255, 220, 0, 0.45);
    }

    .loading,
    .error {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: white;
      font-size: 16px;
    }

    .error {
      color: #ff6b6b;
    }

    .page-placeholder {
      width: 800px;
      height: 1100px;
      background: rgba(255, 255, 255, 0.1);
      display: flex;
      align-items: center;
      justify-content: center;
      color: rgba(255, 255, 255, 0.5);
    }
  `;

  // firstUpdated removed — updated() handles the initial pdfUrl load too,
  // preventing a double loadPDF() call on first render.

  async updated(changedProperties: Map<string, any>) {
    if (changedProperties.has('pdfUrl') && this.pdfUrl) {
      await this.loadPDF();
    }
    if (changedProperties.has('scale') && this.pdf) {
      await this.rerenderVisiblePages();
    }
  }

  async loadPDF() {
    this.loading = true;
    this.error = '';

    try {
      const loadingTask = pdfjsLib.getDocument(this.pdfUrl);
      this.pdf = await loadingTask.promise;
      this.numPages = this.pdf.numPages;
      this.loading = false;

      // Set up intersection observer after pages are rendered
      await this.updateComplete;
      this.setupIntersectionObserver();
    } catch (err) {
      console.error('Error loading PDF:', err);
      this.error = 'Failed to load PDF.';
      this.loading = false;
      this.dispatchEvent(new CustomEvent('pdf-load-error', {
        bubbles: true,
        composed: true,
        detail: { error: err }
      }));
    }
  }

  setupIntersectionObserver() {
    if (this.intersectionObserver) {
      this.intersectionObserver.disconnect();
    }

    this.visiblePages.clear();

    this.intersectionObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const pageNum = parseInt(
            (entry.target as HTMLElement).dataset.page || '0'
          );
          if (pageNum > 0) {
            if (entry.isIntersecting) {
              this.visiblePages.add(pageNum);
              this.renderPage(pageNum);
            } else {
              this.visiblePages.delete(pageNum);
            }
          }
        });

        // Update toolbar to show topmost visible page
        if (this.visiblePages.size > 0) {
          this.currentPage = Math.min(...this.visiblePages);
        }
      },
      {
        root: this.shadowRoot?.querySelector('.pdf-container'),
        rootMargin: '500px', // Pre-render pages close to viewport
        threshold: 0.01
      }
    );

    const pageContainers = this.shadowRoot?.querySelectorAll('.page');
    pageContainers?.forEach((container) => {
      this.intersectionObserver?.observe(container);
    });
  }

  async renderPage(pageNum: number) {
    if (!this.pdf) {
      return;
    }

    // Cancel any existing render task for this page and wait for it
    const existingTask = this.renderTasks.get(pageNum);
    if (existingTask) {
      existingTask.cancel();
      this.renderTasks.delete(pageNum);
      this.renderingPages.delete(pageNum);
      // Give time for cancellation to complete
      await new Promise(resolve => setTimeout(resolve, 0));
    }

    // Check again after awaiting - another render may have started
    if (this.renderingPages.has(pageNum)) {
      return;
    }

    this.renderingPages.add(pageNum);

    try {
      const page = await this.pdf.getPage(pageNum);
      const viewport = page.getViewport({ scale: this.scale });

      const pageContainer = this.shadowRoot?.querySelector(
        `.page[data-page="${pageNum}"]`
      );
      if (!pageContainer) return;

      const canvas = pageContainer.querySelector('canvas') as HTMLCanvasElement;
      const textLayerDiv = pageContainer.querySelector('.textLayer') as HTMLElement;

      if (!canvas || !textLayerDiv) return;

      // Render canvas
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      const context = canvas.getContext('2d');
      if (context) {
        context.clearRect(0, 0, canvas.width, canvas.height);

        const renderTask = page.render({ canvasContext: context, viewport });
        this.renderTasks.set(pageNum, renderTask);

        try {
          await renderTask.promise;
        } catch (err: any) {
          if (err.name === 'RenderingCancelledException') {
            return;
          }
          throw err;
        }
      }

      // Render text layer
      const textContent = await page.getTextContent();
      textLayerDiv.replaceChildren(); // clear without innerHTML
      textLayerDiv.style.width = viewport.width + 'px';
      textLayerDiv.style.height = viewport.height + 'px';

      textContent.items.forEach((item: any) => {
        if (item.str) {
          const span = document.createElement('span');
          span.textContent = item.str;

          const transform = pdfjsLib.Util.transform(
            viewport.transform,
            item.transform
          );

          const angle = Math.atan2(transform[1], transform[0]);
          const fontHeight = Math.sqrt(transform[2] * transform[2] + transform[3] * transform[3]);

          span.style.left = transform[4] + 'px';
          span.style.top = (transform[5] - fontHeight) + 'px';
          span.style.fontSize = fontHeight + 'px';
          span.style.fontFamily = item.fontName || 'sans-serif';
          if (item.width) {
            const hScale = Math.sqrt(transform[0] * transform[0] + transform[1] * transform[1]);
            span.style.width = (item.width * hScale) + 'px';
          }

          if (angle !== 0) {
            span.style.transform = `rotate(${angle}rad)`;
          } else {
            span.style.overflow = 'hidden';
          }

          textLayerDiv.appendChild(span);
        }
      });

      // Remove any previous mouseup handler before adding a new one to prevent
      // accumulation across re-renders ({ once: true } only removes after firing,
      // not before, so N renders before first mouseup would still queue N handlers).
      const prev = mouseupHandlers.get(textLayerDiv);
      if (prev) textLayerDiv.removeEventListener('mouseup', prev);
      const mouseupHandler = () => this.handleTextSelection(pageNum);
      mouseupHandlers.set(textLayerDiv, mouseupHandler);
      textLayerDiv.addEventListener('mouseup', mouseupHandler);
    } catch (err) {
      console.error(`Error rendering page ${pageNum}:`, err);
    } finally {
      this.renderingPages.delete(pageNum);
      this.renderTasks.delete(pageNum);
    }
  }

  async rerenderVisiblePages() {
    // Cancel all active render tasks
    const cancelPromises: Promise<void>[] = [];
    this.renderTasks.forEach((task, pageNum) => {
      task.cancel();
      cancelPromises.push(
        task.promise.catch(() => {}).finally(() => {
          this.renderTasks.delete(pageNum);
          this.renderingPages.delete(pageNum);
        })
      );
    });

    await Promise.all(cancelPromises);
    this.renderTasks.clear();
    this.renderingPages.clear();

    // Small delay to ensure canvas is released
    await new Promise(resolve => setTimeout(resolve, 50));

    // Re-render only currently visible pages
    this.visiblePages.forEach((pageNum) => {
      this.renderPage(pageNum);
    });
  }

  handleTextSelection(pageNum: number) {
    const selection = window.getSelection();
    const selectedText = selection?.toString().trim();

    if (selectedText) {
      const textSelection: TextSelection = {
        text: selectedText,
        page: pageNum
      };

      this.dispatchEvent(
        new CustomEvent('text-selected', {
          detail: textSelection,
          bubbles: true,
          composed: true
        })
      );
    }
  }

  zoomIn() {
    this.scale = Math.min(this.scale + 0.25, 3.0);
  }

  zoomOut() {
    this.scale = Math.max(this.scale - 0.25, 0.5);
  }

  resetZoom() {
    this.scale = 1.5;
  }

  goToPage(page: number) {
    if (page < 1 || page > this.numPages) return;

    const pageContainer = this.shadowRoot?.querySelector(
      `.page[data-page="${page}"]`
    );

    if (pageContainer) {
      pageContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
      this.currentPage = page;
    }
  }

  // Public alias for external navigation
  scrollToPage(page: number) {
    this.goToPage(page);
  }

  nextPage() {
    this.goToPage(this.currentPage + 1);
  }

  prevPage() {
    this.goToPage(this.currentPage - 1);
  }

  // Mouse drag-to-pan handlers
  handleMouseDown(e: MouseEvent) {
    if (e.button !== 0) return;

    const target = e.target as HTMLElement;
    if (target.closest('.textLayer')) {
      return;
    }

    const container = this.shadowRoot?.querySelector('.pdf-container') as HTMLElement;
    if (!container) return;

    this.isPanning = true;
    this.panStart = { x: e.clientX, y: e.clientY };
    this.scrollStart = { x: container.scrollLeft, y: container.scrollTop };

    e.preventDefault();
  }

  handleMouseMove(e: MouseEvent) {
    if (!this.isPanning) return;

    const container = this.shadowRoot?.querySelector('.pdf-container') as HTMLElement;
    if (!container) return;

    const dx = e.clientX - this.panStart.x;
    const dy = e.clientY - this.panStart.y;

    container.scrollLeft = this.scrollStart.x - dx;
    container.scrollTop = this.scrollStart.y - dy;
  }

  handleMouseUp() {
    this.isPanning = false;
  }

  handleMouseLeave() {
    this.isPanning = false;
  }

  render() {
    if (this.loading) {
      return html`<div class="loading">Loading PDF...</div>`;
    }

    if (this.error) {
      return html`<div class="error">${this.error}</div>`;
    }

    if (!this.pdf) {
      return html`<div class="loading">No PDF loaded</div>`;
    }

    return html`
      <div class="toolbar">
        <div class="toolbar-section">
          <button @click=${this.prevPage} ?disabled=${this.currentPage === 1}>
            <svg class="btn-icon" viewBox="0 0 24 24" width="16" height="16">
              <polyline points="15 18 9 12 15 6" stroke="currentColor" fill="none" stroke-width="2"/>
            </svg>
            <span class="btn-text">Previous</span>
          </button>
          <span class="page-info">
            <span class="desktop-page-info">Page ${this.currentPage} / ${this.numPages}</span>
            <span class="mobile-page-info">${this.currentPage}/${this.numPages}</span>
          </span>
          <button @click=${this.nextPage} ?disabled=${this.currentPage === this.numPages}>
            <svg class="btn-icon" viewBox="0 0 24 24" width="16" height="16">
              <polyline points="9 18 15 12 9 6" stroke="currentColor" fill="none" stroke-width="2"/>
            </svg>
            <span class="btn-text">Next</span>
          </button>
        </div>

        <div class="toolbar-section">
          <button @click=${this.zoomOut} ?disabled=${this.scale <= 0.5}>
            <svg class="btn-icon" viewBox="0 0 24 24" width="16" height="16">
              <circle cx="11" cy="11" r="8" stroke="currentColor" fill="none" stroke-width="2"/>
              <line x1="8" y1="11" x2="14" y2="11" stroke="currentColor" stroke-width="2"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65" stroke="currentColor" stroke-width="2"/>
            </svg>
            <span class="btn-text">Zoom Out</span>
          </button>
          <span class="page-info">${Math.round(this.scale * 100)}%</span>
          <button @click=${this.zoomIn} ?disabled=${this.scale >= 3.0}>
            <svg class="btn-icon" viewBox="0 0 24 24" width="16" height="16">
              <circle cx="11" cy="11" r="8" stroke="currentColor" fill="none" stroke-width="2"/>
              <line x1="11" y1="8" x2="11" y2="14" stroke="currentColor" stroke-width="2"/>
              <line x1="8" y1="11" x2="14" y2="11" stroke="currentColor" stroke-width="2"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65" stroke="currentColor" stroke-width="2"/>
            </svg>
            <span class="btn-text">Zoom In</span>
          </button>
          <button class="reset-btn" @click=${this.resetZoom}>
            <span class="btn-text">Reset</span>
          </button>
        </div>
      </div>

      <div
        class="pdf-container ${this.isPanning ? 'panning' : ''}"
        @mousedown=${this.handleMouseDown}
        @mousemove=${this.handleMouseMove}
        @mouseup=${this.handleMouseUp}
        @mouseleave=${this.handleMouseLeave}
      >
        <div class="pages">
          ${Array.from({ length: this.numPages }, (_, i) => i + 1).map(
            (pageNum) => html`
              <div class="page" data-page="${pageNum}">
                <canvas></canvas>
                <div class="textLayer"></div>
              </div>
            `
          )}
        </div>
      </div>
    `;
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.intersectionObserver) {
      this.intersectionObserver.disconnect();
    }
    this.renderTasks.forEach((task) => task.cancel());
    this.renderTasks.clear();
    this.renderingPages.clear();
    this.pdf?.destroy();
    this.pdf = undefined;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'pdf-viewer': PdfViewer;
  }
}
