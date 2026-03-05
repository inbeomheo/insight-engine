"""콘텐츠 라이브러리 서비스 테스트 (F8-01)"""
import pytest
from services import content_library_service as svc


@pytest.fixture(autouse=True)
def clear_state():
    svc.clear_all()
    yield
    svc.clear_all()


def test_create_item():
    item = svc.create_item(title='테스트', content='내용', style='blog_seo', tags=['python'])
    assert item['id']
    assert item['title'] == '테스트'
    assert item['tags'] == ['python']
    assert item['status'] == 'draft'
    assert item['is_pinned'] is False


def test_get_item():
    item = svc.create_item(title='조회 테스트', content='')
    found = svc.get_item(item['id'])
    assert found is not None
    assert found['id'] == item['id']


def test_get_item_not_found():
    assert svc.get_item('nonexistent') is None


def test_update_item():
    item = svc.create_item(title='수정 전', content='')
    updated = svc.update_item(item['id'], title='수정 후', is_pinned=True)
    assert updated['title'] == '수정 후'
    assert updated['is_pinned'] is True


def test_soft_delete():
    item = svc.create_item(title='삭제 테스트', content='')
    svc.delete_item(item['id'], soft=True)
    assert svc.get_item(item['id']) is None


def test_hard_delete():
    item = svc.create_item(title='영구삭제', content='')
    svc.delete_item(item['id'], soft=False)
    # 내부 _items에서도 완전 삭제됨
    assert svc.get_item(item['id']) is None


def test_search_by_title():
    svc.create_item(title='파이썬 강의', content='')
    svc.create_item(title='자바스크립트 기초', content='')
    result = svc.search_items(query='파이썬')
    assert len(result['items']) == 1
    assert result['items'][0]['title'] == '파이썬 강의'


def test_search_filter_by_style():
    svc.create_item(title='A', content='', style='blog_seo')
    svc.create_item(title='B', content='', style='tutorial')
    result = svc.search_items(style='blog_seo')
    assert all(i['style'] == 'blog_seo' for i in result['items'])


def test_search_filter_by_tags():
    svc.create_item(title='A', content='', tags=['python', 'ai'])
    svc.create_item(title='B', content='', tags=['java'])
    result = svc.search_items(tags=['python'])
    assert len(result['items']) == 1


def test_search_pagination():
    for i in range(15):
        svc.create_item(title=f'항목 {i}', content='')
    result = svc.search_items(page=1, per_page=10)
    assert len(result['items']) == 10
    assert result['total'] == 15
    assert result['pages'] == 2


def test_search_is_pinned():
    item = svc.create_item(title='고정', content='')
    svc.update_item(item['id'], is_pinned=True)
    result = svc.search_items(is_pinned=True)
    assert len(result['items']) == 1


def test_increment_view():
    item = svc.create_item(title='뷰 카운트', content='')
    svc.increment_view(item['id'])
    svc.increment_view(item['id'])
    found = svc.get_item(item['id'])
    assert found['view_count'] == 2
