"""MCP publish plugin HTTP redirect hardening tests."""
from unittest.mock import MagicMock, patch

from services.mcp.plugins.ghost import GhostPlugin
from services.mcp.plugins.instagram import InstagramPlugin
from services.mcp.plugins.medium import MediumPlugin
from services.mcp.plugins.shopify import ShopifyPlugin
from services.mcp.plugins.substack import SubstackPlugin
from services.mcp.plugins.threads import ThreadsPlugin


def test_medium_plugin_disables_redirects_for_authenticated_requests():
    me_resp = MagicMock(status_code=200)
    me_resp.json.return_value = {"data": {"id": "user-1"}}
    post_resp = MagicMock(status_code=201)
    post_resp.json.return_value = {"data": {"url": "https://medium.com/p/test"}}

    with patch('services.mcp.plugins.medium.requests.get', return_value=me_resp) as mock_get, \
         patch('services.mcp.plugins.medium.requests.post', return_value=post_resp) as mock_post:
        result = MediumPlugin().execute("body", "Title", api_token="token")

    assert result["success"] is True
    assert mock_get.call_args.kwargs["allow_redirects"] is False
    assert mock_post.call_args.kwargs["allow_redirects"] is False


def test_medium_plugin_blocks_redirect_response():
    with patch('services.mcp.plugins.medium.requests.get', return_value=MagicMock(status_code=302)) as mock_get:
        result = MediumPlugin().execute("body", "Title", api_token="token")

    assert result["success"] is False
    assert "리다이렉트 차단" in result["message"]
    assert mock_get.call_args.kwargs["allow_redirects"] is False


def test_substack_plugin_disables_redirects_for_cookie_request():
    resp = MagicMock(status_code=201)
    resp.json.return_value = {"id": "post-1"}

    with patch('services.mcp.plugins.substack.requests.post', return_value=resp) as mock_post:
        result = SubstackPlugin().execute("body", "Title", subdomain="demo", api_key="session")

    assert result["success"] is True
    assert mock_post.call_args.kwargs["allow_redirects"] is False


def test_substack_plugin_blocks_redirect_response():
    with patch('services.mcp.plugins.substack.requests.post', return_value=MagicMock(status_code=302)) as mock_post:
        result = SubstackPlugin().execute("body", "Title", subdomain="demo", api_key="session")

    assert result["success"] is False
    assert "리다이렉트 차단" in result["message"]
    assert mock_post.call_args.kwargs["allow_redirects"] is False


def test_ghost_plugin_disables_redirects_for_admin_request():
    resp = MagicMock(status_code=201)
    resp.json.return_value = {"posts": [{"id": "post-1", "url": "https://ghost.example/post"}]}
    admin_key = f"kid:{'a' * 64}"

    with patch('services.mcp.plugins.ghost.public_url_error', return_value=None), \
         patch('services.mcp.plugins.ghost.requests.post', return_value=resp) as mock_post:
        result = GhostPlugin().execute("body", "Title", api_url="https://ghost.example", admin_api_key=admin_key)

    assert result["success"] is True
    assert mock_post.call_args.kwargs["allow_redirects"] is False


def test_ghost_plugin_blocks_redirect_response():
    admin_key = f"kid:{'a' * 64}"
    with patch('services.mcp.plugins.ghost.public_url_error', return_value=None), \
         patch('services.mcp.plugins.ghost.requests.post', return_value=MagicMock(status_code=302)) as mock_post:
        result = GhostPlugin().execute("body", "Title", api_url="https://ghost.example", admin_api_key=admin_key)

    assert result["success"] is False
    assert "리다이렉트 차단" in result["message"]
    assert mock_post.call_args.kwargs["allow_redirects"] is False


def test_instagram_plugin_disables_redirects_for_graph_requests():
    create_resp = MagicMock(status_code=200)
    create_resp.json.return_value = {"id": "container-1"}
    publish_resp = MagicMock(status_code=200)
    publish_resp.json.return_value = {"id": "media-1"}

    with patch('services.mcp.plugins.instagram.requests.post', side_effect=[create_resp, publish_resp]) as mock_post:
        result = InstagramPlugin().execute(
            "body",
            "Title",
            access_token="token",
            instagram_account_id="acct",
            image_url="https://cdn.example/image.jpg",
        )

    assert result["success"] is True
    assert all(call.kwargs["allow_redirects"] is False for call in mock_post.call_args_list)


def test_instagram_plugin_blocks_redirect_response():
    with patch('services.mcp.plugins.instagram.requests.post', return_value=MagicMock(status_code=302)) as mock_post:
        result = InstagramPlugin().execute(
            "body",
            "Title",
            access_token="token",
            instagram_account_id="acct",
            image_url="https://cdn.example/image.jpg",
        )

    assert result["success"] is False
    assert "리다이렉트 차단" in result["message"]
    assert mock_post.call_args.kwargs["allow_redirects"] is False


def test_shopify_plugin_disables_redirects_for_admin_request():
    resp = MagicMock(status_code=201)
    resp.json.return_value = {"article": {"id": "art-1", "handle": "post"}}

    with patch('services.mcp.plugins.shopify.public_url_error', return_value=None), \
         patch('services.mcp.plugins.shopify.requests.post', return_value=resp) as mock_post:
        result = ShopifyPlugin().execute(
            "body",
            "Title",
            store_domain="mystore.myshopify.com",
            access_token="token",
            blog_id="1",
        )

    assert result["success"] is True
    assert mock_post.call_args.kwargs["allow_redirects"] is False


def test_shopify_plugin_blocks_unsafe_admin_url():
    with patch('services.mcp.plugins.shopify.public_url_error', return_value='Shopify API URL IP가 안전하지 않아 차단되었습니다.'), \
         patch('services.mcp.plugins.shopify.requests.post') as mock_post:
        result = ShopifyPlugin().execute(
            "body",
            "Title",
            store_domain="127.0.0.1",
            access_token="token",
            blog_id="1",
        )

    assert result["success"] is False
    assert "안전하지 않아 차단" in result["message"]
    mock_post.assert_not_called()


def test_threads_plugin_disables_redirects_for_graph_requests():
    create_resp = MagicMock(status_code=200)
    create_resp.json.return_value = {"id": "container-1"}
    publish_resp = MagicMock(status_code=200)
    publish_resp.json.return_value = {"id": "post-1"}

    with patch('services.mcp.plugins.threads.requests.post', side_effect=[create_resp, publish_resp]) as mock_post:
        result = ThreadsPlugin().execute("body", "Title", access_token="token", user_id="user")

    assert result["success"] is True
    assert all(call.kwargs["allow_redirects"] is False for call in mock_post.call_args_list)


def test_threads_plugin_blocks_redirect_response():
    with patch('services.mcp.plugins.threads.requests.post', return_value=MagicMock(status_code=302)) as mock_post:
        result = ThreadsPlugin().execute("body", "Title", access_token="token", user_id="user")

    assert result["success"] is False
    assert "리다이렉트 차단" in result["message"]
    assert mock_post.call_args.kwargs["allow_redirects"] is False
