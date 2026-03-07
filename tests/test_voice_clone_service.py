"""voice_clone_service 단위 테스트 (검증 로직)"""
import unittest
from unittest.mock import patch

from services.voice_clone_service import VoiceCloneService, ELEVENLABS_API_KEY


class TestVoiceCloneServiceInit(unittest.TestCase):

    @patch('services.voice_clone_service.ELEVENLABS_API_KEY', 'test-key')
    def test_elevenlabs_backend(self):
        """API 키 있으면 elevenlabs 백엔드"""
        svc = VoiceCloneService()
        self.assertEqual(svc.backend, 'elevenlabs')

    @patch('services.voice_clone_service.ELEVENLABS_API_KEY', '')
    def test_coqui_backend(self):
        """API 키 없으면 coqui 백엔드"""
        svc = VoiceCloneService()
        self.assertEqual(svc.backend, 'coqui')


class TestSynthesizeValidation(unittest.TestCase):

    @patch('services.voice_clone_service.ELEVENLABS_API_KEY', 'test-key')
    def test_empty_text(self):
        """빈 텍스트 → ValueError"""
        svc = VoiceCloneService()
        with self.assertRaises(ValueError) as ctx:
            svc.synthesize('')
        self.assertIn('텍스트', str(ctx.exception))

    @patch('services.voice_clone_service.ELEVENLABS_API_KEY', 'test-key')
    def test_whitespace_text(self):
        """공백 텍스트 → ValueError"""
        svc = VoiceCloneService()
        with self.assertRaises(ValueError):
            svc.synthesize('   ')

    @patch('services.voice_clone_service.ELEVENLABS_API_KEY', 'test-key')
    def test_elevenlabs_no_voice_id(self):
        """ElevenLabs 백엔드 + voice_id 없음 → ValueError"""
        svc = VoiceCloneService()
        with self.assertRaises(ValueError) as ctx:
            svc.synthesize('테스트 텍스트')
        self.assertIn('voice_id', str(ctx.exception))

    @patch('services.voice_clone_service.ELEVENLABS_API_KEY', '')
    def test_coqui_no_speaker_wav(self):
        """Coqui 백엔드 + speaker_wav 없음 → ValueError"""
        svc = VoiceCloneService()
        with self.assertRaises(ValueError) as ctx:
            svc.synthesize('테스트 텍스트')
        self.assertIn('speaker_wav', str(ctx.exception))

    @patch('services.voice_clone_service.ELEVENLABS_API_KEY', '')
    def test_coqui_nonexistent_wav(self):
        """Coqui 백엔드 + 존재하지 않는 파일 → FileNotFoundError"""
        svc = VoiceCloneService()
        with self.assertRaises(FileNotFoundError):
            svc.synthesize('텍스트', speaker_wav='/nonexistent/voice.wav')


class TestCloneVoiceFromUrl(unittest.TestCase):

    @patch('services.voice_clone_service.ELEVENLABS_API_KEY', '')
    def test_not_elevenlabs(self):
        """ElevenLabs 아닌 백엔드 → RuntimeError"""
        svc = VoiceCloneService()
        with self.assertRaises(RuntimeError) as ctx:
            svc.clone_voice_from_url('voice', 'https://audio.com/sample.mp3')
        self.assertIn('ElevenLabs', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
