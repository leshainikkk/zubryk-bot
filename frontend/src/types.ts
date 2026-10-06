export interface Profile { id: number; name: string; balance: number; streak: number; photoUrl: string | null; dailyTime: string; registered: boolean; learnedTotal: number }
export interface Day { date: string; label: string; count: number; isToday: boolean }
export interface WordTopic { key: string; name: string; total: number; learned: number }
export interface Leader { name: string; balance: number; rank: number; isMe: boolean }
export interface Dashboard { profile: Profile | null; preview?: boolean; botUsername: string; timezone: string; week: { total: number; days: Day[] }; topics: WordTopic[]; leaders: Leader[]; dailyTimeChoices: { value: string; label: string }[] }
export type Tab = 'home' | 'tests' | 'grammar';
export type RuleBlock = { type: 'paragraph' | 'heading' | 'example'; text: string } | { type: 'list'; items: string[] };
export interface Rule { id: string; title: string; category: string; summary: string; content: RuleBlock[]; examples: string[]; sources: { title: string; url: string }[]; authorship: string }
export interface ExamTopic { id: string; title: string; description: string; icon: string; questionCount: number; variants: string[] }
export interface AnswerResult { correct: boolean; answers: string[]; correctAnswers: string[]; explanation: string }
export interface Question { id: string; topicId: string; variantId: string; type: 'single' | 'multiple'; prompt: string; options: { id: string; text: string }[]; source: string; materials: string[]; attempt?: AnswerResult }
export interface TelegramWebApp {
  initData: string; colorScheme: 'light' | 'dark'; themeParams: Record<string, string | undefined>;
  safeAreaInset?: { top: number; bottom: number; left: number; right: number };
  contentSafeAreaInset?: { top: number; bottom: number; left: number; right: number };
  viewportStableHeight?: number; version: string;
  ready(): void; expand(): void; close(): void;
  onEvent(name: string, callback: () => void): void; offEvent(name: string, callback: () => void): void;
  setHeaderColor(color: string): void; setBackgroundColor(color: string): void; setBottomBarColor?(color: string): void;
  isVersionAtLeast(version: string): boolean;
  openTelegramLink(url: string): void;
  HapticFeedback?: { impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void; selectionChanged(): void; notificationOccurred(type: 'success' | 'error' | 'warning'): void };
  BackButton: { show(): void; hide(): void; onClick(callback: () => void): void; offClick(callback: () => void): void };
  SettingsButton?: { show(): void; hide(): void; onClick(callback: () => void): void; offClick(callback: () => void): void };
}
declare global { interface Window { Telegram?: { WebApp: TelegramWebApp } } }
