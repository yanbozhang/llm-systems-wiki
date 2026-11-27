import type { MermaidConfig } from 'mermaid';

export const diagramTheme: MermaidConfig = {
  startOnLoad: false,
  securityLevel: 'strict',
  theme: 'base',
  fontFamily: 'Inter, PingFang SC, Microsoft YaHei, Noto Sans CJK SC, sans-serif',
  fontSize: 18,
  htmlLabels: false,
  themeVariables: {
    background: '#ffffff',
    primaryColor: '#eef4ff',
    primaryTextColor: '#183654',
    primaryBorderColor: '#728eb7',
    secondaryColor: '#eaf7f5',
    tertiaryColor: '#f4effc',
    lineColor: '#596f88',
    textColor: '#183654',
    edgeLabelBackground: '#ffffff',
    clusterBkg: '#f6f8fc',
    clusterBorder: '#ccd6e3',
    fontSize: '18px',
  },
  flowchart: {
    htmlLabels: false,
    useMaxWidth: false,
    curve: 'linear',
    nodeSpacing: 36,
    rankSpacing: 54,
    diagramPadding: 24,
    padding: 18,
    wrappingWidth: 220,
  },
};

export function fitDiagram(width: number, available: number, readable = true): number {
  if (!Number.isFinite(width) || width <= 0) return 1;
  const fit = Math.min(1, Math.max(1, available) / width);
  return readable ? Math.max(0.8, fit) : fit;
}

export function readableFlowchart(source: string, width: number, height: number): string {
  if (width <= 1100 || width / height <= 3.5) return source;
  return source.replace(/^(\s*(?:flowchart|graph)) LR\b/m, '$1 TB');
}
