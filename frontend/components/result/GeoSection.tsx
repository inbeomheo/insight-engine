'use client';

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Bot, CheckCircle2, Quote, Tag, Code, Copy, Check, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import type { GeoMetadata, CtaData, JsonLdSchema } from '@/lib/types';

interface GeoSectionProps {
  geo: GeoMetadata;
  cta?: CtaData;
  json_ld_schemas?: JsonLdSchema[];
}

export default function GeoSection({ geo, cta, json_ld_schemas }: GeoSectionProps) {
  const [jsonLdExpanded, setJsonLdExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  async function copyJsonLd() {
    if (!json_ld_schemas) return;
    const text = JSON.stringify(json_ld_schemas, null, 2);
    await navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success('JSON-LD 복사 완료');
    setTimeout(() => setCopied(false), 2000);
  }

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

        {/* CTA */}
        {cta && (cta.primary || cta.secondary) && (
          <div>
            <div className="flex items-center gap-1 text-muted-foreground mb-1">
              <ExternalLink className="h-3 w-3" />
              CTA
            </div>
            <div className="space-y-0.5">
              {cta.primary && (
                <div className="text-foreground">
                  <span className="text-muted-foreground mr-1">Primary:</span>
                  {cta.primary}
                </div>
              )}
              {cta.secondary && (
                <div className="text-foreground">
                  <span className="text-muted-foreground mr-1">Secondary:</span>
                  {cta.secondary}
                </div>
              )}
            </div>
          </div>
        )}

        {/* JSON-LD 구조화 데이터 스키마 */}
        {json_ld_schemas && json_ld_schemas.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1 text-muted-foreground">
                <Code className="h-3 w-3" />
                JSON-LD 스키마 ({json_ld_schemas.length}개)
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 px-1.5 text-[10px] gap-0.5"
                  onClick={copyJsonLd}
                >
                  {copied ? (
                    <Check className="h-3 w-3 text-green-500" />
                  ) : (
                    <Copy className="h-3 w-3" />
                  )}
                  복사
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 px-1.5 text-[10px] gap-0.5"
                  onClick={() => setJsonLdExpanded((v) => !v)}
                >
                  {jsonLdExpanded ? (
                    <ChevronUp className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                  {jsonLdExpanded ? '접기' : '펼치기'}
                </Button>
              </div>
            </div>

            {/* 스키마 타입 뱃지 */}
            <div className="flex flex-wrap gap-1 mb-1">
              {json_ld_schemas.map((schema, i) => (
                <Badge key={i} variant="secondary" className="text-[10px]">
                  {String(schema['@type'] ?? 'Schema')}
                </Badge>
              ))}
            </div>

            {/* 펼쳤을 때 코드 미리보기 */}
            {jsonLdExpanded && (
              <pre className="mt-1 p-2 rounded bg-muted text-[10px] leading-relaxed overflow-auto max-h-64 whitespace-pre-wrap break-all">
                {JSON.stringify(json_ld_schemas, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
