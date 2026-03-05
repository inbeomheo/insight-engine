'use client';

/**
 * YouTube 채널 분석 대시보드
 * - 채널 통계 카드
 * - 주제 클러스터 목록
 * - 최근 영상 테이블
 */

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BarChart3, Eye, Users, Video, TrendingUp } from 'lucide-react';

interface TopicCluster {
  topic: string;
  count: number;
  ratio: number;
}

interface VideoItem {
  video_id: string;
  title: string;
  published_at: string;
  view_count: number;
  like_count: number;
}

interface ChannelStats {
  total_videos: number;
  total_views: number;
  subscriber_count: number;
  recent_video_count: number;
  avg_views_recent: number;
}

interface ChannelAnalysisData {
  channel_name: string;
  stats: ChannelStats;
  topic_clusters: TopicCluster[];
  recent_videos: VideoItem[];
}

interface Props {
  data: ChannelAnalysisData;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

const STAT_ITEMS = [
  { key: 'subscriber_count' as const, label: '구독자', icon: Users },
  { key: 'total_videos' as const, label: '총 영상', icon: Video },
  { key: 'total_views' as const, label: '총 조회수', icon: Eye },
  { key: 'avg_views_recent' as const, label: '최근 평균 조회', icon: TrendingUp },
];

export default function ChannelAnalysis({ data }: Props) {
  const { channel_name, stats, topic_clusters, recent_videos } = data;

  return (
    <div className="space-y-6">
      {/* 채널 이름 */}
      <div className="flex items-center gap-2">
        <BarChart3 className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-semibold">{channel_name}</h3>
      </div>

      {/* 통계 카드 그리드 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {STAT_ITEMS.map(({ key, label, icon: Icon }) => (
          <Card key={key}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Icon className="h-4 w-4" />
                <span className="text-xs">{label}</span>
              </div>
              <p className="text-xl font-bold">{formatNumber(stats[key])}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 주제 클러스터 */}
      {topic_clusters.length > 0 && (
        <section>
          <h4 className="text-sm font-semibold text-muted-foreground mb-3">인기 주제</h4>
          <div className="flex flex-wrap gap-2">
            {topic_clusters.map((cluster) => (
              <Badge key={cluster.topic} variant="secondary" className="text-sm py-1 px-3">
                {cluster.topic}
                <span className="ml-1.5 text-muted-foreground">({cluster.count})</span>
              </Badge>
            ))}
          </div>
        </section>
      )}

      {/* 최근 영상 테이블 */}
      {recent_videos.length > 0 && (
        <section>
          <h4 className="text-sm font-semibold text-muted-foreground mb-3">
            최근 영상 ({recent_videos.length}개)
          </h4>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left p-3 font-medium">제목</th>
                  <th className="text-right p-3 font-medium whitespace-nowrap">조회수</th>
                  <th className="text-right p-3 font-medium whitespace-nowrap">좋아요</th>
                  <th className="text-right p-3 font-medium whitespace-nowrap">게시일</th>
                </tr>
              </thead>
              <tbody>
                {recent_videos.map((video) => (
                  <tr key={video.video_id} className="border-b border-border/50 hover:bg-muted/30">
                    <td className="p-3">
                      <a
                        href={`https://www.youtube.com/watch?v=${video.video_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline line-clamp-1"
                      >
                        {video.title}
                      </a>
                    </td>
                    <td className="p-3 text-right text-muted-foreground whitespace-nowrap">
                      {formatNumber(video.view_count)}
                    </td>
                    <td className="p-3 text-right text-muted-foreground whitespace-nowrap">
                      {formatNumber(video.like_count)}
                    </td>
                    <td className="p-3 text-right text-muted-foreground whitespace-nowrap">
                      {video.published_at ? new Date(video.published_at).toLocaleDateString('ko-KR') : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
