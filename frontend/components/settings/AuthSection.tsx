'use client';

import { FormEvent, useEffect, useState } from 'react';
import { LogIn, LogOut, UserPlus } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  getAuthSession,
  signIn,
  signOut,
  signUp,
  subscribeAuthSession,
  type AuthSession,
} from '@/lib/auth-session';

export default function AuthSection() {
  const [auth, setAuth] = useState<AuthSession | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [pending, setPending] = useState(false);

  useEffect(() => {
    const sync = () => setAuth(getAuthSession());
    sync();
    return subscribeAuthSession(sync);
  }, []);

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    if (!email.trim() || !password) return;
    setPending(true);
    try {
      await signIn(email.trim(), password);
      setPassword('');
      toast.success('로그인했습니다.');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '로그인에 실패했습니다.');
    } finally {
      setPending(false);
    }
  }

  async function handleSignup() {
    if (!email.trim() || password.length < 6) {
      toast.error('이메일과 6자 이상의 비밀번호를 입력해주세요.');
      return;
    }
    setPending(true);
    try {
      toast.success(await signUp(email.trim(), password));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '회원가입에 실패했습니다.');
    } finally {
      setPending(false);
    }
  }

  async function handleLogout() {
    setPending(true);
    try {
      await signOut();
      toast.success('로그아웃했습니다.');
    } catch (error) {
      toast.error(
        error instanceof Error
          ? `로컬에서는 로그아웃했지만 서버 세션 폐기에 실패했습니다: ${error.message}`
          : '로컬에서는 로그아웃했지만 서버 세션 폐기에 실패했습니다.',
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-3 border-t pt-4">
      <div>
        <h3 className="text-sm font-semibold">계정</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Supabase 인증을 사용하는 배포에서는 로그인해야 개인 기능을 사용할 수 있습니다.
        </p>
      </div>

      {auth ? (
        <div className="flex items-center justify-between gap-3 rounded-md border bg-muted/30 px-3 py-2">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{auth.user.email || auth.user.id}</p>
            <p className="text-[10px] text-muted-foreground">인증됨</p>
          </div>
          <Button type="button" size="sm" variant="outline" onClick={handleLogout} disabled={pending}>
            <LogOut className="mr-1 h-3.5 w-3.5" />
            로그아웃
          </Button>
        </div>
      ) : (
        <form className="space-y-2" onSubmit={handleLogin}>
          <label className="block space-y-1 text-xs font-medium">
            이메일
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm font-normal focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </label>
          <label className="block space-y-1 text-xs font-medium">
            비밀번호
            <input
              type="password"
              autoComplete="current-password"
              minLength={6}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm font-normal focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </label>
          <div className="flex gap-2">
            <Button type="submit" size="sm" className="flex-1" disabled={pending || !email || !password}>
              <LogIn className="mr-1 h-3.5 w-3.5" />
              로그인
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={handleSignup} disabled={pending}>
              <UserPlus className="mr-1 h-3.5 w-3.5" />
              회원가입
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
