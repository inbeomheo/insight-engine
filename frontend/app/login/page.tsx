'use client';

import { Suspense, useState, type FormEvent } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2 } from 'lucide-react';

type Mode = 'signin' | 'signup';

function LoginForm() {
  const router = useRouter();
  const search = useSearchParams();
  const redirectTo = search.get('redirect') || '/';
  const { signIn, signUp, configured, user } = useAuth();

  const [mode, setMode] = useState<Mode>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  // 이미 로그인된 경우 자동 redirect
  if (user) {
    if (typeof window !== 'undefined') {
      router.replace(redirectTo);
    }
    return null;
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setSubmitting(true);
    try {
      const result = mode === 'signin'
        ? await signIn(email, password)
        : await signUp(email, password);
      if (!result.success) {
        setError(result.error || '인증에 실패했습니다.');
      } else if (mode === 'signup') {
        setInfo('회원가입이 완료되었습니다. 이메일 인증 후 로그인해주세요.');
      } else {
        router.replace(redirectTo);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (!configured) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>로컬 모드</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>Supabase가 설정되지 않았습니다. 로컬 모드에서는 로그인 없이 모든 기능을 사용할 수 있습니다.</p>
          <Button onClick={() => router.replace('/')} className="w-full">홈으로</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="text-xl">
          {mode === 'signin' ? '로그인' : '회원가입'}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">이메일</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="you@example.com"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">비밀번호</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
            />
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {info && (
            <Alert>
              <AlertDescription>{info}</AlertDescription>
            </Alert>
          )}

          <Button type="submit" disabled={submitting} className="w-full">
            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {mode === 'signin' ? '로그인' : '회원가입'}
          </Button>

          <div className="text-center text-sm">
            {mode === 'signin' ? (
              <button
                type="button"
                className="text-primary hover:underline"
                onClick={() => { setMode('signup'); setError(null); setInfo(null); }}
              >
                계정이 없으신가요? 회원가입
              </button>
            ) : (
              <button
                type="button"
                className="text-primary hover:underline"
                onClick={() => { setMode('signin'); setError(null); setInfo(null); }}
              >
                이미 계정이 있으신가요? 로그인
              </button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Suspense
        fallback={
          <div className="text-sm text-muted-foreground">
            <Loader2 className="mx-auto h-6 w-6 animate-spin" />
          </div>
        }
      >
        <LoginForm />
      </Suspense>
    </div>
  );
}
