'use client';

interface WordCloudProps {
  /** 워드클라우드 SVG 문자열 */
  svg: string;
}

/** SVG 워드클라우드를 표시합니다. */
export default function WordCloud({ svg }: WordCloudProps) {
  if (!svg) return null;

  return (
    <div className="mt-4 rounded-xl border border-border/50 bg-muted/20 p-4">
      <h4 className="text-sm font-medium text-foreground/70 mb-3">워드클라우드</h4>
      <div
        className="w-full [&>svg]:w-full [&>svg]:h-auto"
        dangerouslySetInnerHTML={{ __html: svg }}
      />
    </div>
  );
}
