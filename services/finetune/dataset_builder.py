"""
LLM 파인튜닝 데이터셋 빌더 (F10-01)
Insight Engine 생성 콘텐츠를 파인튜닝 데이터셋으로 변환
OpenAI fine-tune / Hugging Face SFT 포맷 지원
"""
import json
import logging
import os
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class TrainingExample:
    """파인튜닝 학습 예시 (Instruction-Input-Output 형식)"""
    instruction: str
    input: str
    output: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_openai_format(self) -> Dict[str, Any]:
        """OpenAI fine-tuning JSONL 포맷 변환"""
        messages = []
        if self.instruction:
            messages.append({"role": "system", "content": self.instruction})
        if self.input:
            messages.append({"role": "user", "content": self.input})
        messages.append({"role": "assistant", "content": self.output})
        return {"messages": messages}

    def to_alpaca_format(self) -> Dict[str, Any]:
        """Alpaca/Stanford 포맷 변환"""
        return {
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output,
        }

    def to_sharegpt_format(self) -> Dict[str, Any]:
        """ShareGPT/Vicuna 포맷 변환"""
        return {
            "conversations": [
                {"from": "human", "value": f"{self.instruction}\n\n{self.input}".strip()},
                {"from": "gpt", "value": self.output},
            ]
        }


class DatasetBuilder:
    """
    파인튜닝 데이터셋 빌더

    사용법:
        builder = DatasetBuilder()
        builder.add_from_history(history_records)
        builder.save('dataset.jsonl', format='openai')
    """

    def __init__(self, min_output_length: int = 200):
        self.examples: List[TrainingExample] = []
        self.min_output_length = min_output_length

    def add_example(self, example: TrainingExample) -> bool:
        """예시 추가 (품질 필터링 적용)"""
        if len(example.output.strip()) < self.min_output_length:
            logger.debug("출력 너무 짧아 제외: %d자", len(example.output))
            return False
        self.examples.append(example)
        return True

    def add_from_history(self, history_records: List[Dict[str, Any]]) -> int:
        """
        히스토리 레코드 배열에서 학습 예시 자동 생성

        Args:
            history_records: ie_histories 테이블 레코드 리스트
                필드: url, title, style_id, content (생성된 콘텐츠)

        Returns:
            추가된 예시 수
        """
        added = 0
        for record in history_records:
            content = record.get('content', '')
            if not content:
                continue

            style_id = record.get('style_id', 'blog_seo')
            url = record.get('url', '')
            title = record.get('title', '제목 없음')

            instruction = self._build_instruction(style_id)
            input_text = f"YouTube URL: {url}\n영상 제목: {title}"

            example = TrainingExample(
                instruction=instruction,
                input=input_text,
                output=content,
                metadata={
                    'style_id': style_id,
                    'url': url,
                    'source': 'history',
                }
            )

            if self.add_example(example):
                added += 1

        logger.info("히스토리에서 %d개 예시 추가 (전체 %d개 중)", added, len(history_records))
        return added

    def _build_instruction(self, style_id: str) -> str:
        """스타일별 인스트럭션 생성"""
        instructions = {
            'blog_seo': "당신은 SEO 최적화 블로그 작가입니다. YouTube 영상 URL과 제목을 보고 고품질 SEO 블로그 포스트를 한국어로 작성하세요.",
            'summary': "당신은 콘텐츠 요약 전문가입니다. YouTube 영상의 핵심 내용을 구조화된 요약문으로 작성하세요.",
            'tutorial': "당신은 기술 교육 콘텐츠 전문가입니다. YouTube 영상 내용을 단계별 튜토리얼 가이드로 변환하세요.",
            'qna': "당신은 Q&A 콘텐츠 작성 전문가입니다. YouTube 영상 내용을 독자의 질문과 답변 형태로 재구성하세요.",
            'sns_post': "당신은 소셜미디어 콘텐츠 전문가입니다. YouTube 영상 핵심 인사이트를 SNS 포스트로 작성하세요.",
            'newsletter': "당신은 뉴스레터 에디터입니다. YouTube 영상 내용을 뉴스레터 형식으로 편집하세요.",
        }
        return instructions.get(style_id, "YouTube 영상 내용을 한국어 콘텐츠로 변환하세요.")

    def split(self, train_ratio: float = 0.9) -> tuple:
        """학습/검증 세트 분리"""
        random.shuffle(self.examples)
        split_idx = int(len(self.examples) * train_ratio)
        return self.examples[:split_idx], self.examples[split_idx:]

    def save(
        self,
        output_path: str,
        fmt: str = 'openai',
        split_train_val: bool = True,
        train_ratio: float = 0.9,
    ) -> Dict[str, int]:
        """
        데이터셋 저장

        Args:
            output_path: 저장 경로 (JSONL)
            fmt: 포맷 ('openai', 'alpaca', 'sharegpt')
            split_train_val: True면 train/val 파일 분리
            train_ratio: 학습 세트 비율

        Returns:
            {'train': n, 'val': m}
        """
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

        format_map = {
            'openai': lambda e: e.to_openai_format(),
            'alpaca': lambda e: e.to_alpaca_format(),
            'sharegpt': lambda e: e.to_sharegpt_format(),
        }
        converter = format_map.get(fmt, format_map['openai'])

        if split_train_val:
            train_examples, val_examples = self.split(train_ratio)
            train_path = output_path.replace('.jsonl', '_train.jsonl')
            val_path = output_path.replace('.jsonl', '_val.jsonl')

            self._write_jsonl(train_path, train_examples, converter)
            self._write_jsonl(val_path, val_examples, converter)

            logger.info("데이터셋 저장: train=%d, val=%d", len(train_examples), len(val_examples))
            return {'train': len(train_examples), 'val': len(val_examples)}
        else:
            self._write_jsonl(output_path, self.examples, converter)
            return {'total': len(self.examples)}

    def _write_jsonl(self, path: str, examples: List[TrainingExample], converter) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            for example in examples:
                line = converter(example)
                f.write(json.dumps(line, ensure_ascii=False) + '\n')
        logger.info("저장 완료: %s (%d예시)", path, len(examples))

    def get_stats(self) -> Dict[str, Any]:
        """데이터셋 통계"""
        if not self.examples:
            return {'total': 0}

        output_lengths = [len(e.output) for e in self.examples]
        styles = {}
        for e in self.examples:
            s = e.metadata.get('style_id', 'unknown')
            styles[s] = styles.get(s, 0) + 1

        return {
            'total': len(self.examples),
            'avg_output_length': sum(output_lengths) // len(output_lengths),
            'min_output_length': min(output_lengths),
            'max_output_length': max(output_lengths),
            'styles': styles,
        }
