export interface OutlineItem {
  title: string;
  page: number;
  level: number;
  children?: OutlineItem[];
}

export interface Concept {
  term: string;
  frequency: number;
  pages: number[];
}

export interface PDFPageInfo {
  pageNumber: number;
  width: number;
  height: number;
  scale: number;
}

export interface TextSelection {
  text: string;
  page: number;
  coords?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}
