"""`generate_docker_image_names.py` のテスト"""

from tools.generate_docker_image_names import (
    _create_docker_image_names,
    _generate_docker_image_names,
    _generate_docker_image_tags,
)


def test_generate_docker_image_tags_for_prerelease() -> None:
    """プレリリース向けのDockerイメージタグを生成できる。"""
    # Inputs
    version = "0.22.0-preview.1"
    comma_separated_prefix = ",cpu,cpu-ubuntu22.04"
    with_latest = False
    # Expects
    expected_image_names = {
        "0.22.0-preview.1",
        "cpu-0.22.0-preview.1",
        "cpu-ubuntu22.04-0.22.0-preview.1",
    }
    # Outputs
    image_names = _generate_docker_image_tags(
        version=version,
        comma_separated_prefix=comma_separated_prefix,
        with_latest=with_latest,
    )

    # Test
    assert image_names == expected_image_names


def test_generate_docker_image_tags_for_release() -> None:
    """リリース向けのDockerイメージタグを生成できる。"""
    # Inputs
    version = "0.22.0"
    comma_separated_prefix = ",cpu,cpu-ubuntu22.04"
    with_latest = True
    # Expects
    expected_image_names = {
        "0.22.0",
        "latest",
        "cpu-0.22.0",
        "cpu-latest",
        "cpu-ubuntu22.04-0.22.0",
        "cpu-ubuntu22.04-latest",
    }
    # Outputs
    image_names = _generate_docker_image_tags(
        version=version,
        comma_separated_prefix=comma_separated_prefix,
        with_latest=with_latest,
    )

    # Test
    assert image_names == expected_image_names


def test_create_docker_image_names() -> None:
    """Dockerイメージ名を生成できる。"""
    # Inputs
    repository = "your-org/your-repo"
    tags = [
        "0.22.0",
        "latest",
        "cpu-0.22.0",
        "cpu-latest",
        "cpu-ubuntu22.04-0.22.0",
        "cpu-ubuntu22.04-latest",
    ]
    # Expects
    expected_image_names = [
        "your-org/your-repo:0.22.0",
        "your-org/your-repo:latest",
        "your-org/your-repo:cpu-0.22.0",
        "your-org/your-repo:cpu-latest",
        "your-org/your-repo:cpu-ubuntu22.04-0.22.0",
        "your-org/your-repo:cpu-ubuntu22.04-latest",
    ]
    # Outputs
    image_names = _create_docker_image_names(
        repository=repository,
        tags=tags,
    )

    # Test
    assert image_names == expected_image_names


def test_generate_docker_image_names_for_prerelease() -> None:
    """プレリリース向けのDockerイメージ名を生成できる。"""
    # Inputs
    repository = "your-org/your-repo"
    version = "0.22.0-preview.1"
    comma_separated_prefix = ",cpu,cpu-ubuntu22.04"
    with_latest = False
    # Expects
    expected_image_names = {
        "your-org/your-repo:0.22.0-preview.1",
        "your-org/your-repo:cpu-0.22.0-preview.1",
        "your-org/your-repo:cpu-ubuntu22.04-0.22.0-preview.1",
    }
    # Outputs
    image_names = _generate_docker_image_names(
        repository=repository,
        version=version,
        comma_separated_prefix=comma_separated_prefix,
        with_latest=with_latest,
    )

    # Test
    assert image_names == expected_image_names


def test_generate_docker_image_names_for_release() -> None:
    """リリース向けのDockerイメージ名を生成できる。"""
    # Inputs
    repository = "your-org/your-repo"
    version = "0.22.0"
    comma_separated_prefix = ",cpu,cpu-ubuntu22.04"
    with_latest = True
    # Expects
    expected_image_names = {
        "your-org/your-repo:0.22.0",
        "your-org/your-repo:latest",
        "your-org/your-repo:cpu-0.22.0",
        "your-org/your-repo:cpu-latest",
        "your-org/your-repo:cpu-ubuntu22.04-0.22.0",
        "your-org/your-repo:cpu-ubuntu22.04-latest",
    }
    # Outputs
    image_names = _generate_docker_image_names(
        repository=repository,
        version=version,
        comma_separated_prefix=comma_separated_prefix,
        with_latest=with_latest,
    )

    # Test
    assert image_names == expected_image_names
