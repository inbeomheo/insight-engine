'use client';

import { Badge } from '@/components/ui/badge';
import { Bot, CheckCircle2, Quote, Tag } from 'lucide-react';
import type { GeoMetadata } from '@/lib/types';

export default function GeoSection({ geo }: { geo: GeoMetadata }) {
  return (
    <div className="mt-4 p-3 border border-border rounded-lg bg-muted/50">
      <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold">
        <Bot className="h-3.5 w-3.5 text-primary" />
        GEO 메타데이터 (AI 검색 최적화)
      </div>

      <div className="space-y-2 text-xs">
        {/* 인용 가능한 핵심 팩트 */}
        {geo.citations?.length > 0 && (
          <div>
            <div className="flex items-center gap-1 text-muted-foreground mb-1">
              <Quote className="h-3 w-3" />
              인용 가능 팩트
            </div>
            <ol className="list-decimal list-inside space-y-0.5 text-foreground">
              {geo.citations.map((cite, i) => (
                <li key={i} className="leading-relaxed">{cite}</li>
              ))}
            </ol>
          </div>
        )}

        {/* 엔티티 태그 */}
        {geo.entity_tags?.length > 0 && (
          <div>
            <div className="flex items-center gap-1 text-muted-foreground mb-1">
              <Tag className="h-3 w-3" />
              엔티티 태그
            </div>
            <div className="flex flex-wrap gap-1">
              {geo.entity_tags.map((tag) => (
                <Badge key={tag} variant="outline" className="text-[10px]">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* 구조화된 데이터 */}
        {geo.structured_data && Object.keys(geo.structured_data).length > 0 && (
          <div>
            <span className="text-muted-foreground">구조화 데이터:</span>
            <table className="mt-1 w-full text-[11px] border-collapse">
              <tbody>
                {Object.entries(geo.structured_data).map(([key, value]) => (
                  <tr key={key} className="border-b border-border/50">
                    <td className="py-0.5 pr-2 font-medium text-muted-foreground whitespace-nowrap">{key}</td>
                    <td className="py-0.5 text-foreground">{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 검증 가능한 핵심 사실 */}
        {geo.key_facts?.length > 0 && (
          <div>
            <div className="flex items-center gap-1 text-muted-foreground mb-1">
              <CheckCircle2 className="h-3 w-3" />
              핵심 사실
            </div>
            <ul className="space-y-0.5 text-foreground">
              {geo.key_facts.map((fact, i) => (
                <li key={i} className="flex items-start gap-1">
                  <span className="text-green-500 mt-0.5 shrink-0">&#10003;</span>
                  {fact}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
