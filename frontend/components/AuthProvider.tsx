'use client';

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useMemo,
  useCallback,
  type ReactNode,
} from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { getSupabase, isSupabaseConfigured } from '@/lib/supabaseClient';

interface AuthContextValue {
  /** Supabase가 설정되어 있는지 (.env에 URL/Anon Key 있는지) */
  configured: boolean;
  /** 초기 세션 복원 진행 중 여부 */
  loading: boolean;
  /** 현재 로그인된 사용자 (없으면 null) */
  user: User | null;
  /** 활성 세션 객체 (access_token 포함) */
  session: Session | null;
  /** 이메일/비밀번호 로그인 — 성공 시 {success:true}, 실패 시 error 문자열 포함 */
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  /** 이메일/비밀번호 회원가입 */
  signUp: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  /** 로그아웃 */
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const configured = isSupabaseConfigured();
  const [loading, setLoading] = useState<boolean>(configured);
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) {
      setLoading(false);
      return;
    }
    // 초기 세션 복원
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setUser(data.session?.user ?? null);
      setLoading(false);
    });
    // 세션 변화 구독 (로그인/로그아웃/토큰 갱신)
    const { data: sub } = supabase.auth.onAuthStateChange((_event, sess) => {
      setSession(sess);
      setUser(sess?.user ?? null);
    });
    return () => {
      sub.subscription.unsubscribe();
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const supabase = getSupabase();
    if (!supabase) {
      return { success: false, error: 'Supabase가 설정되지 않았습니다 (로컬 모드).' };
    }
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return { success: false, error: error.message };
    return { success: true };
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    const supabase = getSupabase();
    if (!supabase) {
      return { success: false, error: 'Supabase가 설정되지 않았습니다 (로컬 모드).' };
    }
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) return { success: false, error: error.message };
    return { success: true };
  }, []);

  const signOut = useCallback(async () => {
    const supabase = getSupabase();
    if (supabase) await supabase.auth.signOut();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ configured, loading, user, session, signIn, signUp, signOut }),
    [configured, loading, user, session, signIn, signUp, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within <AuthProvider>');
  }
  return ctx;
}
