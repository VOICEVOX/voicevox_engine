"""`generate_docker_image_names.py` のテスト"""

from tools.generate_docker_image_names import (
    _generate_docker_image_names,
)


def test_generate_docker_image_names() -> None:
    """Dockerイメージ名を生成できる。"""
    # Inputs
    repository = "your-org/your-repo"
    version = "0.22.0-preview.1"
    comma_separated_prefix = ",cpu,cpu-ubuntu22.04"
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
    )

    # Test
    assert image_names == expected_image_names
