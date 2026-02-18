'use client';

import { Badge } from '@/components/ui/badge';
import { Globe } from 'lucide-react';
import type { SeoMetadata } from '@/lib/types';

export default function SeoSection({ seo }: { seo: SeoMetadata }) {
  return (
    <div className="mt-4 p-3 border border-border rounded-lg bg-muted/50">
      <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold">
        <Globe className="h-3.5 w-3.5 text-primary" />
        SEO 메타데이터
      </div>

      <div className="space-y-2 text-xs">
        {seo.meta_description && (
          <div>
            <span className="text-muted-foreground">메타 설명:</span>
            <p className="mt-0.5 text-foreground">{seo.meta_description}</p>
          </div>
        )}

        {seo.slug && (
          <div>
            <span className="text-muted-foreground">슬러그:</span>
            <code className="ml-1 bg-muted px-1 py-0.5 rounded text-[11px]">{seo.slug}</code>
          </div>
        )}

        {seo.keywords?.length > 0 && (
          <div>
            <span className="text-muted-foreground">키워드:</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {seo.keywords.map((kw) => (
                <Badge key={kw} variant="outline" className="text-[10px]">
                  {kw}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {seo.tags?.length > 0 && (
          <div>
            <span className="text-muted-foreground">태그:</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {seo.tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="text-[10px]">
                  #{tag}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
