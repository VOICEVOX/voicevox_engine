import subprocess


def main():
    subprocess.run(
        ["poetry", "export", "--without-hashes", "-o", "requirements.txt"], shell=True
    )
    subprocess.run(
        [
            "poetry",
            "export",
            "--without-hashes",
            "--with",
            "dev",
            "-o",
            "requirements-dev.txt",
        ],
        shell=True,
    )
    subprocess.run(
        [
            "poetry",
            "export",
            "--without-hashes",
            "--with",
            "test",
            "-o",
            "requirements-test.txt",
        ],
        shell=True,
    )
    subprocess.run(
        [
            "poetry",
            "export",
            "--without-hashes",
            "--with",
            "license",
            "-o",
            "requirements-license.txt",
        ],
        shell=True,
    )

    return subprocess.run(["git", "diff", "--exit-code", "--quiet"], shell=True)


if __name__ == "__main__":
    if main().returncode == 1:
        print("Please add requirement files")
