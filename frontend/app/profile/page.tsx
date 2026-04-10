'use client';

import { useState, useEffect } from 'react';
import { User, Mail, Calendar, BarChart3, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useTranslation } from '@/hooks/useTranslation';
import Link from 'next/link';

interface ProfileData {
  displayName: string;
  email: string;
  plan: string;
  usageUsed: number;
  usageTotal: number;
  memberSince: string;
}

export default function ProfilePage() {
  const { t } = useTranslation();
  const [profile, setProfile] = useState<ProfileData | null>(null);

  useEffect(() => {
    // localStorage에서 프로필 로드 (Supabase 연동 시 API 호출로 교체)
    const saved = localStorage.getItem('ie_profile');
    if (saved) {
      try {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setProfile(JSON.parse(saved));
        return;
      } catch {
        localStorage.removeItem('ie_profile');
      }
    }
    // 기본 프로필
    setProfile({
      displayName: 'User',
      email: '',
      plan: 'Free',
      usageUsed: 0,
      usageTotal: 30,
      memberSince: new Date().toISOString().split('T')[0],
    });
  }, []);

  if (!profile) return null;

  const usagePercent = profile.usageTotal > 0
    ? Math.round((profile.usageUsed / profile.usageTotal) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-lg mx-auto px-4 py-8">
        {/* 뒤로가기 */}
        <Link href="/">
          <Button variant="ghost" size="sm" className="gap-1.5 mb-6 -ml-2">
            <ArrowLeft className="h-4 w-4" />
            {t('common.back')}
          </Button>
        </Link>

        <h1 className="text-xl font-bold mb-6">{t('profile.title')}</h1>

        {/* 아바타 + 이름 */}
        <div className="flex items-center gap-4 mb-8">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white text-xl font-bold shadow-md">
            {profile.displayName.charAt(0).toUpperCase()}
          </div>
          <div>
            <h2 className="text-lg font-semibold">{profile.displayName}</h2>
            {profile.email && (
              <p className="text-sm text-muted-foreground">{profile.email}</p>
            )}
          </div>
        </div>

        {/* 정보 카드 */}
        <div className="space-y-3">
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <Mail className="h-4.5 w-4.5 text-muted-foreground" />
              <div className="flex-1">
                <p className="text-xs text-muted-foreground">{t('profile.email')}</p>
                <p className="text-sm font-medium">{profile.email || '-'}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <User className="h-4.5 w-4.5 text-muted-foreground" />
              <div className="flex-1">
                <p className="text-xs text-muted-foreground">{t('profile.plan')}</p>
                <p className="text-sm font-medium">{profile.plan}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3 mb-2">
                <BarChart3 className="h-4.5 w-4.5 text-muted-foreground" />
                <div className="flex-1">
                  <p className="text-xs text-muted-foreground">{t('profile.usage')}</p>
                  <p className="text-sm font-medium">
                    {t('profile.usageOf', { used: profile.usageUsed, total: profile.usageTotal })}
                  </p>
                </div>
              </div>
              {/* 사용량 프로그래스 바 */}
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all"
                  style={{ width: `${usagePercent}%` }}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <Calendar className="h-4.5 w-4.5 text-muted-foreground" />
              <div className="flex-1">
                <p className="text-xs text-muted-foreground">{t('profile.memberSince')}</p>
                <p className="text-sm font-medium">{profile.memberSince}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
