import type { ModelInfo } from '@/lib/types';

const DEFAULT_MODEL_ID = 'cliproxyapi/gpt-5.5';

/** 이전 서비스의 선택은 지원 중인 동일 모델에 한해서만 연결한다. 저장 데이터는 수정하지 않는다. */
export function resolveModelSelection(models: Pick<ModelInfo, 'id'>[], selectedModel: string): string {
  const savedModel = typeof selectedModel === 'string' ? selectedModel : '';
  const candidate = savedModel.startsWith('chatmock/')
    ? savedModel.replace(/^chatmock\//, 'cliproxyapi/')
    : savedModel;

  if (models.some((model) => model.id === candidate)) return candidate;
  return models.find((model) => model.id === DEFAULT_MODEL_ID)?.id ?? models[0]?.id ?? '';
}
