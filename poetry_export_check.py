import subprocess


def main():
    return subprocess.run(["git", "diff", "--exit-code", "--quiet"], shell=True)


if __name__ == "__main__":
    if main().returncode == 1:
        print("Please add requirement files")
