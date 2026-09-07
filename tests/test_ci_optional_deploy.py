"""외부 배포를 켜지 않은 저장소에서도 CI 검증을 유지한다."""
from pathlib import Path
import re
import secrets
import subprocess

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
DOCKER = WORKFLOW["jobs"]["docker-build"]
DEPLOY = WORKFLOW["jobs"]["deploy"]


def _step(job, name):
    return next(step for step in job["steps"] if step.get("name") == name)


def _condition_matches(condition, context):
    """이 워크플로에서 사용하는 문자열 비교와 AND 조건을 실행한다."""
    matches = []
    for term in condition.split("&&"):
        match = re.fullmatch(r"\s*([\w.]+)\s*==\s*'([^']*)'\s*", term)
        assert match, f"지원하지 않는 조건: {term}"
        key, expected = match.groups()
        matches.append(context.get(key, "").casefold() == expected.casefold())
    return all(matches)


@pytest.mark.parametrize("event,branch", [
    ("push", "master"),
    ("push", "main"),
    ("push", "develop"),
    ("pull_request", "master"),
])
@pytest.mark.parametrize("publish,deploy", [
    ("", ""), ("false", "false"), ("true", ""), ("", "true"), ("true", "true"),
])
def test_external_actions_require_explicit_opt_in_on_master_push(event, branch, publish, deploy):
    context = {
        "github.event_name": event,
        "github.ref": f"refs/heads/{branch}",
        "vars.ENABLE_DOCKER_PUBLISH": publish,
        "vars.ENABLE_RAILWAY_DEPLOY": deploy,
    }
    production_push = event == "push" and branch == "master"
    for name in ("Docker 게시 설정 확인", "Docker Hub 로그인", "검증된 프로덕션 이미지 게시"):
        assert _condition_matches(_step(DOCKER, name)["if"], context) == (
            production_push and publish == "true"
        )
    assert _condition_matches(DEPLOY["if"], context) == (production_push and deploy == "true")


def test_build_and_runtime_validation_precede_optional_external_actions():
    for name in ("backend-test", "frontend-test", "e2e-no-auth", "docker-build"):
        assert "if" not in WORKFLOW["jobs"][name]
    assert DOCKER["needs"] == ["backend-test", "frontend-test", "e2e-no-auth"]
    steps = DOCKER["steps"]
    guard = _step(DOCKER, "Docker 게시 설정 확인")
    for name in (
        "Docker 이미지 빌드 및 로컬 로드", "Docker full-stack 런타임 스모크",
        "CLIProxyAPI 7.2.152 이미지 빌드 검증", "CLIProxyAPI 인증 런타임 스모크",
    ):
        validation = _step(DOCKER, name)
        assert "if" not in validation
        assert steps.index(validation) < steps.index(guard)
    assert _step(DOCKER, "Docker 이미지 빌드 및 로컬 로드")["with"]["push"] is False
    assert _step(DOCKER, "Docker 이미지 빌드 및 로컬 로드")["with"]["load"] is True
    gateway_build = _step(DOCKER, "CLIProxyAPI 7.2.152 이미지 빌드 검증")
    assert gateway_build["with"]["push"] is False
    assert gateway_build["with"]["load"] is True
    assert steps.index(gateway_build) < steps.index(_step(DOCKER, "CLIProxyAPI 인증 런타임 스모크"))
    assert steps.index(guard) < steps.index(_step(DOCKER, "Docker Hub 로그인"))


@pytest.mark.parametrize("missing", ["DOCKER_USERNAME", "DOCKER_PASSWORD", None])
def test_enabled_docker_publish_requires_both_secrets_without_disclosing_values(missing):
    credentials = {name: secrets.token_urlsafe(24) for name in ("DOCKER_USERNAME", "DOCKER_PASSWORD")}
    environment = {name: value for name, value in credentials.items() if name != missing}
    result = subprocess.run(
        ["bash", "-eo", "pipefail", "-c", _step(DOCKER, "Docker 게시 설정 확인")["run"]],
        env=environment, capture_output=True, text=True, check=False,
    )
    assert (result.returncode == 0) == (missing is None)
    if missing:
        assert missing in result.stderr
    for value in credentials.values():
        assert value not in result.stdout + result.stderr


@pytest.mark.parametrize("published,token_present,expected_error", [
    ("", True, "ENABLE_DOCKER_PUBLISH"),
    ("false", True, "ENABLE_DOCKER_PUBLISH"),
    ("true", False, "RAILWAY_TOKEN"),
    ("true", True, None),
])
def test_railway_requires_successful_publication_and_token(published, token_present, expected_error):
    guard = _step(DEPLOY, "Railway 배포 설정 확인")
    assert DEPLOY["needs"] == "docker-build"
    assert DOCKER["outputs"]["image-published"] == "${{ steps.publish.outputs.published }}"
    assert guard["env"]["IMAGE_PUBLISHED"] == "${{ needs.docker-build.outputs.image-published }}"
    assert DEPLOY["steps"][0] == guard
    token = secrets.token_urlsafe(24)
    environment = {"IMAGE_PUBLISHED": published, "RAILWAY_TOKEN": token if token_present else ""}
    result = subprocess.run(
        ["bash", "-eo", "pipefail", "-c", guard["run"]],
        env=environment, capture_output=True, text=True, check=False,
    )
    assert (result.returncode == 0) == (expected_error is None)
    if expected_error:
        assert expected_error in result.stdout + result.stderr
    assert token not in result.stdout + result.stderr


@pytest.mark.parametrize("failed_tag", ["sha", "production", "none"])
def test_publish_output_is_written_only_after_both_pushes_succeed(tmp_path, failed_tag):
    publish = _step(DOCKER, "검증된 프로덕션 이미지 게시")
    assert publish["id"] == "publish"
    output = tmp_path / "github-output"
    # Docker 호출만 대체하고 실제 게시 셸의 실패 전파와 출력 시점을 검증한다.
    docker_stub = '''docker() {
      if [[ "$1" == "push" && "$2" == "test/insight-engine:$FAILED_TAG" ]]; then
        return 1
      fi
      return 0
    }
    '''
    result = subprocess.run(
        ["bash", "-eo", "pipefail", "-c", docker_stub + publish["run"]],
        env={
            "DOCKER_REPOSITORY": "test/insight-engine", "IMAGE_SHA": "sha",
            "GITHUB_OUTPUT": str(output), "FAILED_TAG": failed_tag,
        },
        capture_output=True, text=True, check=False,
    )
    assert (result.returncode == 0) == (failed_tag == "none")
    assert (output.read_text() if output.exists() else "") == (
        "published=true\n" if failed_tag == "none" else ""
    )
